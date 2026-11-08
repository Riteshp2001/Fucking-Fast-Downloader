from __future__ import annotations

import re
import time
import typing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from PyQt5 import QtCore, QtGui, QtWidgets

from ff_downloader.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR
from ff_downloader.core import DownloadEngine, FuckingFastResolver, SpeedMeter, browser_installed
from ff_downloader.ui.brand_assets import ASSETS_DIR, application_icon, brand_mark
from ff_downloader.ui.session import load_session, save_session
from ff_downloader.ui.solar_icons import SolarIconFactory
from ff_downloader.workers import BrowserInstallWorker, DownloadWorker, ResolveWorker

PENDING = "pending"
PREPARING = "preparing"
READY = "ready"
FAILED = "failed"
QUEUED = "queued"
DOWNLOADING = "downloading"
DONE = "done"
ERROR = "error"

STATUS_LABELS = {
    PENDING: "Not prepared",
    PREPARING: "Preparing…",
    READY: "Ready",
    FAILED: "Failed",
    QUEUED: "Queued",
    DOWNLOADING: "Downloading…",
    DONE: "Done",
    ERROR: "Download failed",
}
STATUS_TONES = {READY: "accent", DONE: "accent", FAILED: "danger", ERROR: "danger", PENDING: "subtle"}

# Direct links expire after 24 hours; treat them as stale a little earlier.
LINK_LIFETIME = 23 * 60 * 60


@dataclass
class QueueEntry:
    source: str
    direct: str = ""
    state: str = PENDING
    error: str = ""
    detail: str = ""
    checked: bool = True
    prepared_at: float = 0.0


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def format_size(size: float) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def format_duration(seconds: float) -> str:
    total = int(seconds)
    if total < 60:
        return f"{total}s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


class LinkInput(QtWidgets.QPlainTextEdit):
    """Multiline URL input that can distinguish a paste from normal typing."""

    pasted = QtCore.pyqtSignal()

    def insertFromMimeData(self, source: QtCore.QMimeData) -> None:
        super().insertFromMimeData(source)
        self.pasted.emit()


class ElidedLabel(QtWidgets.QLabel):
    """Single-line label that shortens long text with an ellipsis instead of growing."""

    _full_text = ""
    _mode = QtCore.Qt.ElideRight

    def __init__(self, text: str = "", mode: QtCore.Qt.TextElideMode = QtCore.Qt.ElideRight):
        super().__init__()
        self._mode = mode
        self.setTextFormat(QtCore.Qt.PlainText)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full_text = text
        self._elide()

    def text(self) -> str:
        return self._full_text

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event: QtCore.QEvent) -> None:
        super().changeEvent(event)
        if event.type() in (QtCore.QEvent.FontChange, QtCore.QEvent.StyleChange):
            self._elide()

    def _elide(self) -> None:
        shown = self.fontMetrics().elidedText(self._full_text, self._mode, max(self.width(), 1))
        super().setText(shown)
        self.setToolTip("" if shown == self._full_text else self._full_text)


class TitleBar(QtWidgets.QFrame):
    def __init__(self, on_minimize, on_maximize, on_close, on_theme, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(48)
        self._icon_color = "#94A3B8"

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(8)

        self.brand_icon = QtWidgets.QLabel()
        self.brand_icon.setFixedSize(26, 26)
        self.brand_icon.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.brand_icon)

        brand = QtWidgets.QLabel(APP_NAME)
        brand.setObjectName("titleBrand")
        layout.addWidget(brand)

        version = QtWidgets.QLabel(f"v{APP_VERSION}")
        version.setObjectName("titleVersion")
        layout.addWidget(version)
        layout.addStretch(1)

        self.theme_button = self._window_button("sun", "Toggle theme")
        self.min_button = self._window_button("minimize", "Minimize")
        self.max_button = self._window_button("maximize", "Maximize")
        self.close_button = self._window_button("close", "Close", danger=True)

        self.theme_button.clicked.connect(on_theme)
        self.min_button.clicked.connect(on_minimize)
        self.max_button.clicked.connect(on_maximize)
        self.close_button.clicked.connect(on_close)

        for button in (
            self.theme_button,
            self.min_button,
            self.max_button,
            self.close_button,
        ):
            layout.addWidget(button)

    def _window_button(self, icon: str, tooltip: str, danger: bool = False):
        button = QtWidgets.QPushButton()
        button.setObjectName("winClose" if danger else "winButton")
        button.setProperty("solarIcon", icon)
        button.setFixedSize(40, 34)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.setFocusPolicy(QtCore.Qt.NoFocus)
        button.setToolTip(tooltip)
        return button

    def apply_theme(self, text: str, muted: str, accent: str, dark: bool) -> None:
        self._icon_color = muted
        self.brand_icon.setPixmap(brand_mark(24))
        self.theme_button.setProperty("solarIcon", "sun" if dark else "moon")
        self.theme_button.setToolTip(
            "Switch to light mode" if dark else "Switch to dark mode"
        )
        self._refresh_icons()

    def _refresh_icons(self) -> None:
        for button in (
            self.theme_button,
            self.min_button,
            self.max_button,
            self.close_button,
        ):
            name = button.property("solarIcon")
            button.setIcon(SolarIconFactory.icon(str(name), self._icon_color, 17))
            button.setIconSize(QtCore.QSize(17, 17))

    def set_maximized(self, maximized: bool) -> None:
        self.max_button.setProperty("solarIcon", "restore" if maximized else "maximize")
        self.max_button.setToolTip("Restore" if maximized else "Maximize")
        self._refresh_icons()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and not self.window().isMaximized():
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.max_button.click()
        super().mouseDoubleClickEvent(event)


