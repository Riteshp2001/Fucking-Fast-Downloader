from __future__ import annotations

import re
import typing
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from PyQt5 import QtCore, QtGui, QtWidgets

from ff_downloader.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR
from ff_downloader.ui.brand_assets import application_icon, brand_mark
from ff_downloader.ui.solar_icons import SolarIconFactory
from ff_downloader.workers import DownloadWorker, ResolveWorker


class LinkInput(QtWidgets.QPlainTextEdit):
    """Multiline URL input that can distinguish a paste from normal typing."""

    pasted = QtCore.pyqtSignal()

    def insertFromMimeData(self, source: QtCore.QMimeData) -> None:
        super().insertFromMimeData(source)
        self.pasted.emit()


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
        self.resolve_worker: ResolveWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.download_dir = DOWNLOADS_DIR
        self.resolved_pairs: list[tuple[str, str]] = []
        self.resolution_failures: list[tuple[str, str]] = []
        self._active_download = False
        self._paused = False
        self._details_open = False
        self._source_revision = ""
        self._resolve_revision = ""
        self._prepared_revision = ""
        self._failed_downloads = 0

        self._build_ui()
        self._connect()
        self._apply_theme()
        self._sync_actions()

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

    def _section_heading(self, icon: str, title: str, subtitle: str):
        row = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel()
        icon_label.setProperty("solarLabel", icon)
        icon_label.setFixedSize(24, 24)
        row.addWidget(icon_label, 0, QtCore.Qt.AlignTop)

        text = QtWidgets.QVBoxLayout()
        text.setSpacing(2)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("sectionTitle")
        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setObjectName("helper")
        subtitle_label.setWordWrap(True)
        text.addWidget(title_label)
        text.addWidget(subtitle_label)
        row.addLayout(text, 1)
        return row

    def _metric(self, title: str, value: str):
        frame = QtWidgets.QFrame()
        frame.setObjectName("metricCard")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        label = QtWidgets.QLabel(title.upper())
        label.setObjectName("metricLabel")
        value_label = QtWidgets.QLabel(value)
        value_label.setObjectName("metricValue")
        layout.addWidget(label)
        layout.addWidget(value_label)
        return frame, value_label

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
        body.setContentsMargins(30, 22, 30, 16)
        body.setSpacing(14)
        body.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)

        hero = QtWidgets.QHBoxLayout()
        hero_text = QtWidgets.QVBoxLayout()
        hero_text.setSpacing(4)
        eyebrow = QtWidgets.QLabel("DOWNLOAD MANAGER")
        eyebrow.setObjectName("eyebrow")
        title = QtWidgets.QLabel("Download files")
        title.setObjectName("appTitle")
        subtitle = QtWidgets.QLabel(
            "Paste your links, prepare the queue, and download when you are ready."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        hero_text.addWidget(eyebrow)
        hero_text.addWidget(title)
        hero_text.addWidget(subtitle)
        hero.addLayout(hero_text, 1)

        self.folder_btn = self._button("Save folder", "folder", compact=True)
        hero.addWidget(self.folder_btn, 0, QtCore.Qt.AlignBottom)
        body.addLayout(hero)

        self.link_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.link_splitter.setChildrenCollapsible(False)
        self.link_splitter.setHandleWidth(16)
        self.link_splitter.setMinimumHeight(300)

        source_card = QtWidgets.QFrame()
        source_card.setObjectName("card")
        source_layout = QtWidgets.QVBoxLayout(source_card)
        source_layout.setContentsMargins(18, 14, 18, 14)
        source_layout.setSpacing(8)
        source_layout.addLayout(
            self._section_heading(
                "paste",
                "Paste links",
                "One URL per line. Duplicates are ignored.",
            )
        )

        self.link_input = LinkInput()
        self.link_input.setObjectName("linkInput")
        self.link_input.setPlaceholderText(
            "Paste public share or direct download URLs here…"
        )
        self.link_input.setMinimumHeight(130)
        source_layout.addWidget(self.link_input, 1)

        source_footer = QtWidgets.QHBoxLayout()
        self.source_count = QtWidgets.QLabel("0 links")
        self.source_count.setObjectName("pill")
        self.input_hint = QtWidgets.QLabel("Paste to prepare automatically")
        self.input_hint.setObjectName("hint")
        self.resolve_btn = self._button("Prepare", "link", compact=True)
        source_footer.addWidget(self.source_count)
        source_footer.addWidget(self.input_hint)
        source_footer.addStretch(1)
        source_footer.addWidget(self.resolve_btn)
        source_layout.addLayout(source_footer)
        self.link_splitter.addWidget(source_card)

        resolved_card = QtWidgets.QFrame()
        resolved_card.setObjectName("card")
        resolved_layout = QtWidgets.QVBoxLayout(resolved_card)
        resolved_layout.setContentsMargins(18, 16, 18, 16)
        resolved_layout.setSpacing(12)

        resolved_head = QtWidgets.QHBoxLayout()
        resolved_head.addLayout(
            self._section_heading(
                "link",
                "Download queue",
                "Prepared files appear here.",
            ),
            1,
        )
        self.resolved_count = QtWidgets.QLabel("Waiting")
        self.resolved_count.setObjectName("pill")
        self.copy_btn = self._icon_button("copy", "Copy prepared direct URLs")
        resolved_head.addWidget(self.resolved_count, 0, QtCore.Qt.AlignTop)
        resolved_head.addWidget(self.copy_btn, 0, QtCore.Qt.AlignTop)
        resolved_layout.addLayout(resolved_head)

        self.resolved_list = QtWidgets.QTreeWidget()
        self.resolved_list.setObjectName("resolvedList")
        self.resolved_list.setHeaderLabels(["File", "Status"])
        self.resolved_list.setRootIsDecorated(False)
        self.resolved_list.setAlternatingRowColors(False)
        self.resolved_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.resolved_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.resolved_list.header().setStretchLastSection(True)
        self.resolved_list.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        self.resolve_empty = QtWidgets.QLabel(
            "Paste a link above to build your download queue."
        )
        self.resolve_empty.setObjectName("emptyState")
        self.resolve_empty.setAlignment(QtCore.Qt.AlignCenter)
        self.resolve_empty.setWordWrap(True)
        self.queue_stack = QtWidgets.QStackedWidget()
        self.queue_stack.addWidget(self.resolve_empty)
        self.queue_stack.addWidget(self.resolved_list)
        resolved_layout.addWidget(self.queue_stack)
        self.link_splitter.addWidget(resolved_card)
        self.link_splitter.setStretchFactor(0, 1)
        self.link_splitter.setStretchFactor(1, 1)
        self.link_splitter.setSizes([560, 560])
        body.addWidget(self.link_splitter, 1)

        activity = QtWidgets.QFrame()
        activity.setObjectName("card")
        activity_layout = QtWidgets.QVBoxLayout(activity)
        activity_layout.setContentsMargins(18, 14, 18, 14)
        activity_layout.setSpacing(8)

        activity_head = QtWidgets.QHBoxLayout()
        activity_head.addLayout(
            self._section_heading(
                "download",
                "Download",
                "Save the queue to your selected folder.",
            ),
            1,
        )
        self.state_pill = QtWidgets.QLabel("READY")
        self.state_pill.setObjectName("statePill")
        activity_head.addWidget(self.state_pill, 0, QtCore.Qt.AlignTop)
        activity_layout.addLayout(activity_head)

        status_row = QtWidgets.QHBoxLayout()
        self.file_label = QtWidgets.QLabel("Prepare a link to enable downloading")
        self.file_label.setObjectName("fileName")
        self.file_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.path_label = QtWidgets.QLabel(str(self.download_dir))
        self.path_label.setObjectName("pathLabel")
        self.path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.path_label.setToolTip(str(self.download_dir))
        status_row.addWidget(self.file_label, 1)
        status_row.addWidget(self.path_label, 0)
        activity_layout.addLayout(status_row)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(9)
        activity_layout.addWidget(self.progress)

        action_row = QtWidgets.QHBoxLayout()
        self.progress_value = QtWidgets.QLabel("0% complete")
        self.progress_value.setObjectName("transferDetail")
        self.speed_value = QtWidgets.QLabel("0 MB/s")
        self.speed_value.setObjectName("transferDetail")
        self.size_value = QtWidgets.QLabel("0 / 0 MB")
        self.size_value.setObjectName("transferDetail")
        action_row.addWidget(self.progress_value)
        action_row.addWidget(self.speed_value)
        action_row.addWidget(self.size_value)
        action_row.addStretch(1)
        self.details_btn = self._button("Details", "document", compact=True)
        self.pause_resume_btn = self._button("Pause", "pause", compact=True)
        self.cancel_btn = self._button("Cancel", "stop", compact=True)
        self.download_btn = self._button("Download ready files", "download", primary=True)
        action_row.addWidget(self.details_btn)
        action_row.addWidget(self.pause_resume_btn)
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.download_btn)
        activity_layout.addLayout(action_row)

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(120)
        self.log_view.setVisible(False)
        activity_layout.addWidget(self.log_view)
        self.download_card = activity
        self.download_card.setVisible(True)
        body.addWidget(self.download_card)

        footer = QtWidgets.QHBoxLayout()
        self.status_icon = QtWidgets.QLabel()
        self.status_icon.setFixedSize(18, 18)
        self.status_text = QtWidgets.QLabel("Ready for links")
        self.status_text.setObjectName("footerText")
        footer.addWidget(self.status_icon)
        footer.addWidget(self.status_text)
        footer.addStretch(1)
        body.addLayout(footer)

    def _connect(self) -> None:
        self.link_input.textChanged.connect(self._source_changed)
        self.link_input.pasted.connect(self._auto_resolve_after_paste)
        self.resolve_btn.clicked.connect(self.resolve_links)
        self.copy_btn.clicked.connect(self.copy_resolved_links)
        self.folder_btn.clicked.connect(self.choose_folder)
        self.download_btn.clicked.connect(self.download_all)
        self.pause_resume_btn.clicked.connect(self.toggle_pause)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.details_btn.clicked.connect(self.toggle_details)
        self.resolved_list.customContextMenuRequested.connect(self._resolved_menu)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event: QtCore.QEvent) -> None:
        if event.type() == QtCore.QEvent.WindowStateChange:
            self.title_bar.set_maximized(self.isMaximized())
        super().changeEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)

    def toggle_theme(self) -> None:
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings.setValue("theme", self.theme)
        self._apply_theme()

    def _apply_theme(self) -> None:
        p = self.palette
        dark = self.theme == "dark"
        self.title_bar.apply_theme(p["text"], p["muted"], p["accent"], dark)
        self.status_icon.setPixmap(
            SolarIconFactory.icon("link", p["accent"], 16).pixmap(16, 16)
        )
        self._refresh_solar_icons()

        self.setStyleSheet(
            f"""
            QWidget#root {{ background: {p['bg']}; color: {p['text']}; }}
            QWidget#content {{ background: {p['bg']}; }}
            QLabel {{ color: {p['text']}; }}
            QFrame#titleBar {{ background: {p['title']}; border-bottom: 1px solid {p['border']}; }}
            QLabel#titleBrand {{ font-size: 13px; font-weight: 700; }}
            QLabel#titleVersion {{ color: {p['subtle']}; font-size: 10px; font-weight: 600; }}
            QPushButton#winButton, QPushButton#winClose {{ background: transparent; border: none; border-radius: 8px; }}
            QPushButton#winButton:hover {{ background: {p['surface_hover']}; }}
            QPushButton#winClose:hover {{ background: {p['danger']}; }}
            QLabel#eyebrow {{ color: {p['accent']}; font-size: 10px; font-weight: 750; letter-spacing: 1.5px; }}
            QLabel#appTitle {{ font-size: 24px; font-weight: 750; }}
            QLabel#subtitle {{ color: {p['muted']}; font-size: 12px; }}
            QLabel#sectionTitle {{ font-size: 15px; font-weight: 700; }}
            QLabel#helper, QLabel#hint, QLabel#pathLabel, QLabel#footerText, QLabel#transferDetail {{ color: {p['muted']}; }}
            QLabel#helper {{ font-size: 11px; }}
            QLabel#hint {{ font-size: 10px; }}
            QLabel#pathLabel {{ font-size: 10px; }}
            QLabel#transferDetail {{ font-size: 11px; font-weight: 600; }}
            QLabel#fileName {{ font-size: 14px; font-weight: 650; }}
            QLabel#emptyState {{ color: {p['subtle']}; font-size: 11px; padding: 18px; }}
            QLabel#pill, QLabel#statePill {{ background: {p['surface_alt']}; border: 1px solid {p['border']}; border-radius: 11px; padding: 4px 9px; color: {p['muted']}; font-size: 10px; font-weight: 700; }}
            QLabel#statePill {{ color: {p['accent']}; }}
            QFrame#card {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 12px; }}
            QFrame#metricCard {{ background: {p['surface_alt']}; border: 1px solid {p['border']}; border-radius: 10px; }}
            QLabel#metricLabel {{ color: {p['subtle']}; font-size: 9px; font-weight: 700; letter-spacing: .8px; }}
            QLabel#metricValue {{ font-size: 13px; font-weight: 700; }}
            QPushButton {{ background: {p['surface_alt']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 0 14px; font-weight: 650; }}
            QPushButton:hover {{ background: {p['surface_hover']}; border-color: {p['border_hover']}; }}
            QPushButton:pressed {{ padding-top: 1px; }}
            QPushButton:disabled {{ color: {p['subtle']}; border-color: {p['border']}; }}
            QPushButton[primary="true"] {{ background: {p['accent']}; color: {p['accent_text']}; border-color: {p['accent']}; padding: 0 20px; }}
            QPushButton[primary="true"]:hover {{ background: {p['accent_hover']}; border-color: {p['accent_hover']}; }}
            QPushButton[iconOnly="true"] {{ padding: 0; }}
            QPlainTextEdit#linkInput, QTreeWidget#resolvedList, QTextEdit#logView {{ background: {p['surface_alt']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 10px; selection-background-color: {p['selection']}; selection-color: {p['text']}; }}
            QPlainTextEdit#linkInput {{ padding: 12px; font-size: 11px; }}
            QPlainTextEdit#linkInput:focus, QTreeWidget#resolvedList:focus {{ border-color: {p['accent']}; }}
            QTreeWidget#resolvedList {{ outline: none; }}
            QTreeWidget#resolvedList::item {{ min-height: 30px; padding: 3px 6px; border-radius: 6px; }}
            QTreeWidget#resolvedList::item:hover {{ background: {p['surface_hover']}; }}
            QHeaderView::section {{ background: {p['surface']}; color: {p['muted']}; border: none; border-bottom: 1px solid {p['border']}; padding: 7px; font-size: 10px; font-weight: 650; }}
            QTextEdit#logView {{ padding: 8px; color: {p['muted']}; font-family: 'Cascadia Mono', 'Consolas', monospace; font-size: 10px; }}
            QProgressBar {{ background: {p['surface_alt']}; border: 1px solid {p['border']}; border-radius: 5px; }}
            QProgressBar::chunk {{ background: {p['accent']}; border-radius: 4px; }}
            QSplitter::handle {{ background: transparent; }}
            QMenu {{ background: {p['surface']}; color: {p['text']}; border: 1px solid {p['border']}; padding: 4px; }}
            QMenu::item {{ padding: 7px 24px 7px 12px; border-radius: 6px; }}
            QMenu::item:selected {{ background: {p['selection']}; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {p['border_hover']}; min-height: 28px; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            """
        )

    def _refresh_solar_icons(self) -> None:
        p = self.palette
        for button in self.findChildren(QtWidgets.QPushButton):
            name = button.property("solarIcon")
            if not name:
                continue
            primary = bool(button.property("primary"))
            if button.objectName() in {"winButton", "winClose"}:
                color = p["muted"]
            else:
                color = p["accent_text"] if primary else p["text"]
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

    def _source_changed(self) -> None:
        links = self.source_links()
        self.source_count.setText(
            f"{len(links)} link" if len(links) == 1 else f"{len(links)} links"
        )
        revision = "\n".join(links)
        if revision != self._source_revision:
            self._source_revision = revision
            self.resolved_pairs.clear()
            self.resolution_failures.clear()
            self._prepared_revision = ""
            self.resolved_list.clear()
            self.resolved_count.setText("Waiting" if not links else "Not resolved")
            self.resolve_empty.setText("Paste a link above to build your download queue.")
            self.queue_stack.setCurrentWidget(self.resolve_empty)
            self.file_label.setText("Prepare a link to enable downloading")
        self._sync_actions()

    def _auto_resolve_after_paste(self) -> None:
        QtCore.QTimer.singleShot(250, self.resolve_links)

    def resolve_links(self) -> None:
        links = self.source_links()
        if not links:
            self._set_status("Paste at least one link first", "READY")
            return
        if self.resolve_worker and self.resolve_worker.isRunning():
            return

        self.resolve_btn.setEnabled(False)
        self._resolve_revision = "\n".join(links)
        self.resolved_count.setText("Resolving…")
        self.resolve_empty.setText("Preparing links… A browser check may need your attention.")
        self.queue_stack.setCurrentWidget(self.resolve_empty)
        self._set_status(f"Resolving {len(links)} link(s)…", "RESOLVING")
        self.resolve_worker = ResolveWorker(links, self)
        self.resolve_worker.log.connect(self.log)
        self.resolve_worker.completed.connect(self._show_resolution)
        self.resolve_worker.failed.connect(self._resolve_failed)
        self.resolve_worker.finished.connect(self._resolve_finished)
        self.resolve_worker.start()

    def _resolve_finished(self) -> None:
        self._sync_actions()

    def _resolve_failed(self, error: str) -> None:
        self.resolved_pairs.clear()
        self.resolution_failures.clear()
        self._prepared_revision = ""
        self.resolved_list.clear()
        self.resolved_count.setText("Failed")
        self.resolve_empty.setText(
            "These links could not be prepared. Check the original URLs and try again."
        )
        self.queue_stack.setCurrentWidget(self.resolve_empty)
        self._set_status("Resolve failed", "ERROR")
        self.file_label.setText("No files are ready to download")
        self.log(f"Resolve failed: {error}")
        self._sync_actions()

    def _show_resolution(self, pairs: list, failures: list) -> None:
        if "\n".join(self.source_links()) != self._resolve_revision:
            self.log("Ignored a prepared queue because the source links changed")
            return
        self.resolved_pairs = [(str(source), str(direct)) for source, direct in pairs]
        self.resolution_failures = [(str(source), str(error)) for source, error in failures]
        self._prepared_revision = self._resolve_revision
        self.resolved_list.clear()
        for source, direct in self.resolved_pairs:
            item = QtWidgets.QTreeWidgetItem([self._queue_label(source), "Ready"])
            item.setData(0, QtCore.Qt.UserRole, source)
            item.setData(1, QtCore.Qt.UserRole, direct)
            item.setToolTip(0, source)
            item.setToolTip(1, direct)
            self.resolved_list.addTopLevelItem(item)
        for source, error in self.resolution_failures:
            item = QtWidgets.QTreeWidgetItem([self._queue_label(source), "Needs attention"])
            item.setData(0, QtCore.Qt.UserRole, source)
            item.setToolTip(0, source)
            item.setToolTip(1, error)
            self.resolved_list.addTopLevelItem(item)
        count = len(self.resolved_pairs)
        failed = len(self.resolution_failures)
        self.resolved_count.setText(f"{count} ready" if not failed else f"{count} ready · {failed} check")
        self.queue_stack.setCurrentWidget(
            self.resolved_list if count + failed else self.resolve_empty
        )
        if count:
            status = f"Prepared {count} download" if count == 1 else f"Prepared {count} downloads"
            if failed:
                status += f"; {failed} need attention"
            self._set_status(status, "READY")
            self.file_label.setText(
                f"{count} file ready to download" if count == 1 else f"{count} files ready to download"
            )
        else:
            self._set_status("No downloads could be prepared", "ERROR")
            self.file_label.setText("No files are ready to download")
        self.log(f"Prepared {count} direct link(s); {failed} need attention")
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

    def copy_resolved_links(self) -> None:
        if not self.resolved_pairs:
            self._set_status("Nothing resolved yet", "READY")
            return
        direct = [pair[1] for pair in self.resolved_pairs]
        QtWidgets.QApplication.clipboard().setText("\n".join(direct))
        self._set_status(f"Copied {len(direct)} direct link(s)", "READY")

    def _resolved_menu(self, position: QtCore.QPoint) -> None:
        item = self.resolved_list.itemAt(position)
        if item is None:
            return
        menu = QtWidgets.QMenu(self)
        copy_direct = menu.addAction("Copy direct link")
        copy_source = menu.addAction("Copy source link")
        copy_direct.setEnabled(bool(item.data(1, QtCore.Qt.UserRole)))
        action = menu.exec_(self.resolved_list.viewport().mapToGlobal(position))
        if action is copy_direct:
            QtWidgets.QApplication.clipboard().setText(
                str(item.data(1, QtCore.Qt.UserRole))
            )
        elif action is copy_source:
            QtWidgets.QApplication.clipboard().setText(
                str(item.data(0, QtCore.Qt.UserRole))
            )

    def choose_folder(self) -> None:
        selected = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose download folder", str(self.download_dir)
        )
        if selected:
            self.download_dir = Path(selected)
            self.path_label.setText(selected)
            self.path_label.setToolTip(selected)
            self._set_status("Download folder updated", "READY")

    def download_all(self) -> None:
        links = self.source_links()
        if not links:
            self._set_status("Paste at least one link first", "READY")
            return
        if not self.resolved_pairs or self._prepared_revision != "\n".join(links):
            self._set_status("Prepare at least one working link before downloading", "READY")
            return
        if self._active_download:
            return

        self._active_download = True
        self._paused = False
        self._failed_downloads = 0
        self.progress.setValue(0)
        self._set_status("Download session started", "ACTIVE")
        self.download_worker = DownloadWorker(
            links,
            self.download_dir,
            self,
            resolved_links=self.resolved_pairs,
        )
        self.download_worker.log.connect(self.log)
        self.download_worker.current_file.connect(self.file_label.setText)
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.failed.connect(self._download_failed)
        self.download_worker.all_done.connect(self._download_finished)
        self.download_worker.start()
        self._sync_actions()

    def toggle_pause(self) -> None:
        if not self.download_worker or not self._active_download:
            return
        if self._paused:
            self.download_worker.resume()
            self._paused = False
            self._set_status("Download resumed", "ACTIVE")
        else:
            self.download_worker.pause()
            self._paused = True
            self._set_status("Download paused", "PAUSED")
        self._sync_actions()

    def cancel_download(self) -> None:
        if self.download_worker and self._active_download:
            self.download_worker.cancel()
            self._set_status("Cancelling…", "CANCELLING")

    def _download_failed(self, link: str, error: str) -> None:
        self._failed_downloads += 1
        self._set_status("One item failed", "ERROR")
        self.log(f"Failed {link}: {error}")

    def _download_finished(self) -> None:
        self._active_download = False
        self._paused = False
        if self._failed_downloads:
            self._set_status(
                f"Download finished; {self._failed_downloads} item(s) need attention", "ERROR"
            )
        else:
            self._set_status("Download complete", "READY")
        self.log("Download session finished")
        self._sync_actions()

    def update_progress(self, done: int, total: int, speed: float) -> None:
        fraction = done / total if total else 0
        self.progress.setValue(max(0, min(1000, int(fraction * 1000))))
        self.speed_value.setText(f"{speed / 1048576:.1f} MB/s")
        self.progress_value.setText(f"{fraction * 100:.1f}% complete")
        self.size_value.setText(
            f"{done / 1048576:.1f} / {total / 1048576:.1f} MB"
        )

    def toggle_details(self) -> None:
        self._details_open = not self._details_open
        self.log_view.setVisible(self._details_open)
        self.details_btn.setText("Hide details" if self._details_open else "Details")

    def _sync_actions(self) -> None:
        has_links = bool(self.source_links())
        resolving = bool(self.resolve_worker and self.resolve_worker.isRunning())
        prepared = bool(self.resolved_pairs) and self._prepared_revision == "\n".join(
            self.source_links()
        )
        self.resolve_btn.setEnabled(
            has_links and not resolving and not self._active_download
        )
        self.copy_btn.setEnabled(prepared)
        self.download_btn.setEnabled(
            prepared and not self._active_download and not resolving
        )
        self.pause_resume_btn.setVisible(self._active_download)
        self.cancel_btn.setVisible(self._active_download)
        self.folder_btn.setEnabled(not self._active_download)
        self.pause_resume_btn.setText("Resume" if self._paused else "Pause")
        self.pause_resume_btn.setProperty(
            "solarIcon", "play" if self._paused else "pause"
        )
        self._refresh_solar_icons()

    def _set_status(self, text: str, state: str) -> None:
        self.status_text.setText(text)
        self.state_pill.setText(state)

    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        color = self.palette["subtle"]
        self.log_view.append(
            f'<span style="color:{color}">{stamp}</span>&nbsp;&nbsp;{safe}'
        )
