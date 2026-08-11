from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from ff_downloader.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR
from ff_downloader.ui.solar_icons import SolarIconFactory
from ff_downloader.workers import DownloadWorker, ResolveWorker


class MainWindow(QtWidgets.QMainWindow):
    ACCENT = "#7BDCB5"
    TEXT = "#E8EDF3"
    MUTED = "#8D99A8"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1120, 760)
        self.setMinimumSize(900, 620)
        self.resolve_worker: ResolveWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.download_dir = DOWNLOADS_DIR
        self._build_ui()
        self._connect()
        self._apply_theme()

    def _button(self, text: str, icon: str, primary: bool = False) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.setProperty("primary", primary)
        button.setIcon(SolarIconFactory.icon(icon, "#07110D" if primary else self.TEXT, 19))
        button.setIconSize(QtCore.QSize(19, 19))
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.setMinimumHeight(42)
        return button

    def _metric(self, title: str, value: str) -> tuple[QtWidgets.QFrame, QtWidgets.QLabel]:
        frame = QtWidgets.QFrame()
        frame.setObjectName("metricCard")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 11, 14, 11)
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
        shell.setContentsMargins(24, 20, 24, 22)
        shell.setSpacing(16)

        header = QtWidgets.QHBoxLayout()
        brand = QtWidgets.QVBoxLayout()
        eyebrow = QtWidgets.QLabel("DESKTOP DOWNLOAD MANAGER")
        eyebrow.setObjectName("eyebrow")
        title = QtWidgets.QLabel(APP_NAME)
        title.setObjectName("appTitle")
        subtitle = QtWidgets.QLabel("Resolve links, validate redirects and download without clutter.")
        subtitle.setObjectName("subtitle")
        brand.addWidget(eyebrow)
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch(1)
        self.folder_btn = self._button("Download folder", "folder")
        header.addWidget(self.folder_btn)
        shell.addLayout(header)

        action_bar = QtWidgets.QFrame()
        action_bar.setObjectName("actionBar")
        action_layout = QtWidgets.QHBoxLayout(action_bar)
        action_layout.setContentsMargins(10, 10, 10, 10)
        action_layout.setSpacing(8)
        self.paste_btn = self._button("Paste links", "paste")
        self.validate_btn = self._button("Resolve", "shield")
        self.copy_btn = self._button("Copy resolved", "copy")
        self.download_btn = self._button("Download all", "download", primary=True)
        action_layout.addWidget(self.paste_btn)
        action_layout.addWidget(self.validate_btn)
        action_layout.addWidget(self.copy_btn)
        action_layout.addStretch(1)
        action_layout.addWidget(self.download_btn)
        shell.addWidget(action_bar)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(12)

        queue_card = QtWidgets.QFrame()
        queue_card.setObjectName("card")
        queue_layout = QtWidgets.QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(16, 16, 16, 16)
        queue_layout.setSpacing(12)
        queue_head = QtWidgets.QHBoxLayout()
        queue_title = QtWidgets.QLabel("Link queue")
        queue_title.setObjectName("sectionTitle")
        self.queue_count = QtWidgets.QLabel("0 items")
        self.queue_count.setObjectName("pill")
        queue_head.addWidget(queue_title)
        queue_head.addStretch(1)
        queue_head.addWidget(self.queue_count)
        queue_layout.addLayout(queue_head)
        helper = QtWidgets.QLabel("Paste FuckingFast links or a supported source page. Resolved direct links replace the queue in-place.")
        helper.setObjectName("helper")
        helper.setWordWrap(True)
        queue_layout.addWidget(helper)
        self.link_list = QtWidgets.QListWidget()
        self.link_list.setObjectName("linkList")
        self.link_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.link_list.setAlternatingRowColors(False)
        self.link_list.setSpacing(2)
        queue_layout.addWidget(self.link_list, 1)
        splitter.addWidget(queue_card)

        activity_card = QtWidgets.QFrame()
        activity_card.setObjectName("card")
        activity_layout = QtWidgets.QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(18, 16, 18, 16)
        activity_layout.setSpacing(14)
        activity_head = QtWidgets.QHBoxLayout()
        activity_title = QtWidgets.QLabel("Download activity")
        activity_title.setObjectName("sectionTitle")
        self.state_pill = QtWidgets.QLabel("IDLE")
        self.state_pill.setObjectName("statePill")
        activity_head.addWidget(activity_title)
        activity_head.addStretch(1)
        activity_head.addWidget(self.state_pill)
        activity_layout.addLayout(activity_head)

        self.file_label = QtWidgets.QLabel("Nothing downloading yet")
        self.file_label.setObjectName("fileName")
        self.file_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        activity_layout.addWidget(self.file_label)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        activity_layout.addWidget(self.progress)

        metrics = QtWidgets.QHBoxLayout()
        speed_card, self.speed_value = self._metric("Speed", "0 MB/s")
        progress_card, self.progress_value = self._metric("Progress", "0%")
        size_card, self.size_value = self._metric("Transferred", "0 / 0 MB")
        metrics.addWidget(speed_card)
        metrics.addWidget(progress_card)
        metrics.addWidget(size_card)
        activity_layout.addLayout(metrics)

        controls = QtWidgets.QHBoxLayout()
        self.pause_btn = self._button("Pause", "pause")
        self.resume_btn = self._button("Resume", "play")
        self.cancel_btn = self._button("Cancel", "stop")
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.resume_btn)
        controls.addWidget(self.cancel_btn)
        controls.addStretch(1)
        activity_layout.addLayout(controls)

        log_head = QtWidgets.QHBoxLayout()
        log_title = QtWidgets.QLabel("Session log")
        log_title.setObjectName("subsectionTitle")
        self.path_label = QtWidgets.QLabel(str(self.download_dir))
        self.path_label.setObjectName("pathLabel")
        self.path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        log_head.addWidget(log_title)
        log_head.addStretch(1)
        log_head.addWidget(self.path_label)
        activity_layout.addLayout(log_head)
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        activity_layout.addWidget(self.log_view, 1)
        splitter.addWidget(activity_card)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        shell.addWidget(splitter, 1)

        footer = QtWidgets.QHBoxLayout()
        status_icon = QtWidgets.QLabel()
        status_icon.setPixmap(SolarIconFactory.icon("link", self.ACCENT, 16).pixmap(16, 16))
        self.status_text = QtWidgets.QLabel("Ready")
        self.status_text.setObjectName("footerText")
        version = QtWidgets.QLabel(f"v{APP_VERSION}")
        version.setObjectName("footerText")
        footer.addWidget(status_icon)
        footer.addWidget(self.status_text)
        footer.addStretch(1)
        footer.addWidget(version)
        shell.addLayout(footer)

    def _connect(self) -> None:
        self.paste_btn.clicked.connect(self.paste_links)
        self.validate_btn.clicked.connect(self.resolve_links)
        self.copy_btn.clicked.connect(self.copy_links)
        self.download_btn.clicked.connect(self.download_all)
        self.folder_btn.clicked.connect(self.choose_folder)
        self.pause_btn.clicked.connect(self.pause_download)
        self.resume_btn.clicked.connect(self.resume_download)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.link_list.model().rowsInserted.connect(lambda *_: self._sync_count())
        self.link_list.model().rowsRemoved.connect(lambda *_: self._sync_count())
        self.link_list.model().modelReset.connect(self._sync_count)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QWidget#root {{ background: #0B0E12; color: {self.TEXT}; }}
            QLabel {{ color: {self.TEXT}; }}
            QLabel#eyebrow {{ color: {self.ACCENT}; font-size: 10px; font-weight: 700; letter-spacing: 1.4px; }}
            QLabel#appTitle {{ font-size: 28px; font-weight: 750; }}
            QLabel#subtitle, QLabel#helper, QLabel#footerText, QLabel#pathLabel {{ color: {self.MUTED}; }}
            QLabel#subtitle {{ font-size: 12px; }}
            QLabel#helper {{ font-size: 11px; line-height: 1.4; }}
            QLabel#sectionTitle {{ font-size: 16px; font-weight: 700; }}
            QLabel#subsectionTitle {{ font-size: 12px; font-weight: 650; }}
            QLabel#fileName {{ font-size: 15px; font-weight: 650; padding: 2px 0; }}
            QLabel#pill, QLabel#statePill {{ background: #171D24; border: 1px solid #252D36; border-radius: 11px; padding: 4px 9px; color: #AAB5C2; font-size: 10px; font-weight: 700; }}
            QLabel#statePill {{ color: {self.ACCENT}; }}
            QFrame#card, QFrame#actionBar {{ background: #11151A; border: 1px solid #202730; border-radius: 16px; }}
            QFrame#metricCard {{ background: #0D1116; border: 1px solid #202730; border-radius: 12px; }}
            QLabel#metricLabel {{ color: #6F7B89; font-size: 9px; font-weight: 700; letter-spacing: .8px; }}
            QLabel#metricValue {{ font-size: 14px; font-weight: 700; }}
            QPushButton {{ background: #161B21; color: {self.TEXT}; border: 1px solid #28313B; border-radius: 10px; padding: 0 14px; font-weight: 600; }}
            QPushButton:hover {{ background: #1B222A; border-color: #394653; }}
            QPushButton:pressed {{ background: #0F1318; }}
            QPushButton[primary="true"] {{ background: {self.ACCENT}; color: #07110D; border-color: {self.ACCENT}; }}
            QPushButton[primary="true"]:hover {{ background: #8BE5C0; }}
            QListWidget#linkList, QTextEdit#logView {{ background: #0C1014; border: 1px solid #202730; border-radius: 12px; padding: 8px; selection-background-color: #24473B; selection-color: #F2FFF9; }}
            QListWidget#linkList::item {{ min-height: 34px; padding: 4px 8px; border-radius: 8px; }}
            QListWidget#linkList::item:hover {{ background: #141A20; }}
            QTextEdit#logView {{ color: #AAB4C0; font-family: 'Cascadia Mono', 'Consolas', monospace; font-size: 10px; }}
            QProgressBar {{ background: #1B2229; border: none; border-radius: 5px; }}
            QProgressBar::chunk {{ background: {self.ACCENT}; border-radius: 5px; }}
            QSplitter::handle {{ background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: #303944; min-height: 28px; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

    def links(self) -> list[str]:
        return [self.link_list.item(i).text() for i in range(self.link_list.count())]

    def _sync_count(self) -> None:
        count = self.link_list.count()
        self.queue_count.setText(f"{count} item" if count == 1 else f"{count} items")

    def paste_links(self) -> None:
        raw = QtWidgets.QApplication.clipboard().text()
        links = [line.strip().strip('"').strip("'") for line in raw.splitlines() if line.strip()]
        unique = list(dict.fromkeys(links))
        self.link_list.clear()
        self.link_list.addItems(unique)
        self._sync_count()
        self.status_text.setText(f"Loaded {len(unique)} link(s)")
        self.log(f"Loaded {len(unique)} link(s) from clipboard")

    def resolve_links(self) -> None:
        links = self.links()
        if not links:
            self.status_text.setText("Paste at least one link first")
            return
        self.state_pill.setText("RESOLVING")
        self.status_text.setText("Resolving links…")
        self.resolve_worker = ResolveWorker(links, self)
        self.resolve_worker.log.connect(self.log)
        self.resolve_worker.resolved.connect(self._replace_links)
        self.resolve_worker.failed.connect(self._resolve_failed)
        self.resolve_worker.start()

    def _resolve_failed(self, error: str) -> None:
        self.state_pill.setText("ERROR")
        self.status_text.setText("Resolve failed")
        self.log(f"Resolve failed: {error}")

    def _replace_links(self, links: list[str]) -> None:
        self.link_list.clear()
        self.link_list.addItems(links)
        self._sync_count()
        self.state_pill.setText("READY")
        self.status_text.setText(f"Resolved {len(links)} direct link(s)")
        self.log(f"Resolved {len(links)} direct link(s)")

    def copy_links(self) -> None:
        links = self.links()
        if not links:
            self.status_text.setText("Nothing to copy")
            return
        QtWidgets.QApplication.clipboard().setText("\n".join(f'"{link}"' for link in links))
        self.status_text.setText(f"Copied {len(links)} link(s)")
        self.log(f"Copied {len(links)} link(s) for an external download manager")

    def choose_folder(self) -> None:
        selected = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose download folder", str(self.download_dir))
        if selected:
            self.download_dir = Path(selected)
            self.path_label.setText(selected)
            self.status_text.setText("Download folder updated")

    def download_all(self) -> None:
        links = self.links()
        if not links:
            self.status_text.setText("Paste at least one link first")
            return
        self.state_pill.setText("ACTIVE")
        self.status_text.setText("Download session started")
        self.download_worker = DownloadWorker(links, self.download_dir, self)
        self.download_worker.log.connect(self.log)
        self.download_worker.current_file.connect(self.file_label.setText)
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.item_done.connect(self._remove_link)
        self.download_worker.failed.connect(self._download_failed)
        self.download_worker.all_done.connect(self._download_finished)
        self.download_worker.start()

    def pause_download(self) -> None:
        if self.download_worker:
            self.download_worker.pause()
            self.state_pill.setText("PAUSED")
            self.status_text.setText("Download paused")

    def resume_download(self) -> None:
        if self.download_worker:
            self.download_worker.resume()
            self.state_pill.setText("ACTIVE")
            self.status_text.setText("Download resumed")

    def cancel_download(self) -> None:
        if self.download_worker:
            self.download_worker.cancel()
            self.state_pill.setText("CANCELLING")
            self.status_text.setText("Cancelling…")

    def _download_failed(self, link: str, error: str) -> None:
        self.state_pill.setText("ERROR")
        self.status_text.setText("One item failed")
        self.log(f"Failed {link}: {error}")

    def _download_finished(self) -> None:
        self.state_pill.setText("IDLE")
        self.status_text.setText("Download session finished")
        self.log("Download session finished")

    def _remove_link(self, link: str) -> None:
        for index in range(self.link_list.count()):
            if self.link_list.item(index).text() == link:
                self.link_list.takeItem(index)
                break
        self._sync_count()

    def update_progress(self, done: int, total: int, speed: float) -> None:
        fraction = done / total if total else 0
        ratio = int(fraction * 1000)
        self.progress.setValue(max(0, min(1000, ratio)))
        self.speed_value.setText(f"{speed / 1048576:.1f} MB/s")
        self.progress_value.setText(f"{fraction * 100:.1f}%")
        self.size_value.setText(f"{done / 1048576:.1f} / {total / 1048576:.1f} MB")

    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.log_view.append(f'<span style="color:#66717E">{stamp}</span>&nbsp;&nbsp;{safe}')