class ResizeHandle(QtWidgets.QWidget):
    CURSORS: typing.ClassVar[dict[int, QtCore.Qt.CursorShape]] = {
        QtCore.Qt.LeftEdge: QtCore.Qt.SizeHorCursor,
        QtCore.Qt.RightEdge: QtCore.Qt.SizeHorCursor,
        QtCore.Qt.TopEdge: QtCore.Qt.SizeVerCursor,
        QtCore.Qt.BottomEdge: QtCore.Qt.SizeVerCursor,
        QtCore.Qt.LeftEdge | QtCore.Qt.TopEdge: QtCore.Qt.SizeFDiagCursor,
        QtCore.Qt.RightEdge | QtCore.Qt.TopEdge: QtCore.Qt.SizeBDiagCursor,
        QtCore.Qt.LeftEdge | QtCore.Qt.BottomEdge: QtCore.Qt.SizeBDiagCursor,
        QtCore.Qt.RightEdge | QtCore.Qt.BottomEdge: QtCore.Qt.SizeFDiagCursor,
    }

    def __init__(self, edges, thickness: int = 7, parent=None):
        super().__init__(parent)
        self._edges = edges
        self.setCursor(self.CURSORS.get(edges, QtCore.Qt.ArrowCursor))
        if edges in (QtCore.Qt.LeftEdge, QtCore.Qt.RightEdge):
            self.setFixedWidth(thickness)
        elif edges in (QtCore.Qt.TopEdge, QtCore.Qt.BottomEdge):
            self.setFixedHeight(thickness)
        else:
            self.setFixedSize(thickness, thickness)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and not self.window().isMaximized():
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemResize(self._edges)
        super().mousePressEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    PALETTES = {
        "dark": {
            "bg": "#171A15",
            "title": "#1D211B",
            "surface": "#22261F",
            "surface_alt": "#1B1F19",
            "surface_hover": "#2C322A",
            "border": "#414A3E",
            "border_hover": "#778370",
            "text": "#F4F5ED",
            "muted": "#C0C7B9",
            "subtle": "#9BA697",
            "accent": "#91D6A8",
            "accent_hover": "#B4E4C2",
            "accent_text": "#142419",
            "danger": "#FFB1BF",
            "selection": "#314A35",
        },
        "light": {
            "bg": "#F5F4EE",
            "title": "#FBFAF5",
            "surface": "#FFFEF9",
            "surface_alt": "#F0F1E9",
            "surface_hover": "#E7ECE5",
            "border": "#CFD5C9",
            "border_hover": "#899885",
            "text": "#18251B",
            "muted": "#445548",
            "subtle": "#68796B",
            "accent": "#216B4D",
            "accent_hover": "#18563D",
            "accent_text": "#FEFEF8",
            "danger": "#B42345",
            "selection": "#D9E9D9",
        },
    }

    URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(application_icon())
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Window
            | QtCore.Qt.WindowMinimizeButtonHint
        )
        self.resize(1160, 740)
        self.setMinimumSize(840, 590)

        self.settings = QtCore.QSettings("Riteshp2001", APP_NAME)
        saved_theme = str(self.settings.value("theme", "light"))
        self.theme = saved_theme if saved_theme in self.PALETTES else "dark"
        saved_dir = Path(str(self.settings.value("download_dir", str(DOWNLOADS_DIR))))
        self.download_dir = saved_dir if saved_dir.is_dir() else DOWNLOADS_DIR

        self.resolve_worker: ResolveWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.browser_worker: BrowserInstallWorker | None = None
        self.entries: dict[str, QueueEntry] = {}
        self.expansions: dict[str, list[str]] = {}
        self._items: dict[str, QtWidgets.QTreeWidgetItem] = {}
        self._active_download = False
        self._paused = False
        self._download_cancelled = False
        self._download_index = 0
        self._download_total = 0
        self._failed_downloads = 0
        self._current_source = ""
        self._resolve_stopped = False
        self._prepare_queued = False
        self._browser_installing = False
        self._browser_mode = "hidden"
        self._browser_meter = SpeedMeter()
        self._details_open = False
        self._closing = False
        self._session_timer = QtCore.QTimer(self)
        self._session_timer.setSingleShot(True)
        self._session_timer.setInterval(1000)

        self._build_ui()
        self._connect()
        self._apply_theme()
        self._set_status("Ready", "READY")
        self._restore_session()
        self._source_changed()
        QtCore.QTimer.singleShot(0, self._check_browser)

    @property
    def palette(self) -> dict[str, str]:
        return self.PALETTES[self.theme]

    def _button(
        self,
        text: str,
        icon: str,
        *,
        primary: bool = False,
        compact: bool = False,
    ) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.setProperty("primary", primary)
        button.setProperty("solarIcon", icon)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.setMinimumHeight(40 if compact else 44)
        return button

    def _icon_button(self, icon: str, tooltip: str) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton()
        button.setProperty("solarIcon", icon)
        button.setProperty("iconOnly", True)
        button.setFixedSize(38, 38)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.setToolTip(tooltip)
        return button

    @staticmethod
    def _card_header(icon: str, title: str) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        icon_label = QtWidgets.QLabel()
        icon_label.setProperty("solarLabel", icon)
        icon_label.setFixedSize(20, 20)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("cardTitle")
        row.addWidget(icon_label)
        row.addWidget(title_label)
        return row

    def _build_ui(self) -> None:
        root = QtWidgets.QWidget(self)
        root.setObjectName("root")
        self.setCentralWidget(root)
        shell = QtWidgets.QVBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.title_bar = TitleBar(
            self.showMinimized,
            self._toggle_maximize,
            self.close,
            self.toggle_theme,
        )
        shell.addWidget(self.title_bar)

        resize_frame = QtWidgets.QWidget()
        resize_layout = QtWidgets.QGridLayout(resize_frame)
        resize_layout.setContentsMargins(0, 0, 0, 0)
        resize_layout.setSpacing(0)
        for row, col, edges in (
            (0, 0, QtCore.Qt.LeftEdge | QtCore.Qt.TopEdge),
            (0, 1, QtCore.Qt.TopEdge),
            (0, 2, QtCore.Qt.RightEdge | QtCore.Qt.TopEdge),
            (1, 0, QtCore.Qt.LeftEdge),
            (1, 2, QtCore.Qt.RightEdge),
            (2, 0, QtCore.Qt.LeftEdge | QtCore.Qt.BottomEdge),
            (2, 1, QtCore.Qt.BottomEdge),
            (2, 2, QtCore.Qt.RightEdge | QtCore.Qt.BottomEdge),
        ):
            resize_layout.addWidget(ResizeHandle(edges), row, col)

        self.workspace_scroll = QtWidgets.QScrollArea()
        self.workspace_scroll.setObjectName("workspaceScroll")
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.workspace_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.workspace_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        content = QtWidgets.QWidget()
        content.setObjectName("content")
        self.workspace_scroll.setWidget(content)
        resize_layout.addWidget(self.workspace_scroll, 1, 1)
        shell.addWidget(resize_frame, 1)

        body = QtWidgets.QVBoxLayout(content)
        body.setContentsMargins(22, 16, 22, 16)
        body.setSpacing(12)
        body.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        body.addWidget(self._build_browser_notice())

        self.link_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.link_splitter.setChildrenCollapsible(False)
        self.link_splitter.setHandleWidth(12)
        self.link_splitter.setMinimumHeight(300)
        self.link_splitter.addWidget(self._build_links_card())
        self.link_splitter.addWidget(self._build_queue_card())
        self.link_splitter.setStretchFactor(0, 2)
        self.link_splitter.setStretchFactor(1, 3)
        self.link_splitter.setSizes([440, 660])
        body.addWidget(self.link_splitter, 1)
        body.addWidget(self._build_download_card())

    def _build_browser_notice(self) -> QtWidgets.QFrame:
        self.browser_notice = QtWidgets.QFrame()
        self.browser_notice.setObjectName("notice")
        layout = QtWidgets.QHBoxLayout(self.browser_notice)
        layout.setContentsMargins(14, 8, 8, 8)
        layout.setSpacing(12)

        icon = QtWidgets.QLabel()
        icon.setProperty("solarLabel", "globe")
        icon.setFixedSize(20, 20)
        layout.addWidget(icon)

        text = QtWidgets.QVBoxLayout()
        text.setSpacing(6)
        self.browser_label = ElidedLabel()
        self.browser_label.setObjectName("noticeText")
        self.browser_progress = QtWidgets.QProgressBar()
        self.browser_progress.setRange(0, 1000)
        self.browser_progress.setTextVisible(False)
        self.browser_progress.setFixedHeight(6)
        self.browser_progress.setVisible(False)
        text.addWidget(self.browser_label)
        text.addWidget(self.browser_progress)
        layout.addLayout(text, 1)

        self.browser_btn = self._button("Install", "download", compact=True)
        layout.addWidget(self.browser_btn)
        self.browser_notice.setVisible(False)
        return self.browser_notice

    def _build_links_card(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head = self._card_header("link", "Links")
        self.source_count = QtWidgets.QLabel("0 links")
        self.source_count.setObjectName("pill")
        self.paste_btn = self._icon_button("paste", "Paste from clipboard")
        self.clear_btn = self._icon_button("trash", "Clear all links")
        head.addWidget(self.source_count)
        head.addStretch(1)
        head.addWidget(self.paste_btn)
        head.addWidget(self.clear_btn)
        layout.addLayout(head)

        self.link_input = LinkInput()
        self.link_input.setObjectName("linkInput")
        self.link_input.setPlaceholderText("Paste share links or a FitGirl page, one per line")
        self.link_input.setMinimumHeight(130)
        layout.addWidget(self.link_input, 1)

        foot = QtWidgets.QHBoxLayout()
        self.auto_check = QtWidgets.QCheckBox("Prepare on paste")
        self.auto_check.setChecked(self.settings.value("auto_prepare", True, type=bool))
        self.auto_check.setToolTip("Start preparing as soon as links are pasted")
        self.resolve_btn = self._button("Prepare", "refresh", compact=True)
        self.resolve_btn.setToolTip("Get fresh download links (Ctrl+Enter)")
        foot.addWidget(self.auto_check)
        foot.addStretch(1)
        foot.addWidget(self.resolve_btn)
        layout.addLayout(foot)
        return card

    def _build_queue_card(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head = self._card_header("checklist", "Queue")
        self.resolved_count = QtWidgets.QLabel("Empty")
        self.resolved_count.setObjectName("pill")
        self.copy_btn = self._icon_button("copy", "Copy download links")
        head.addWidget(self.resolved_count)
        head.addStretch(1)
        head.addWidget(self.copy_btn)
        layout.addLayout(head)

        self.resolved_list = QtWidgets.QTreeWidget()
        self.resolved_list.setObjectName("resolvedList")
        self.resolved_list.setHeaderLabels(["File", "Status"])
        self.resolved_list.setRootIsDecorated(False)
        self.resolved_list.setUniformRowHeights(True)
        self.resolved_list.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.resolved_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.resolved_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header = self.resolved_list.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(1, 150)

        self.resolve_empty = QtWidgets.QLabel("Paste links to build your queue")
        self.resolve_empty.setObjectName("emptyState")
        self.resolve_empty.setAlignment(QtCore.Qt.AlignCenter)
        self.resolve_empty.setWordWrap(True)
        self.queue_stack = QtWidgets.QStackedWidget()
        self.queue_stack.addWidget(self.resolve_empty)
        self.queue_stack.addWidget(self.resolved_list)
        layout.addWidget(self.queue_stack, 1)
        return card

    def _build_download_card(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        self.file_label = ElidedLabel(mode=QtCore.Qt.ElideMiddle)
        self.file_label.setObjectName("fileName")
        self.state_pill = QtWidgets.QLabel("READY")
        self.state_pill.setObjectName("statePill")
        top.addWidget(self.file_label, 1)
        top.addWidget(self.state_pill)
        layout.addLayout(top)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)

        info = QtWidgets.QHBoxLayout()
        self.status_text = ElidedLabel()
        self.status_text.setObjectName("statusText")
        self.detail_text = QtWidgets.QLabel()
        self.detail_text.setObjectName("transferDetail")
        info.addWidget(self.status_text, 1)
        info.addWidget(self.detail_text)
        layout.addLayout(info)

        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(8)
        self.folder_btn = self._button("", "folder", compact=True)
        self.folder_btn.setProperty("chip", True)
        self.folder_btn.setMaximumWidth(320)
        self.open_folder_btn = self._icon_button("folder-open", "Open download folder")
        self.details_btn = self._button("Log", "document", compact=True)
        self.pause_resume_btn = self._button("Pause", "pause", compact=True)
        self.cancel_btn = self._button("Cancel", "stop", compact=True)
        self.download_btn = self._button("Download", "download", primary=True, compact=True)
        actions.addWidget(self.folder_btn)
        actions.addWidget(self.open_folder_btn)
        actions.addStretch(1)
        for button in (
            self.details_btn,
            self.pause_resume_btn,
            self.cancel_btn,
            self.download_btn,
        ):
            actions.addWidget(button)
        layout.addLayout(actions)

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(120)
        self.log_view.setVisible(False)
        layout.addWidget(self.log_view)

        self.download_card = card
        self._update_folder_button()
        return card

    def _connect(self) -> None:
        self.link_input.textChanged.connect(self._source_changed)
        self.link_input.pasted.connect(self._auto_resolve_after_paste)
        self.paste_btn.clicked.connect(self.paste_links)
        self.clear_btn.clicked.connect(self.clear_links)
        self.auto_check.toggled.connect(self._auto_prepare_toggled)
        self.resolve_btn.clicked.connect(self._prepare_clicked)
        self.copy_btn.clicked.connect(self.copy_resolved_links)
        self.browser_btn.clicked.connect(self._browser_button_clicked)
        self.folder_btn.clicked.connect(self.choose_folder)
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.download_btn.clicked.connect(self.download_all)
        self.pause_resume_btn.clicked.connect(self.toggle_pause)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.details_btn.clicked.connect(self.toggle_details)
        self.resolved_list.customContextMenuRequested.connect(self._resolved_menu)
        self.resolved_list.itemChanged.connect(self._queue_item_changed)
        self.resolved_list.itemDoubleClicked.connect(self._queue_item_activated)
        self._session_timer.timeout.connect(self._save_session)
        for keys in ("Ctrl+Return", "Ctrl+Enter"):
            QtWidgets.QShortcut(QtGui.QKeySequence(keys), self, activated=self.resolve_links)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event: QtCore.QEvent) -> None:
        if event.type() == QtCore.QEvent.WindowStateChange:
            self.title_bar.set_maximized(self.isMaximized())
        super().changeEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        busy = [
            worker
            for worker in (self.resolve_worker, self.download_worker, self.browser_worker)
            if worker is not None and worker.isRunning()
        ]
        if not busy:
            self._save_session()
            super().closeEvent(event)
            return
        event.ignore()
        if self._closing or (self.download_worker in busy and not self._confirm_quit()):
            return
        # Workers own threads and a browser; let them stop cleanly before the window closes.
        self._closing = True
        for worker in busy:
            worker.cancel()
            worker.finished.connect(self.close)
        self.hide()

    def _confirm_quit(self) -> bool:
        answer = QtWidgets.QMessageBox.question(
            self,
            APP_NAME,
            "A download is still running. Stop it and quit?\nIt will resume next time.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def toggle_theme(self) -> None:
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings.setValue("theme", self.theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        p = self.palette
        dark = self.theme == "dark"
        self.title_bar.apply_theme(p["text"], p["muted"], p["accent"], dark)
        check = (ASSETS_DIR / ("check-dark.svg" if dark else "check-light.svg")).as_posix()

        self.setStyleSheet(
            f"""
            QWidget#root {{ background: {p['bg']}; color: {p['text']}; }}
            QWidget#content {{ background: {p['bg']}; }}
            QLabel {{ color: {p['text']}; }}
            QToolTip {{ background: {p['surface']}; color: {p['text']}; border: 1px solid {p['border']}; padding: 5px 8px; }}
            QFrame#titleBar {{ background: {p['title']}; border-bottom: 1px solid {p['border']}; }}
            QLabel#titleBrand {{ font-size: 13px; font-weight: 700; }}
            QLabel#titleVersion {{ color: {p['subtle']}; font-size: 10px; font-weight: 600; }}
            QPushButton#winButton, QPushButton#winClose {{ background: transparent; border: none; border-radius: 8px; }}
            QPushButton#winButton:hover {{ background: {p['surface_hover']}; }}
            QPushButton#winClose:hover {{ background: {p['danger']}; }}
            QFrame#card {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 12px; }}
            QFrame#notice {{ background: {p['surface']}; border: 1px solid {p['border']}; border-left: 3px solid {p['accent']}; border-radius: 10px; }}
            QFrame#notice[tone="danger"] {{ border-left-color: {p['danger']}; }}
            QLabel#noticeText {{ font-size: 12px; font-weight: 600; }}
            QLabel#cardTitle {{ font-size: 14px; font-weight: 700; }}
            QLabel#fileName {{ font-size: 14px; font-weight: 650; }}
            QLabel#statusText, QLabel#transferDetail {{ color: {p['muted']}; font-size: 11px; }}
            QLabel#transferDetail {{ font-weight: 600; }}
            QLabel#emptyState {{ color: {p['subtle']}; font-size: 12px; padding: 18px; }}
            QLabel#pill, QLabel#statePill {{ background: {p['surface_alt']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 3px 9px; color: {p['muted']}; font-size: 10px; font-weight: 700; }}
            QLabel#statePill[tone="accent"] {{ color: {p['accent']}; border-color: {p['accent']}; }}
            QLabel#statePill[tone="danger"] {{ color: {p['danger']}; border-color: {p['danger']}; }}
            QPushButton {{ background: {p['surface_alt']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 0 14px; font-weight: 650; }}
            QPushButton:hover {{ background: {p['surface_hover']}; border-color: {p['border_hover']}; }}
            QPushButton:pressed {{ padding-top: 1px; }}
            QPushButton:disabled {{ color: {p['subtle']}; border-color: {p['border']}; }}
            QPushButton[primary="true"] {{ background: {p['accent']}; color: {p['accent_text']}; border-color: {p['accent']}; padding: 0 20px; }}
            QPushButton[primary="true"]:hover {{ background: {p['accent_hover']}; border-color: {p['accent_hover']}; }}
            QPushButton[primary="true"]:disabled {{ background: {p['surface_alt']}; color: {p['subtle']}; border-color: {p['border']}; }}
            QPushButton[iconOnly="true"] {{ padding: 0; }}
            QPushButton[chip="true"] {{ color: {p['muted']}; font-weight: 600; padding: 0 12px; text-align: left; }}
            QCheckBox {{ color: {p['muted']}; font-size: 11px; spacing: 8px; }}
            QCheckBox::indicator, QTreeWidget#resolvedList::indicator {{ width: 15px; height: 15px; border: 1px solid {p['border_hover']}; border-radius: 4px; background: {p['surface']}; }}
            QCheckBox::indicator:checked, QTreeWidget#resolvedList::indicator:checked {{ background: {p['accent']}; border-color: {p['accent']}; image: url("{check}"); }}
            QPlainTextEdit#linkInput, QTreeWidget#resolvedList, QTextEdit#logView {{ background: {p['surface_alt']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 10px; selection-background-color: {p['selection']}; selection-color: {p['text']}; }}
            QPlainTextEdit#linkInput {{ padding: 10px; font-size: 11px; }}
            QPlainTextEdit#linkInput:focus, QTreeWidget#resolvedList:focus {{ border-color: {p['accent']}; }}
            QTreeWidget#resolvedList {{ outline: none; }}
            QTreeWidget#resolvedList::item {{ min-height: 30px; padding: 2px 6px; }}
            QTreeWidget#resolvedList::item:hover {{ background: {p['surface_hover']}; }}
            QTreeWidget#resolvedList::item:selected {{ background: {p['selection']}; }}
            QHeaderView::section {{ background: {p['surface']}; color: {p['muted']}; border: none; border-bottom: 1px solid {p['border']}; padding: 7px; font-size: 10px; font-weight: 650; }}
            QTextEdit#logView {{ padding: 8px; color: {p['muted']}; font-family: 'Cascadia Mono', 'Consolas', monospace; font-size: 10px; }}
            QProgressBar {{ background: {p['surface_alt']}; border: 1px solid {p['border']}; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {p['accent']}; border-radius: 3px; }}
            QSplitter::handle {{ background: transparent; }}
            QMenu {{ background: {p['surface']}; color: {p['text']}; border: 1px solid {p['border']}; padding: 4px; }}
            QMenu::item {{ padding: 7px 24px 7px 12px; border-radius: 6px; }}
            QMenu::item:selected {{ background: {p['selection']}; }}
            QMenu::item:disabled {{ color: {p['subtle']}; }}
            QMenu::separator {{ height: 1px; background: {p['border']}; margin: 4px 8px; }}
            QMessageBox {{ background: {p['surface']}; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {p['border_hover']}; min-height: 28px; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
            QScrollBar::handle:horizontal {{ background: {p['border_hover']}; min-width: 28px; border-radius: 4px; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
            """
        )
        self._refresh_solar_icons()
        self._repaint_queue()

    def _refresh_solar_icons(self) -> None:
        p = self.palette
        for button in self.findChildren(QtWidgets.QPushButton):
            name = button.property("solarIcon")
            if not name:
                continue
            if button.objectName() in {"winButton", "winClose"}:
                color = p["muted"]
            elif not button.isEnabled():
                color = p["subtle"]
            elif button.property("primary"):
                color = p["accent_text"]
            else:
                color = p["text"]
            button.setIcon(SolarIconFactory.icon(str(name), color, 18))
            button.setIconSize(QtCore.QSize(18, 18))
        for label in self.findChildren(QtWidgets.QLabel):
            name = label.property("solarLabel")
            if name:
                label.setPixmap(
                    SolarIconFactory.icon(str(name), p["accent"], 20).pixmap(20, 20)
                )

    def source_links(self) -> list[str]:
        text = self.link_input.toPlainText()
        matches = self.URL_RE.findall(text)
        if not matches:
            matches = [
                line.strip().strip('"').strip("'") for line in text.splitlines()
            ]
        return list(dict.fromkeys(link for link in matches if link))

    def _visible_sources(self) -> list[str]:
        sources: list[str] = []
        for link in self.source_links():
            sources.extend(self.expansions.get(link, [link]))
        return list(dict.fromkeys(sources))

    def _visible_entries(self) -> list[QueueEntry]:
        sources = self._visible_sources()
        return [self.entries[source] for source in sources if source in self.entries]

    @staticmethod
    def _new_entry(source: str) -> QueueEntry:
        entry = QueueEntry(source=source)
        if FuckingFastResolver.is_direct_link(source):
            entry.direct, entry.state, entry.prepared_at = source, READY, time.time()
        return entry

    @staticmethod
    def _is_stale(entry: QueueEntry, now: float) -> bool:
        return (
            bool(entry.direct)
            and not FuckingFastResolver.is_direct_link(entry.source)
            and now - entry.prepared_at > LINK_LIFETIME
        )

    def _source_changed(self) -> None:
        links = self.source_links()
        self.source_count.setText(plural(len(links), "link"))
        current = set(links)
        self.expansions = {
            origin: sources for origin, sources in self.expansions.items() if origin in current
        }
        for link in links:
            for source in self.expansions.get(link, [link]):
                if source not in self.entries:
                    self.entries[source] = self._new_entry(source)
        visible = set(self._visible_sources())
        busy = (PREPARING, QUEUED, DOWNLOADING)
        self.entries = {
            source: entry
            for source, entry in self.entries.items()
            if source in visible or entry.state in busy
        }
        self._rebuild_queue()
        self._refresh_summary()
        self._sync_actions()
        self._schedule_session_save()

    def paste_links(self) -> None:
        text = QtWidgets.QApplication.clipboard().text().strip()
        if not text:
            self._notify("Clipboard is empty")
            return
        current = self.link_input.toPlainText()
        cursor = self.link_input.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(f"\n{text}" if current and not current.endswith("\n") else text)
        self.link_input.setTextCursor(cursor)
        self._auto_resolve_after_paste()

    def clear_links(self) -> None:
        cursor = self.link_input.textCursor()
        cursor.select(QtGui.QTextCursor.Document)
        cursor.removeSelectedText()
        self._notify("Links cleared · Ctrl+Z to undo")

    def _auto_resolve_after_paste(self) -> None:
        if not self.auto_check.isChecked():
            return
        if self._resolving() or self._browser_install_running():
            self._prepare_queued = True
            return
        QtCore.QTimer.singleShot(250, self.resolve_links)

    def _auto_prepare_toggled(self, checked: bool) -> None:
        self.settings.setValue("auto_prepare", checked)

    def _resolving(self) -> bool:
        return self.resolve_worker is not None and self.resolve_worker.isRunning()

    def _browser_install_running(self) -> bool:
        return self.browser_worker is not None and self.browser_worker.isRunning()

    @staticmethod
    def _dispose(worker: QtCore.QThread | None) -> None:
        if worker is None:
            return
        if worker.isRunning():
            worker.finished.connect(worker.deleteLater)
        else:
            worker.deleteLater()

    def _prepare_clicked(self) -> None:
        if self._resolving():
            self.stop_preparing()
        else:
            self.resolve_links()

    def resolve_links(self) -> None:
        if self._resolving():
            return
        if self._browser_install_running():
            self._prepare_queued = True
            self._notify("Preparing starts once the browser engine is installed")
            return
        self._expire_stale_links()
        targets = [
            entry
            for entry in self._visible_entries()
            if entry.checked and entry.state in (PENDING, FAILED)
        ]
        if not targets:
            self._notify("Nothing to prepare" if self.source_links() else "Paste a link first")
            return
        for entry in targets:
            entry.state, entry.detail, entry.error = PREPARING, "Waiting…", ""
            self._paint_entry(entry)
        self._dispose(self.resolve_worker)
        self._resolve_stopped = False

        worker = ResolveWorker([entry.source for entry in targets], self)
        worker.log.connect(self._resolve_log)
        worker.install_started.connect(self._browser_install_started)
        worker.browser_progress.connect(self._browser_install_progress)
        worker.install_finished.connect(self._browser_install_finished)
        worker.expanded.connect(self._resolve_expanded)
        worker.item_started.connect(self._resolve_item_started)
        worker.item_resolved.connect(self._resolve_item_resolved)
        worker.item_failed.connect(self._resolve_item_failed)
        worker.completed.connect(self._show_resolution)
        worker.failed.connect(self._resolve_failed)
        worker.finished.connect(self._resolve_finished)
        self.resolve_worker = worker
        worker.start()

        self.file_label.setText(f"Preparing {plural(len(targets), 'link')}")
        self._set_status("A browser window may ask you to verify", "PREPARING")
        self._update_queue_summary()
        self._sync_actions()

    def stop_preparing(self) -> None:
        if self.resolve_worker is None or not self.resolve_worker.isRunning():
            return
        self._resolve_stopped = True
        self._prepare_queued = False
        self.resolve_worker.cancel()
        self.resolve_btn.setEnabled(False)
        self._set_status("Stopping…", "STOPPING")

    def _resolve_log(self, message: str) -> None:
        self.log(message)
        if self._resolving() and not self._resolve_stopped:
            self.status_text.setText(message)

    def _resolve_expanded(self, link: str, sources: list) -> None:
        if not FuckingFastResolver.is_source_page(link):
            return
        page = self.entries.pop(link, None)
        checked = page.checked if page is not None else True
        self.expansions[link] = [str(source) for source in sources]
        for source in self.expansions[link]:
            entry = self.entries.get(source)
            if entry is None:
                entry = self.entries[source] = QueueEntry(source=source, checked=checked)
            if entry.state in (PENDING, FAILED):
                entry.state, entry.detail, entry.error = PREPARING, "Waiting…", ""
        self._rebuild_queue()
        self._sync_actions()
        self._schedule_session_save()

    def _resolve_item_started(self, source: str) -> None:
        entry = self.entries.get(source)
        if entry is not None:
            entry.state, entry.detail, entry.error = PREPARING, "", ""
            self._paint_entry(entry)
        self.file_label.setText(f"Preparing {self._queue_label(source)}")

    def _resolve_item_resolved(self, source: str, direct: str) -> None:
        self._mark_resolved(source, direct)
        self._update_queue_summary()
        self._sync_actions()

    def _resolve_item_failed(self, source: str, error: str) -> None:
        self.log(f"Could not prepare {self._queue_label(source)}: {error}")
        self._mark_failed(source, error)
        self._update_queue_summary()
        self._sync_actions()

    def _mark_resolved(self, source: str, direct: str) -> None:
        entry = self.entries.get(source)
        if entry is None:
            return
        entry.direct, entry.state, entry.detail, entry.error = direct, READY, "", ""
        entry.prepared_at = time.time()
        self._paint_entry(entry)
        self._schedule_session_save()

    def _mark_failed(self, source: str, error: str) -> None:
        entry = self.entries.get(source)
        if entry is None:
            return
        entry.state, entry.detail, entry.error = FAILED, "", error
        self._paint_entry(entry)
        self._schedule_session_save()

    def _resolve_failed(self, error: str) -> None:
        self.log(f"Prepare failed: {error}")
        self._set_status(f"Couldn't prepare links: {error}", "ERROR")

    def _resolve_finished(self) -> None:
        for entry in self.entries.values():
            if entry.state == PREPARING:
                entry.state, entry.detail = (READY if entry.direct else PENDING), ""
                self._paint_entry(entry)
        if self._resolve_stopped:
            self._set_status("Preparation stopped", "READY")
        self._resolve_stopped = False
        self._update_queue_summary()
        self._refresh_summary()
        self._check_browser()
        self._sync_actions()
        self._schedule_session_save()
        if self._prepare_queued:
            self._prepare_queued = False
            QtCore.QTimer.singleShot(0, self.resolve_links)

    def _show_resolution(self, pairs: list, failures: list) -> None:
        pairs = [(str(source), str(direct)) for source, direct in pairs]
        failures = [(str(source), str(error)) for source, error in failures]
        missing = [source for source, _ in pairs + failures if source not in self.entries]
        for source in missing:
            self.entries[source] = QueueEntry(source=source)
        if missing:
            self._rebuild_queue()
        for source, direct in pairs:
            self._mark_resolved(source, direct)
        for source, error in failures:
            self._mark_failed(source, error)

        count, failed = len(pairs), len(failures)
        if count:
            message = f"Prepared {plural(count, 'link')}"
            self._set_status(f"{message} · {failed} failed" if failed else message, "READY")
        elif failed:
            self._set_status(f"Couldn't prepare {plural(failed, 'link')}", "ERROR")
        self.log(f"Prepared {count} link(s); {failed} failed")
        self._update_queue_summary()
        self._refresh_summary()
        self._sync_actions()

    @staticmethod
    def _short_url(url: str) -> str:
        return url if len(url) <= 54 else f"{url[:26]}…{url[-24:]}"

    @classmethod
    def _queue_label(cls, url: str) -> str:
        parsed = urlparse(url)
        fragment = unquote(parsed.fragment).strip()
        if fragment:
            return fragment
        filename = unquote(Path(parsed.path).name).strip()
        return filename or cls._short_url(url)

    # ---------------------------------------------------------------- queue

    def _rebuild_queue(self) -> None:
        entries = self._visible_entries()
        blocked = self.resolved_list.blockSignals(True)
        try:
            self.resolved_list.clear()
            self._items = {}
            for entry in entries:
                item = QtWidgets.QTreeWidgetItem([self._queue_label(entry.source), ""])
                item.setData(0, QtCore.Qt.UserRole, entry.source)
                item.setToolTip(0, entry.source)
                self.resolved_list.addTopLevelItem(item)
                self._items[entry.source] = item
        finally:
            self.resolved_list.blockSignals(blocked)
        self._repaint_queue()
        self.queue_stack.setCurrentWidget(self.resolved_list if entries else self.resolve_empty)
        self._update_queue_summary()

    def _repaint_queue(self) -> None:
        for entry in self._visible_entries():
            self._paint_entry(entry)

    def _paint_entry(self, entry: QueueEntry) -> None:
        item = self._items.get(entry.source)
        if item is None:
            return
        status = entry.detail or STATUS_LABELS[entry.state]
        if entry.state == READY and not entry.detail and self._has_partial(entry):
            status = "Resumable"
        color = QtGui.QColor(self.palette[STATUS_TONES.get(entry.state, "text")])
        blocked = self.resolved_list.blockSignals(True)
        try:
            item.setCheckState(0, QtCore.Qt.Checked if entry.checked else QtCore.Qt.Unchecked)
            item.setText(1, status)
            item.setToolTip(1, entry.error or status)
            item.setForeground(1, QtGui.QBrush(color))
        finally:
            self.resolved_list.blockSignals(blocked)

    def _partial_file(self, entry: QueueEntry) -> Path:
        name = DownloadEngine.filename_from_link(entry.source)
        name = name or DownloadEngine.filename_from_url(entry.direct)
        return self.download_dir / f"{name}.part"

    def _has_partial(self, entry: QueueEntry) -> bool:
        try:
            return self._partial_file(entry).exists()
        except OSError:
            return False

    def _update_queue_summary(self) -> None:
        entries = self._visible_entries()
        active = (READY, QUEUED, DOWNLOADING)
        counts = (
            (sum(e.direct != "" and e.state in active for e in entries), "ready"),
            (sum(e.state == DONE for e in entries), "done"),
            (sum(e.state in (FAILED, ERROR) for e in entries), "failed"),
            (sum(e.state in (PENDING, PREPARING) for e in entries), "to prepare"),
        )
        parts = [f"{count} {label}" for count, label in counts if count]
        self.resolved_count.setText(" · ".join(parts) if parts else "Empty")

    def _refresh_summary(self) -> None:
        if self._active_download or self._resolving():
            return
        entries = self._visible_entries()
        ready = sum(e.checked and e.direct != "" and e.state in (READY, ERROR) for e in entries)
        pending = sum(e.checked and e.state in (PENDING, FAILED) for e in entries)
        if not entries:
            text = "Add links to get started"
        elif ready:
            text = f"{plural(ready, 'file')} ready to download"
        elif pending:
            text = f"{plural(pending, 'link')} to prepare"
        elif all(entry.state == DONE for entry in entries):
            text = "All files downloaded"
        else:
            text = "Nothing selected"
        self.file_label.setText(text)

    def _selected_entries(self) -> list[QueueEntry]:
        items = self.resolved_list.selectedItems()
        sources = [str(item.data(0, QtCore.Qt.UserRole)) for item in items]
        return [self.entries[source] for source in sources if source in self.entries]

    def _queue_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        entry = self.entries.get(str(item.data(0, QtCore.Qt.UserRole)))
        if column != 0 or entry is None:
            return
        entry.checked = item.checkState(0) == QtCore.Qt.Checked
        self._update_queue_summary()
        self._refresh_summary()
        self._sync_actions()
        self._schedule_session_save()

    def _queue_item_activated(self, item: QtWidgets.QTreeWidgetItem, _column: int) -> None:
        entry = self.entries.get(str(item.data(0, QtCore.Qt.UserRole)))
        if entry is not None and entry.state == DONE:
            self.open_folder()

    def _copy(self, values: list[str]) -> None:
        if values:
            QtWidgets.QApplication.clipboard().setText("\n".join(values))
            self._notify(f"Copied {plural(len(values), 'link')}")

    def copy_resolved_links(self) -> None:
        entries = self._visible_entries()
        links = [entry.direct for entry in entries if entry.checked and entry.direct]
        if links:
            self._copy(links)
        else:
            self._notify("No download links yet")

    def _resolved_menu(self, position: QtCore.QPoint) -> None:
        item = self.resolved_list.itemAt(position)
        if item is None:
            return
        if not item.isSelected():
            self.resolved_list.setCurrentItem(item)
        entries = self._selected_entries()
        menu = QtWidgets.QMenu(self)
        copy_direct = menu.addAction("Copy download link")
        copy_source = menu.addAction("Copy share link")
        menu.addSeparator()
        include = menu.addAction("Include")
        exclude = menu.addAction("Exclude")
        copy_direct.setEnabled(any(entry.direct for entry in entries))
        action = menu.exec_(self.resolved_list.viewport().mapToGlobal(position))
        if action is copy_direct:
            self._copy([entry.direct for entry in entries if entry.direct])
        elif action is copy_source:
            self._copy([entry.source for entry in entries])
        elif action is include or action is exclude:
            for entry in entries:
                entry.checked = action is include
                self._paint_entry(entry)
            self._update_queue_summary()
            self._refresh_summary()
            self._sync_actions()
            self._schedule_session_save()

    # -------------------------------------------------------------- folders

    def choose_folder(self) -> None:
        selected = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose download folder", str(self.download_dir)
        )
        if selected:
            self.download_dir = Path(selected)
            self.settings.setValue("download_dir", selected)
            self._update_folder_button()
            self._repaint_queue()
            self._sync_actions()
            self._notify("Download folder updated")

    def open_folder(self) -> None:
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._notify(f"Can't open the folder: {exc}")
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.download_dir)))

    def _update_folder_button(self) -> None:
        path = str(self.download_dir)
        metrics = self.folder_btn.fontMetrics()
        self.folder_btn.setText(metrics.elidedText(path, QtCore.Qt.ElideMiddle, 240))
        self.folder_btn.setToolTip(f"Saving to {path}\nClick to change")

    # ------------------------------------------------------------ downloads

    def _expire_stale_links(self) -> None:
        now = time.time()
        for entry in self._visible_entries():
            if entry.state in (READY, ERROR) and self._is_stale(entry, now):
                entry.direct, entry.state, entry.error = "", PENDING, ""
                self._paint_entry(entry)

    def download_all(self) -> None:
        if self._active_download:
            return
        if not self.source_links():
            self._notify("Paste a link first")
            return
        self._expire_stale_links()
        targets = [
            entry
            for entry in self._visible_entries()
            if entry.checked and entry.direct and entry.state in (READY, ERROR)
        ]
        if not targets:
            self._notify("Prepare at least one link before downloading")
            self._sync_actions()
            return
        self._dispose(self.download_worker)

        self._active_download = True
        self._paused = False
        self._download_cancelled = False
        self._failed_downloads = 0
        self._download_index = 0
        self._download_total = len(targets)
        self._current_source = ""
        for entry in targets:
            entry.state, entry.detail, entry.error = QUEUED, "", ""
            self._paint_entry(entry)
        self.progress.setValue(0)
        self.detail_text.clear()

        worker = DownloadWorker(
            self.source_links(),
            self.download_dir,
            self,
            resolved_links=[(entry.source, entry.direct) for entry in targets],
        )
        worker.log.connect(self.log)
        worker.item_started.connect(self._download_started)
        worker.progress.connect(self.update_progress)
        worker.item_done.connect(self._download_item_done)
        worker.failed.connect(self._download_failed)
        worker.expired.connect(self._download_expired)
        worker.all_done.connect(self._download_finished)
        self.download_worker = worker
        worker.start()

        self.file_label.setText(f"Starting {plural(len(targets), 'download')}")
        self._set_status(f"File 1 of {len(targets)}", "DOWNLOADING")
        self._update_queue_summary()
        self._sync_actions()

    def _download_started(self, source: str, filename: str) -> None:
        self._current_source = source
        self._download_index += 1
        entry = self.entries.get(source)
        if entry is not None:
            entry.state, entry.detail = DOWNLOADING, "Starting…"
            self._paint_entry(entry)
        self.file_label.setText(filename)
        self.progress.setValue(0)
        self.detail_text.clear()
        self._set_status(f"File {self._download_index} of {self._download_total}", "DOWNLOADING")
        self._update_queue_summary()

    def update_progress(self, done: int, total: int, speed: float) -> None:
        done, total, speed = int(done), int(total), float(speed)
        fraction = min(done / total, 1.0) if total else 0.0
        self.progress.setValue(int(fraction * 1000))
        details = [f"{fraction:.0%}"] if total else []
        if speed > 0:
            details.append(f"{format_size(speed)}/s")
        size = f"{format_size(done)} of {format_size(total)}" if total else format_size(done)
        details.append(size)
        if speed > 0 and total > done:
            details.append(f"{format_duration((total - done) / speed)} left")
        self.detail_text.setText(" · ".join(details))

        entry = self.entries.get(self._current_source)
        if entry is not None and entry.state == DOWNLOADING and not self._paused:
            row = [f"{fraction:.0%}" if total else format_size(done)]
            if speed > 0:
                row.append(f"{format_size(speed)}/s")
            entry.detail = " · ".join(row)
            self._paint_entry(entry)

    def _download_item_done(self, source: str) -> None:
        entry = self.entries.get(source)
        if entry is not None:
            entry.state, entry.detail, entry.error = DONE, "", ""
            self._paint_entry(entry)
        self.progress.setValue(1000)
        self._update_queue_summary()
        self._schedule_session_save()

    def _download_failed(self, source: str, error: str) -> None:
        self._failed_downloads += 1
        self.log(f"{self._queue_label(source) if source else 'Download'} failed: {error}")
        entry = self.entries.get(source)
        if entry is not None:
            entry.state, entry.detail, entry.error = ERROR, "", error
            self._paint_entry(entry)
        self._update_queue_summary()
        self._schedule_session_save()

    def _download_expired(self, source: str, error: str) -> None:
        self._failed_downloads += 1
        self.log(f"{self._queue_label(source)}: {error}")
        entry = self.entries.get(source)
        if entry is None:
            return
        if FuckingFastResolver.is_direct_link(entry.source):
            entry.state, entry.checked = ERROR, False
            entry.error = "This direct link expired. Paste its share link instead."
        else:
            entry.direct, entry.state = "", FAILED
            entry.error = "Download link expired. Prepare it again."
        entry.detail = ""
        self._paint_entry(entry)
        self._update_queue_summary()
        self._schedule_session_save()

    def _download_finished(self) -> None:
        self._active_download = False
        self._paused = False
        self._current_source = ""
        for entry in self.entries.values():
            if entry.state in (QUEUED, DOWNLOADING):
                entry.state, entry.detail = READY, ""
                self._paint_entry(entry)
        self.detail_text.clear()
        if self._download_cancelled:
            self.file_label.setText("Download stopped")
            self._set_status("Partial files resume where they left off", "READY")
        elif self._failed_downloads:
            self.file_label.setText(f"{plural(self._failed_downloads, 'file')} failed")
            self._set_status("Check the queue and try again", "ERROR")
        else:
            self.file_label.setText("All downloads complete")
            self._set_status(f"Saved to {self.download_dir}", "DONE")
            self.progress.setValue(1000)
        self.log("Download session finished")
        QtWidgets.QApplication.alert(self)
        self._update_queue_summary()
        self._sync_actions()
        self._schedule_session_save()

    def toggle_pause(self) -> None:
        if self.download_worker is None or not self._active_download:
            return
        self._paused = not self._paused
        if self._paused:
            self.download_worker.pause()
            self._set_status("Paused", "PAUSED")
        else:
            self.download_worker.resume()
            self._set_status(
                f"File {max(self._download_index, 1)} of {self._download_total}", "DOWNLOADING"
            )
        entry = self.entries.get(self._current_source)
        if entry is not None and entry.state == DOWNLOADING and self._paused:
            entry.detail = "Paused"
            self._paint_entry(entry)
        self._sync_actions()

    def cancel_download(self) -> None:
        if self.download_worker is None or not self._active_download:
            return
        self._download_cancelled = True
        self.download_worker.cancel()
        self._set_status("Stopping…", "STOPPING")

    def toggle_details(self) -> None:
        self._details_open = not self._details_open
        self.log_view.setVisible(self._details_open)
        self.details_btn.setText("Hide log" if self._details_open else "Log")

    # ------------------------------------------------------- browser engine

    def _check_browser(self) -> None:
        if self._browser_installing:
            return
        if browser_installed():
            self._set_browser_notice("hidden")
        elif self._browser_mode != "error":
            self._set_browser_notice("missing")

    def _set_browser_notice(self, mode: str, error: str = "") -> None:
        self._browser_mode = mode
        self.browser_notice.setVisible(mode != "hidden")
        self.browser_progress.setVisible(mode == "installing")
        self._set_tone(self.browser_notice, "danger" if mode == "error" else "accent")
        self.browser_btn.setEnabled(True)
        if mode == "installing":
            self.browser_progress.setRange(0, 1000)
            self.browser_progress.setValue(0)
            self.browser_label.setText("Starting browser engine download…")
            self._set_button(self.browser_btn, "Cancel", "stop")
        elif mode == "error":
            self.browser_label.setText(f"Browser engine download failed: {error}")
            self._set_button(self.browser_btn, "Retry", "refresh")
        else:
            self.browser_label.setText(
                "Browser engine needed for share links · one-time ~660 MB download"
            )
            self._set_button(self.browser_btn, "Install", "download")
        self._refresh_solar_icons()

    def _browser_button_clicked(self) -> None:
        if not self._browser_installing:
            self.install_browser()
            return
        worker = self.browser_worker if self._browser_install_running() else self.resolve_worker
        if worker is not None:
            worker.cancel()
        self.browser_btn.setEnabled(False)
        self.browser_label.setText("Cancelling…")

    def install_browser(self) -> None:
        if self._browser_installing or self._resolving() or self._browser_install_running():
            return
        self._dispose(self.browser_worker)
        worker = BrowserInstallWorker(self)
        worker.log.connect(self.log)
        worker.install_started.connect(self._browser_install_started)
        worker.browser_progress.connect(self._browser_install_progress)
        worker.install_finished.connect(self._browser_install_finished)
        worker.finished.connect(self._browser_worker_finished)
        self.browser_worker = worker
        worker.start()
        self._sync_actions()

    def _browser_worker_finished(self) -> None:
        self._sync_actions()
        if self._prepare_queued:
            self._prepare_queued = False
            self.resolve_links()

    def _browser_install_started(self) -> None:
        self._browser_installing = True
        self._browser_meter.reset()
        self._set_browser_notice("installing")
        self._sync_actions()

    def _browser_install_progress(self, done: int, total: int) -> None:
        done, total = int(done), int(total)
        if total and done >= total:
            self.browser_progress.setRange(0, 0)
            self.browser_label.setText("Installing browser engine…")
            return
        speed = self._browser_meter.update(done)
        parts = ["Downloading browser engine"]
        parts.append(f"{done / total:.0%}" if total else format_size(done))
        if speed > 0:
            parts.append(f"{format_size(speed)}/s")
        if total:
            parts.append(f"{format_size(done)} of {format_size(total)}")
        self.browser_progress.setRange(0, 1000)
        self.browser_progress.setValue(int(done / total * 1000) if total else 0)
        self.browser_label.setText(" · ".join(parts))

    def _browser_install_finished(self, ok: bool, error: str) -> None:
        self._browser_installing = False
        if ok:
            self._set_browser_notice("hidden")
            self.log("Browser engine installed")
        elif error:
            self._set_browser_notice("error", error)
            self.log(f"Browser engine download failed: {error}")
            self._set_status("Browser engine download failed", "ERROR")
        else:
            self._set_browser_notice("missing")
            self._set_status("Browser engine download cancelled", "READY")
        self._sync_actions()

    # -------------------------------------------------------------- session

    def _schedule_session_save(self) -> None:
        self._session_timer.start()

    def _session_data(self) -> dict:
        return {
            "links": self.link_input.toPlainText(),
            "expansions": dict(self.expansions),
            "entries": [
                {
                    "source": entry.source,
                    "direct": entry.direct,
                    "state": entry.state,
                    "error": entry.error,
                    "checked": entry.checked,
                    "prepared_at": entry.prepared_at,
                }
                for entry in self._visible_entries()
            ],
            "geometry": self.saveGeometry().toBase64().data().decode("ascii"),
        }

    def _save_session(self) -> None:
        self._session_timer.stop()
        if not save_session(self._session_data()):
            self.log("Could not save the session")

    def _restore_session(self) -> None:
        data = load_session()
        geometry = data.get("geometry")
        if isinstance(geometry, str) and geometry:
            self.restoreGeometry(QtCore.QByteArray.fromBase64(geometry.encode("ascii", "ignore")))
        entries = data.get("entries")
        now = time.time()
        for raw in entries if isinstance(entries, list) else []:
            entry = self._entry_from_session(raw, now)
            if entry is not None:
                self.entries[entry.source] = entry
        expansions = data.get("expansions")
        if isinstance(expansions, dict):
            self.expansions = {
                str(origin): [str(source) for source in sources]
                for origin, sources in expansions.items()
                if isinstance(sources, list)
            }
        links = data.get("links")
        if isinstance(links, str) and links.strip():
            self.link_input.setPlainText(links)
            self._set_status("Restored your last session", "READY")

    @classmethod
    def _entry_from_session(cls, raw: object, now: float) -> QueueEntry | None:
        if not isinstance(raw, dict) or not isinstance(raw.get("source"), str):
            return None
        state = raw.get("state")
        prepared_at = raw.get("prepared_at")
        entry = QueueEntry(
            source=raw["source"],
            direct=str(raw.get("direct") or ""),
            state=state if isinstance(state, str) and state in STATUS_LABELS else PENDING,
            error=str(raw.get("error") or ""),
            checked=raw.get("checked") is not False,
            prepared_at=float(prepared_at) if isinstance(prepared_at, (int, float)) else 0.0,
        )
        # An interrupted download resumes from its .part file on the next run.
        if entry.state in (PREPARING, QUEUED, DOWNLOADING):
            entry.state = READY
        if cls._is_stale(entry, now):
            entry.direct = ""
        if entry.state in (READY, ERROR) and not entry.direct:
            entry.state = PENDING
        return entry

    # --------------------------------------------------------------- status

    def _sync_actions(self) -> None:
        entries = self._visible_entries()
        resolving = self._resolving()
        can_prepare = any(entry.checked and entry.state in (PENDING, FAILED) for entry in entries)
        downloadable = [
            entry
            for entry in entries
            if entry.checked and entry.direct and entry.state in (READY, ERROR)
        ]
        resumable = not self._active_download and any(map(self._has_partial, downloadable))

        self._set_button(
            self.resolve_btn,
            "Stop" if resolving else "Prepare",
            "stop" if resolving else "refresh",
        )
        self.resolve_btn.setEnabled(
            resolving or (can_prepare and not self._browser_install_running())
        )
        self.copy_btn.setEnabled(any(entry.direct for entry in entries))
        self.clear_btn.setEnabled(
            bool(self.link_input.toPlainText().strip())
            and not resolving
            and not self._active_download
        )
        self._set_button(self.download_btn, "Resume" if resumable else "Download", "download")
        self.download_btn.setEnabled(bool(downloadable) and not self._active_download)
        self.download_btn.setVisible(not self._active_download)
        self.pause_resume_btn.setVisible(self._active_download)
        self.cancel_btn.setVisible(self._active_download)
        self._set_button(
            self.pause_resume_btn,
            "Resume" if self._paused else "Pause",
            "play" if self._paused else "pause",
        )
        self.folder_btn.setEnabled(not self._active_download)
        self._refresh_solar_icons()

    @staticmethod
    def _set_button(button: QtWidgets.QPushButton, text: str, icon: str) -> None:
        button.setText(text)
        button.setProperty("solarIcon", icon)

    @staticmethod
    def _set_tone(widget: QtWidgets.QWidget, tone: str) -> None:
        if widget.property("tone") == tone:
            return
        widget.setProperty("tone", tone)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_status(self, text: str, state: str) -> None:
        self.status_text.setText(text)
        self.state_pill.setText(state)
        if state == "ERROR":
            tone = "danger"
        elif state in {"PAUSED", "STOPPING"}:
            tone = "muted"
        else:
            tone = "accent"
        self._set_tone(self.state_pill, tone)

    def _notify(self, text: str) -> None:
        self.status_text.setText(text)

    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        color = self.palette["subtle"]
        self.log_view.append(
            f'<span style="color:{color}">{stamp}</span>&nbsp;&nbsp;{safe}'
        )
