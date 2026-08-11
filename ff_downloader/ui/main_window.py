from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5 import QtWidgets

from ff_downloader.config import APP_NAME, APP_VERSION, DOWNLOADS_DIR
from ff_downloader.workers import DownloadWorker, ResolveWorker


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(980, 680)
        self.resolve_worker: ResolveWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.download_dir = DOWNLOADS_DIR
        self._build_ui()
        self._connect()

    def _build_ui(self) -> None:
        root = QtWidgets.QWidget(self)
        self.setCentralWidget(root)
        layout = QtWidgets.QVBoxLayout(root)

        title = QtWidgets.QLabel(APP_NAME)
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        subtitle = QtWidgets.QLabel("Resolve, validate and download public FuckingFast links")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        buttons = QtWidgets.QHBoxLayout()
        self.paste_btn = QtWidgets.QPushButton("Paste links")
        self.validate_btn = QtWidgets.QPushButton("Resolve links")
        self.copy_btn = QtWidgets.QPushButton("Copy resolved")
        self.download_btn = QtWidgets.QPushButton("Download all")
        self.folder_btn = QtWidgets.QPushButton("Choose folder")
        for button in (self.paste_btn, self.validate_btn, self.copy_btn, self.download_btn, self.folder_btn):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        splitter = QtWidgets.QSplitter()
        self.link_list = QtWidgets.QListWidget()
        self.link_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        splitter.addWidget(self.link_list)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        self.file_label = QtWidgets.QLabel("No active download")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1000)
        self.stats_label = QtWidgets.QLabel("0 MB / 0 MB   •   0 MB/s")
        controls = QtWidgets.QHBoxLayout()
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.resume_btn = QtWidgets.QPushButton("Resume")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.resume_btn)
        controls.addWidget(self.cancel_btn)
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        right_layout.addWidget(self.file_label)
        right_layout.addWidget(self.progress)
        right_layout.addWidget(self.stats_label)
        right_layout.addLayout(controls)
        right_layout.addWidget(self.log_view, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.statusBar().showMessage(str(self.download_dir))

    def _connect(self) -> None:
        self.paste_btn.clicked.connect(self.paste_links)
        self.validate_btn.clicked.connect(self.resolve_links)
        self.copy_btn.clicked.connect(self.copy_links)
        self.download_btn.clicked.connect(self.download_all)
        self.folder_btn.clicked.connect(self.choose_folder)
        self.pause_btn.clicked.connect(lambda: self.download_worker and self.download_worker.pause())
        self.resume_btn.clicked.connect(lambda: self.download_worker and self.download_worker.resume())
        self.cancel_btn.clicked.connect(lambda: self.download_worker and self.download_worker.cancel())

    def links(self) -> list[str]:
        return [self.link_list.item(i).text() for i in range(self.link_list.count())]

    def paste_links(self) -> None:
        raw = QtWidgets.QApplication.clipboard().text()
        links = [line.strip().strip('"').strip("'") for line in raw.splitlines() if line.strip()]
        self.link_list.clear()
        self.link_list.addItems(list(dict.fromkeys(links)))
        self.log(f"Loaded {len(links)} link(s)")

    def resolve_links(self) -> None:
        links = self.links()
        if not links:
            return
        self.resolve_worker = ResolveWorker(links, self)
        self.resolve_worker.log.connect(self.log)
        self.resolve_worker.resolved.connect(self._replace_links)
        self.resolve_worker.failed.connect(lambda error: self.log(f"Resolve failed: {error}"))
        self.resolve_worker.start()

    def _replace_links(self, links: list[str]) -> None:
        self.link_list.clear()
        self.link_list.addItems(links)
        self.log(f"Resolved {len(links)} direct link(s)")

    def copy_links(self) -> None:
        links = self.links()
        if not links:
            return
        text = "\n".join(f'"{link}"' for link in links)
        QtWidgets.QApplication.clipboard().setText(text)
        self.log(f"Copied {len(links)} link(s) for an external download manager")

    def choose_folder(self) -> None:
        selected = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose download folder", str(self.download_dir))
        if selected:
            self.download_dir = Path(selected)
            self.statusBar().showMessage(selected)

    def download_all(self) -> None:
        links = self.links()
        if not links:
            return
        self.download_worker = DownloadWorker(links, self.download_dir, self)
        self.download_worker.log.connect(self.log)
        self.download_worker.current_file.connect(self.file_label.setText)
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.item_done.connect(self._remove_link)
        self.download_worker.failed.connect(lambda link, error: self.log(f"Failed {link}: {error}"))
        self.download_worker.all_done.connect(lambda: self.log("Download session finished"))
        self.download_worker.start()

    def _remove_link(self, link: str) -> None:
        for index in range(self.link_list.count()):
            if self.link_list.item(index).text() == link:
                self.link_list.takeItem(index)
                break

    def update_progress(self, done: int, total: int, speed: float) -> None:
        ratio = int((done / total) * 1000) if total else 0
        self.progress.setValue(max(0, min(1000, ratio)))
        self.stats_label.setText(
            f"{done / 1048576:.1f} MB / {total / 1048576:.1f} MB   •   {speed / 1048576:.1f} MB/s"
        )

    def log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{stamp}] {message}")
