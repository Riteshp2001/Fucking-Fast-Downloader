from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt5 import QtCore
from requests.exceptions import RequestException

from ff_downloader.config import BETWEEN_LINK_DELAY, DOWNLOADS_DIR
from ff_downloader.core import (
    DownloadCancelled,
    DownloadEngine,
    FuckingFastResolver,
    LinkExpired,
    ResolutionError,
    browser_installed,
    ensure_browser_installed,
)


class _BrowserWorker(QtCore.QThread):
    """A worker that can download the browser engine and be stopped from the UI."""

    log = QtCore.pyqtSignal(str)
    install_started = QtCore.pyqtSignal()
    browser_progress = QtCore.pyqtSignal(object, object)
    install_finished = QtCore.pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = threading.Event()

    def cancel(self) -> None:
        self._stop.set()

    def _install_browser(self) -> bool:
        self.install_started.emit()
        try:
            ensure_browser_installed(self.log.emit, self.browser_progress.emit, self._stop)
        except Exception as exc:
            self.install_finished.emit(False, "" if self._stop.is_set() else str(exc))
            return False
        self.install_finished.emit(True, "")
        return True


class BrowserInstallWorker(_BrowserWorker):
    def run(self) -> None:
        self._install_browser()


class ResolveWorker(_BrowserWorker):
    expanded = QtCore.pyqtSignal(str, list)
    item_started = QtCore.pyqtSignal(str)
    item_resolved = QtCore.pyqtSignal(str, str)
    item_failed = QtCore.pyqtSignal(str, str)
    completed = QtCore.pyqtSignal(list, list)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, links: list[str], parent=None):
        super().__init__(parent)
        self.links = links

    def run(self) -> None:
        needs_browser = any(not FuckingFastResolver.is_direct_link(link) for link in self.links)
        if needs_browser and not browser_installed() and not self._install_browser():
            return
        resolver = FuckingFastResolver(self.log.emit, self._stop)
        try:
            batch = resolver.resolve_available(
                self.links,
                on_expanded=self.expanded.emit,
                on_started=self.item_started.emit,
                on_resolved=self.item_resolved.emit,
                on_failed=self.item_failed.emit,
            )
            pairs = [(item.source_url, item.direct_url) for item in batch.links]
            self.completed.emit(pairs, batch.failures)
        except ResolutionError as exc:
            self.failed.emit(str(exc))
        finally:
            resolver.close()


class DownloadWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    # object, not int: Qt's int is 32-bit and files can be larger than 2 GiB.
    progress = QtCore.pyqtSignal(object, object, float)
    item_size = QtCore.pyqtSignal(str, object, object)
    item_started = QtCore.pyqtSignal(str, str)
    item_done = QtCore.pyqtSignal(str, object)
    failed = QtCore.pyqtSignal(str, str)
    expired = QtCore.pyqtSignal(str, str)
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
        self.engine = DownloadEngine(self.progress.emit, self.log.emit)
        self._stop_probes = threading.Event()

    def pause(self) -> None:
        self.engine.pause()

    def resume(self) -> None:
        self.engine.resume()

    def cancel(self) -> None:
        self._stop_probes.set()
        self.engine.cancel()

    def _probe_item(self, source: str, direct: str, path: Path) -> None:
        if self._stop_probes.is_set():
            return
        try:
            done = self.engine.existing_bytes(path)
        except OSError:
            done = 0
        total = self.engine.probe_size(direct)
        if not self._stop_probes.is_set():
            self.item_size.emit(source, done if total is None else min(done, total), total)

    def run(self) -> None:
        probes = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ff-size")
        try:
            prepared = self.resolved_links or self._resolve_links()
            targets = []
            for source, direct in prepared:
                filename = self.engine.filename_from_link(source)
                path = self.directory / (filename or self.engine.filename_from_url(direct))
                targets.append((source, direct, path))
                probes.submit(self._probe_item, source, direct, path)
            for index, (source, direct, path) in enumerate(targets):
                try:
                    if index:
                        self._stop_probes.wait(BETWEEN_LINK_DELAY)
                    self.engine.checkpoint()
                    self.item_started.emit(source, path.name)
                    self.log.emit(f"Downloading {path.name}")
                    saved = self.engine.download(direct, path)
                    self.item_done.emit(source, saved.stat().st_size)
                except DownloadCancelled:
                    self.log.emit("Download cancelled")
                    break
                except LinkExpired as exc:
                    self.expired.emit(source, str(exc))
                except (RequestException, OSError, RuntimeError) as exc:
                    self.failed.emit(source, str(exc))
        except ResolutionError as exc:
            self.failed.emit("", str(exc))
        finally:
            self._stop_probes.set()
            probes.shutdown(wait=True, cancel_futures=True)
            self.all_done.emit()

    def _resolve_links(self) -> list[tuple[str, str]]:
        resolver = FuckingFastResolver(self.log.emit)
        try:
            batch = resolver.resolve_available(self.links)
        finally:
            resolver.close()
        for source, error in batch.failures:
            self.failed.emit(source, error)
        return [(item.source_url, item.direct_url) for item in batch.links]
