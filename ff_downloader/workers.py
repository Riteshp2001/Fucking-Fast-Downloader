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

_LAST_RESOLVED_INPUTS: tuple[str, ...] = ()
_LAST_RESOLVED_URLS: dict[str, str] = {}


def _clear_cached_resolution(links: list[str]) -> None:
    global _LAST_RESOLVED_INPUTS, _LAST_RESOLVED_URLS
    if _LAST_RESOLVED_INPUTS == tuple(links):
        _LAST_RESOLVED_INPUTS = ()
        _LAST_RESOLVED_URLS = {}


def _remember_resolution(links: list[str], pairs: list[tuple[str, str]]) -> None:
    global _LAST_RESOLVED_INPUTS, _LAST_RESOLVED_URLS
    _LAST_RESOLVED_INPUTS = tuple(links)
    _LAST_RESOLVED_URLS = dict(pairs)


def _cached_resolution(links: list[str]) -> dict[str, str]:
    if _LAST_RESOLVED_INPUTS != tuple(links):
        return {}
    return dict(_LAST_RESOLVED_URLS)


class ResolveWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    resolved = QtCore.pyqtSignal(list)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, links: list[str], parent=None):
        super().__init__(parent)
        self.links = links
        self.finished.connect(self._resolve_latest_parent_sources)

    @QtCore.pyqtSlot()
    def _resolve_latest_parent_sources(self) -> None:
        parent = self.parent()
        source_links = getattr(parent, "source_links", None)
        resolve_links = getattr(parent, "resolve_links", None)
        if not callable(source_links) or not callable(resolve_links):
            return
        current_links = source_links()
        if current_links and current_links != self.links:
            resolve_links()

    def run(self) -> None:
        resolver = FuckingFastResolver(self.log.emit)
        _clear_cached_resolution(self.links)
        try:
            results = resolver.resolve_many(self.links)
            pairs = [(item.source_url, item.direct_url) for item in results]
            _remember_resolution(self.links, pairs)
            self.resolved.emit(pairs)
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
        resolved_urls: dict[str, str] | None = None,
    ):
        super().__init__(parent)
        self.links = links
        self.directory = directory
        self.resolved_urls = resolved_urls or _cached_resolution(links)
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
            expanded = (
                list(self.resolved_urls)
                if self.resolved_urls
                else self.resolver.expand_sources(self.links)
            )
            for index, source in enumerate(expanded):
                try:
                    direct = self.resolved_urls.get(source) or self.resolver.resolve(source)
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
                if index + 1 < len(expanded):
                    time.sleep(BETWEEN_LINK_DELAY)
        except ResolutionError as exc:
            self.failed.emit("", str(exc))
        finally:
            self.resolver.close()
            self.all_done.emit()
