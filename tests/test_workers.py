from __future__ import annotations

from PyQt5 import QtCore

from ff_downloader.workers import (
    DownloadWorker,
    ResolveWorker,
)


def test_download_worker_uses_the_prepared_queue_without_global_cache(tmp_path) -> None:
    source_links = ["https://fitgirl-repacks.site/example/"]
    pairs = [
        ("https://fuckingfast.co/part-1", "https://dl.fuckingfast.co/direct-1"),
        ("https://fuckingfast.co/part-2", "https://dl.fuckingfast.co/direct-2"),
    ]
    worker = DownloadWorker(source_links, tmp_path, resolved_links=pairs)

    assert worker.resolved_links == pairs


class _ResolveParent(QtCore.QObject):
    def __init__(self, links: list[str]):
        super().__init__()
        self.links = links
        self.resolve_calls = 0

    def source_links(self) -> list[str]:
        return self.links

    def resolve_links(self) -> None:
        self.resolve_calls += 1


def test_finished_resolver_never_starts_a_second_browser_resolution() -> None:
    parent = _ResolveParent(["https://fuckingfast.co/new"])
    worker = ResolveWorker(["https://fuckingfast.co/old"], parent)

    worker.finished.emit()

    assert parent.resolve_calls == 0
