from __future__ import annotations

import time
from pathlib import Path

from PyQt5 import QtCore
from requests.exceptions import RequestException

from ff_downloader.config import BETWEEN_LINK_DELAY, DOWNLOADS_DIR
from ff_downloader.core import (
    DownloadCancelled,
    DownloadEngine,
    FuckingFastResolver,
    ResolutionError,
)


class ResolveWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    completed = QtCore.pyqtSignal(list, list)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, links: list[str], parent=None):
        super().__init__(parent)
        self.links = links

    def run(self) -> None:
        resolver = FuckingFastResolver(self.log.emit)
        try:
            batch = resolver.resolve_available(self.links)
            pairs = [(item.source_url, item.direct_url) for item in batch.links]
            self.completed.emit(pairs, batch.failures)
        except ResolutionError as exc:
            self.failed.emit(str(exc))
        finally:
            resolver.close()


class DownloadWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(int, int, float)
    current_file = QtCore.pyqtSignal(str)
    item_done = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str, str)
    all_done = QtCore.pyqtSignal()

    def __init__(
        self,
        links: list[str],
        directory: Path = DOWNLOADS_DIR,
        parent=None,
        *,
        resolved_links: list[tuple[str, str]] | None = None,
    ):
        super().__init__(parent)
        self.links = links
        self.directory = directory
        self.resolved_links = list(resolved_links or [])
        self.resolver: FuckingFastResolver | None = None
        self.engine: DownloadEngine | None = None

    def pause(self) -> None:
        if self.engine:
            self.engine.pause()

    def resume(self) -> None:
        if self.engine:
            self.engine.resume()

    def cancel(self) -> None:
        if self.engine:
            self.engine.cancel()

    def run(self) -> None:
        self.resolver = FuckingFastResolver(self.log.emit)
        self.engine = DownloadEngine(self.progress.emit, self.log.emit)
        try:
            prepared = self.resolved_links
            if not prepared:
                batch = self.resolver.resolve_available(self.links)
                prepared = [(item.source_url, item.direct_url) for item in batch.links]
                for source, error in batch.failures:
                    self.failed.emit(source, error)

            for index, (source, direct) in enumerate(prepared):
                try:
                    filename = self.engine.filename_from_link(source) or self.engine.filename_from_url(direct)
                    self.current_file.emit(filename)
                    self.log.emit(f"Downloading {filename}")
                    self.engine.download(direct, self.directory / filename)
                    self.item_done.emit(source)
                    self.log.emit(f"Finished {filename}")
                except DownloadCancelled:
                    self.log.emit("Download cancelled")
                    break
                except (ResolutionError, RequestException, OSError, RuntimeError) as exc:
                    self.failed.emit(source, str(exc))
                if index + 1 < len(prepared):
                    time.sleep(BETWEEN_LINK_DELAY)
        except ResolutionError as exc:
            self.failed.emit("", str(exc))
        finally:
            self.resolver.close()
            self.all_done.emit()
