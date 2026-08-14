from __future__ import annotations

import os

import pytest

from ff_downloader.core import downloader
from ff_downloader.core.downloader import DownloadEngine


class _Response:
    def __init__(self, status_code: int, headers: dict[str, str], chunks: list[bytes] | None = None):
        self.status_code = status_code
        self.headers = headers
        self._chunks = chunks or []
        self.closed = False

    def iter_content(self, _size: int):
        yield from self._chunks

    def close(self) -> None:
        self.closed = True


def test_resumes_a_file_even_when_its_size_matches_the_old_part_size_sentinel(
    tmp_path, monkeypatch
) -> None:
    destination = tmp_path / "part.bin"
    destination.write_bytes(b"abcd")
    monkeypatch.setattr(
        downloader.requests,
        "get",
        lambda *_a, **_k: _Response(
            206,
            {"Content-Range": "bytes 4-5/6", "content-length": "2"},
            [b"ef"],
        ),
    )

    DownloadEngine().download("https://dl.fuckingfast.co/download/part.bin", destination)

    assert destination.read_bytes() == b"abcdef"


def test_explains_when_an_expired_direct_link_cannot_be_downloaded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        downloader.requests,
        "get",
        lambda *_a, **_k: _Response(403, {}),
    )

    with pytest.raises(RuntimeError, match="original share link"):
        DownloadEngine().download(
            "https://dl.fuckingfast.co/download/no-longer-valid", tmp_path / "file.bin"
        )


@pytest.mark.live_network
def test_downloads_a_real_public_test_file_when_live_checks_are_enabled(tmp_path) -> None:
    if os.environ.get("LIVE_DOWNLOAD_TESTS") != "1":
        pytest.skip("Set LIVE_DOWNLOAD_TESTS=1 to run the public-network smoke test")

    destination = tmp_path / "public-test-file.bin"

    DownloadEngine().download("https://httpbin.org/bytes/64?seed=42", destination)

    assert destination.stat().st_size == 64
