from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from ff_downloader.config import DEFAULT_TIMEOUT, STREAM_BLOCK_SIZE

ProgressFn = Callable[[int, int, float], None]
LogFn = Callable[[str], None]


class DownloadCancelled(RuntimeError):
    pass


class DownloadEngine:
    """Serial downloader with resume support, mirroring the Fitgirl flow."""

    def __init__(self, progress: ProgressFn | None = None, log: LogFn | None = None):
        self.progress = progress or (lambda _done, _total, _speed: None)
        self.log = log or (lambda *_message: None)
        self._pause = threading.Event()
        self._cancel = threading.Event()

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

    @staticmethod
    def filename_from_link(link: str) -> str:
        fragment = urlparse(link).fragment.strip()
        if not fragment:
            return ""
        invalid = '<>:"/\\|?*'
        return "".join("_" if char in invalid else char for char in fragment)[:220]

    def download(self, url: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._cancel.clear()
        self._pause.clear()

        existing_size = destination.stat().st_size if destination.is_file() else 0
        req_headers = {}
        if existing_size > 0:
            req_headers["Range"] = f"bytes={existing_size}-"

        response = requests.get(url, headers=req_headers, stream=True, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 416:
            self.log(f"File already complete: {destination.name}")
            response.close()
            return destination

        if response.status_code == 206:
            content_range = response.headers.get("Content-Range", "")
            match = re.search(r"/(\d+)$", content_range)
            total_size = int(match.group(1)) if match else existing_size + int(response.headers.get("content-length", 0))
            if existing_size >= total_size > 0:
                self.log(f"File already complete: {destination.name}")
                response.close()
                return destination
            mode = "ab"
            initial = existing_size
            self.log(f"Resuming {destination.name} from {existing_size} bytes")
        elif response.status_code == 200:
            total_size = int(response.headers.get("content-length", 0) or 0)
            if existing_size > 0 and total_size and existing_size >= total_size:
                self.log(f"File already complete: {destination.name}")
                response.close()
                return destination
            if existing_size > 0:
                self.log(f"Server ignored resume request; restarting {destination.name}")
            mode = "wb"
            initial = 0
        else:
            response.close()
            if (
                urlparse(url).hostname == "dl.fuckingfast.co"
                and response.status_code in {401, 403, 404, 410}
            ):
                raise RuntimeError(
                    "This direct link has expired or is unavailable. Paste the original share link "
                    "to prepare a fresh download URL."
                )
            raise RuntimeError(f"Failed to download file (HTTP {response.status_code})")

        started = time.monotonic()
        done = initial
        try:
            with destination.open(mode) as handle:
                for data in response.iter_content(STREAM_BLOCK_SIZE):
                    self._checkpoint()
                    if not data:
                        continue
                    handle.write(data)
                    done += len(data)
                    elapsed = max(time.monotonic() - started, 0.001)
                    self.progress(done, total_size, (done - initial) / elapsed)
        finally:
            response.close()

        final_size = destination.stat().st_size
        if total_size and final_size < total_size:
            raise RuntimeError(f"Download incomplete: {final_size}/{total_size} bytes")

        self.log(f"Downloaded {destination.name}")
        return destination
