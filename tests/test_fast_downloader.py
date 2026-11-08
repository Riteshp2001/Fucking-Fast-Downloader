from __future__ import annotations

import pytest

from ff_downloader.core import fast_downloader

PAYLOAD = bytes(range(256)) * 400


class _Response:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes = b""):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, size: int):
        for start in range(0, len(self._body), size):
            yield self._body[start : start + size]


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def mount(self, *_args) -> None:
        return None

    def get(self, _url: str, headers: dict[str, str] | None = None, **_kwargs) -> _Response:
        byte_range = (headers or {}).get("Range")
        if byte_range is None:
            return _Response(200, {"content-length": str(len(PAYLOAD))}, PAYLOAD)
        start, end = byte_range.removeprefix("bytes=").split("-")
        first, last = int(start), int(end) if end else len(PAYLOAD) - 1
        content_range = f"bytes {first}-{last}/{len(PAYLOAD)}"
        return _Response(206, {"Content-Range": content_range}, PAYLOAD[first : last + 1])


@pytest.fixture
def fake_server(monkeypatch) -> None:
    monkeypatch.setattr(fast_downloader.requests, "Session", _Session)
    monkeypatch.setattr(fast_downloader, "MIN_PARALLEL_SIZE", 1024)


@pytest.mark.usefixtures("fake_server")
def test_parallel_download_reassembles_every_range_in_order() -> None:
    reports: list[tuple[int, int]] = []

    buffer = fast_downloader.fast_webdl(
        "https://example.com/browser.zip",
        progress_callback=lambda done, total: reports.append((done, total)),
    )

    assert buffer.read() == PAYLOAD
    assert reports[-1] == (len(PAYLOAD), len(PAYLOAD))


@pytest.mark.usefixtures("fake_server")
def test_stop_request_aborts_the_browser_download() -> None:
    with (
        fast_downloader.download_progress(should_stop=lambda: True),
        pytest.raises(fast_downloader.DownloadStopped),
    ):
        fast_downloader.fast_webdl("https://example.com/browser.zip")


def test_patch_can_be_applied_repeatedly() -> None:
    fast_downloader.patch_camoufox_fast_download()
    fast_downloader.patch_camoufox_fast_download()

    assert fast_downloader.pkgman.webdl is fast_downloader.fast_webdl
