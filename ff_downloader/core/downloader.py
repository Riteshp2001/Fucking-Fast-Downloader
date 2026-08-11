from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse

from curl_cffi import requests

from ff_downloader.config import (
    BASE_HEADERS,
    DEFAULT_TIMEOUT,
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_WORKERS,
    STREAM_BLOCK_SIZE,
)

ProgressFn = Callable[[int, int, float], None]
LogFn = Callable[[str], None]


class DownloadCancelled(RuntimeError):
    pass


class DownloadEngine:
    def __init__(self, progress: ProgressFn | None = None, log: LogFn | None = None):
        self.progress = progress or (lambda _done, _total, _speed: None)
        self.log = log or (lambda _message: None)
        self._pause = threading.Event()
        self._cancel = threading.Event()
        self._write_lock = threading.Lock()

    def pause(self) -> None:
        self._pause.set()

    def resume(self) -> None:
        self._pause.clear()

    def cancel(self) -> None:
        self._cancel.set()
        self._pause.clear()

    def _checkpoint(self) -> None:
        if self._cancel.is_set():
            raise DownloadCancelled("Download cancelled")
        while self._pause.is_set():
            time.sleep(0.1)
            if self._cancel.is_set():
                raise DownloadCancelled("Download cancelled")

    @staticmethod
    def filename_from_url(url: str) -> str:
        name = unquote(Path(urlparse(url).path).name) or "download.bin"
        invalid = '<>:"/\\|?*'
        return "".join("_" if char in invalid else char for char in name)[:220]

    def _probe(self, url: str) -> tuple[int, bool]:
        response = requests.get(
            url,
            headers={**BASE_HEADERS, "Range": "bytes=0-0"},
            impersonate="chrome",
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=True,
        )
        total = 0
        content_range = response.headers.get("content-range", "")
        if "/" in content_range:
            try:
                total = int(content_range.rsplit("/", 1)[1])
            except ValueError:
                total = 0
        if not total:
            total = int(response.headers.get("content-length", 0) or 0)
        supports_ranges = response.status_code == 206 or "bytes" in response.headers.get("accept-ranges", "").lower()
        response.close()
        return total, supports_ranges

    def download(self, url: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        total, supports_ranges = self._probe(url)
        self._cancel.clear()
        self._pause.clear()

        if total > DOWNLOAD_CHUNK_SIZE and supports_ranges:
            self._download_parallel(url, destination, total)
        else:
            self._download_stream(url, destination, total)
        return destination

    def _download_parallel(self, url: str, destination: Path, total: int) -> None:
        with destination.open("wb") as handle:
            handle.truncate(total)

        ranges = [
            (start, min(start + DOWNLOAD_CHUNK_SIZE - 1, total - 1))
            for start in range(0, total, DOWNLOAD_CHUNK_SIZE)
        ]
        started = time.monotonic()
        completed = 0

        def fetch(start: int, end: int) -> int:
            for attempt in range(3):
                self._checkpoint()
                try:
                    response = requests.get(
                        url,
                        headers={**BASE_HEADERS, "Range": f"bytes={start}-{end}"},
                        stream=True,
                        impersonate="chrome",
                        timeout=DEFAULT_TIMEOUT,
                    )
                    if response.status_code not in {200, 206}:
                        raise RuntimeError(f"Chunk returned HTTP {response.status_code}")
                    cursor = start
                    for block in response.iter_content(STREAM_BLOCK_SIZE):
                        self._checkpoint()
                        if not block:
                            continue
                        with self._write_lock:
                            with destination.open("r+b") as handle:
                                handle.seek(cursor)
                                handle.write(block)
                        cursor += len(block)
                    return cursor - start
                except DownloadCancelled:
                    raise
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(1.5 ** attempt)
            return 0

        with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
            futures = [pool.submit(fetch, start, end) for start, end in ranges]
            for future in as_completed(futures):
                completed += future.result()
                elapsed = max(time.monotonic() - started, 0.001)
                self.progress(completed, total, completed / elapsed)

    def _download_stream(self, url: str, destination: Path, expected_total: int) -> None:
        started = time.monotonic()
        done = 0
        with requests.get(
            url,
            headers=BASE_HEADERS,
            stream=True,
            impersonate="chrome",
            timeout=DEFAULT_TIMEOUT,
        ) as response:
            if response.status_code >= 400:
                raise RuntimeError(f"Download returned HTTP {response.status_code}")
            total = int(response.headers.get("content-length", 0) or expected_total or 0)
            with destination.open("wb") as handle:
                for block in response.iter_content(1024 * 1024):
                    self._checkpoint()
                    if not block:
                        continue
                    handle.write(block)
                    done += len(block)
                    elapsed = max(time.monotonic() - started, 0.001)
                    self.progress(done, total, done / elapsed)
