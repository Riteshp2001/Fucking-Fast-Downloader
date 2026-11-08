"""Parallel, low-memory replacement for Camoufox's single-stream browser download."""

from __future__ import annotations

import contextlib
import io
import re
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import BinaryIO

import requests
from camoufox import pkgman
from requests.adapters import HTTPAdapter

ProgressFn = Callable[[int, int], None]
StopFn = Callable[[], bool]

CONNECTIONS = 8
MIN_PARALLEL_SIZE = 8 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
TIMEOUT = 30
RANGE_ATTEMPTS = 5
REPORT_INTERVAL = 0.25

_listener: ProgressFn | None = None
_should_stop: StopFn | None = None


class DownloadStopped(RuntimeError):
    pass


@contextlib.contextmanager
def download_progress(
    listener: ProgressFn | None = None, should_stop: StopFn | None = None
) -> Iterator[None]:
    """Report Camoufox package downloads to ``listener``; abort them once ``should_stop()``."""
    global _listener, _should_stop
    saved = _listener, _should_stop
    _listener, _should_stop = listener, should_stop
    try:
        yield
    finally:
        _listener, _should_stop = saved


class _Progress:
    """Thread-safe byte counter that reports at a steady pace."""

    def __init__(self, total: int, callback: ProgressFn | None, should_stop: StopFn | None):
        self.total = total
        self.done = 0
        self._callback = callback
        self._should_stop = should_stop
        self._lock = threading.Lock()
        self._reported = 0.0

    def check(self) -> None:
        if self._should_stop is not None and self._should_stop():
            raise DownloadStopped("Browser download cancelled")

    def add(self, size: int) -> None:
        self.check()
        with self._lock:
            self.done += size
            now = time.monotonic()
            if self._callback is not None and now - self._reported >= REPORT_INTERVAL:
                self._reported = now
                self._callback(self.done, self.total)

    def finish(self) -> None:
        if self._callback is not None:
            with self._lock:
                self._callback(self.done, max(self.total, self.done))


def _auth_headers(url: str) -> dict[str, str]:
    token = getattr(pkgman, "GITHUB_TOKEN", None)
    return {"Authorization": f"Bearer {token}"} if token and "api.github" in url else {}


def _ranged_size(session: requests.Session, url: str, headers: dict[str, str]) -> int:
    """Return the file size when the server honours byte ranges, otherwise 0."""
    try:
        with session.get(
            url, headers={**headers, "Range": "bytes=0-0"}, stream=True, timeout=TIMEOUT
        ) as response:
            if response.status_code != 206:
                return 0
            match = re.search(r"/(\d+)\s*$", response.headers.get("Content-Range", ""))
            return int(match.group(1)) if match else 0
    except requests.RequestException:
        return 0


def _download_single(
    session: requests.Session,
    url: str,
    headers: dict[str, str],
    buffer: BinaryIO,
    callback: ProgressFn | None,
) -> None:
    with session.get(url, headers=headers, stream=True, timeout=TIMEOUT) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)
        progress = _Progress(total, callback, _should_stop)
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                buffer.write(chunk)
                progress.add(len(chunk))
    progress.finish()


def _download_parallel(
    session: requests.Session,
    url: str,
    headers: dict[str, str],
    total: int,
    buffer: BinaryIO,
    callback: ProgressFn | None,
) -> None:
    progress = _Progress(total, callback, _should_stop)
    base = buffer.tell()
    write_lock = threading.Lock()
    failed = threading.Event()
    span = -(-total // CONNECTIONS)

    def fetch(start: int, end: int) -> None:
        position, stalls = start, 0
        while position <= end and not failed.is_set():
            progress.check()
            before = position
            error: requests.RequestException | None = None
            try:
                with session.get(
                    url,
                    headers={**headers, "Range": f"bytes={position}-{end}"},
                    stream=True,
                    timeout=TIMEOUT,
                ) as response:
                    if response.status_code != 206:
                        raise requests.HTTPError(
                            f"Ranged download returned HTTP {response.status_code}"
                        )
                    for chunk in response.iter_content(CHUNK_SIZE):
                        piece = chunk[: end - position + 1]
                        if failed.is_set() or not piece:
                            break
                        with write_lock:
                            buffer.seek(base + position)
                            buffer.write(piece)
                        position += len(piece)
                        progress.add(len(piece))
            except requests.RequestException as exc:
                error = exc
            if position > before:
                stalls = 0
                continue
            stalls += 1
            if stalls >= RANGE_ATTEMPTS:
                raise error or requests.ConnectionError("The download server stopped sending data")
            time.sleep(stalls)

    with ThreadPoolExecutor(max_workers=CONNECTIONS) as pool:
        futures = [
            pool.submit(fetch, start, min(start + span, total) - 1)
            for start in range(0, total, span)
        ]
        try:
            for future in as_completed(futures):
                future.result()
        except BaseException:
            failed.set()
            raise
    progress.finish()


def fast_webdl(
    url: str,
    desc: str | None = None,
    buffer: BinaryIO | None = None,
    bar: bool = True,
    progress_callback: ProgressFn | None = None,
) -> BinaryIO:
    """Drop-in for ``camoufox.pkgman.webdl`` that streams large files over parallel ranges."""
    callback = progress_callback or _listener
    headers = _auth_headers(url)
    if buffer is None:
        buffer = io.BytesIO()
    with requests.Session() as session:
        adapter = HTTPAdapter(pool_maxsize=CONNECTIONS)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        # API responses are small JSON documents; probing them would only spend rate limit.
        total = 0 if "api.github" in url else _ranged_size(session, url, headers)
        if total >= MIN_PARALLEL_SIZE:
            _download_parallel(session, url, headers, total, buffer, callback)
        else:
            _download_single(session, url, headers, buffer, callback)
    buffer.seek(0)
    return buffer


def patch_camoufox_fast_download() -> None:
    """Route Camoufox browser downloads through :func:`fast_webdl` (safe to call repeatedly)."""
    pkgman.webdl = fast_webdl
