from __future__ import annotations

import re
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from ff_downloader.config import DEFAULT_TIMEOUT, STREAM_BLOCK_SIZE

ProgressFn = Callable[[int, int, float], None]
LogFn = Callable[[str], None]

REPORT_INTERVAL = 0.2
TRANSFER_ATTEMPTS = 5
RETRY_DELAY = 2.0
SIZE_PROBE_TIMEOUT = (3, 3)
TRANSIENT_ERRORS = (
    requests.ConnectionError,
    requests.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


class DownloadCancelled(RuntimeError):
    pass


class LinkExpired(RuntimeError):
    pass


class SpeedMeter:
    """Transfer speed averaged over a short sliding window."""

    def __init__(self, window: float = 4.0):
        self.window = window
        self._samples: deque[tuple[float, int]] = deque()

    def reset(self) -> None:
        self._samples.clear()

    def update(self, done: int, now: float | None = None) -> float:
        now = time.monotonic() if now is None else now
        samples = self._samples
        samples.append((now, done))
        while len(samples) > 2 and now - samples[0][0] > self.window:
            samples.popleft()
        started, base = samples[0]
        # Too short a span gives wild spikes; report nothing until there is a real sample.
        return (done - base) / (now - started) if now - started >= 0.5 else 0.0


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

    def checkpoint(self) -> bool:
        """Raise once cancelled and block while paused; return whether it paused."""
        paused = False
        while True:
            if self._cancel.is_set():
                raise DownloadCancelled("Download cancelled")
            if not self._pause.is_set():
                return paused
            paused = True
            time.sleep(0.1)

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

    @staticmethod
    def probe_size(url: str) -> int | None:
        """Check the file size without reading the response body."""
        headers = {"Accept-Encoding": "identity"}
        try:
            with requests.head(
                url, headers=headers, allow_redirects=True, timeout=SIZE_PROBE_TIMEOUT
            ) as response:
                size = _content_length(response)
                if size is not None:
                    return size
                if response.status_code not in (200, 403, 405, 501):
                    return None
            with requests.get(
                url,
                headers={**headers, "Range": "bytes=0-0"},
                stream=True,
                timeout=SIZE_PROBE_TIMEOUT,
            ) as response:
                if response.status_code == 206:
                    content_range = response.headers.get("Content-Range", "")
                    match = re.fullmatch(r"bytes 0-0/([0-9]{1,20})", content_range)
                    return int(match.group(1)) if match else None
                return _content_length(response)
        except requests.RequestException:
            # Size lookup is advisory; the actual transfer reports any download failure.
            return None
        return None

    @staticmethod
    def _working_path(destination: Path) -> Path:
        part = destination.with_name(f"{destination.name}.part")
        # Older versions wrote straight to the final name; keep resuming those files in place.
        return destination if destination.is_file() and not part.exists() else part

    @classmethod
    def existing_bytes(cls, destination: Path) -> int:
        return cls._size(cls._working_path(destination))

    def download(self, url: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        working = self._working_path(destination)

        stalls = 0
        while True:
            before = self._size(working)
            try:
                self._transfer(url, working, destination.name)
                break
            except TRANSIENT_ERRORS:
                stalls = 0 if self._size(working) > before else stalls + 1
                if stalls >= TRANSFER_ATTEMPTS:
                    raise
                self.log(f"Connection interrupted; resuming {destination.name}")
                self._cancel.wait(min(RETRY_DELAY * stalls, 10))

        if working != destination:
            working.replace(destination)
        self.log(f"Downloaded {destination.name}")
        return destination

    @staticmethod
    def _size(path: Path) -> int:
        return path.stat().st_size if path.is_file() else 0

    def _transfer(self, url: str, working: Path, name: str) -> None:
        self.checkpoint()
        existing_size = self._size(working)
        req_headers = {"Range": f"bytes={existing_size}-"} if existing_size > 0 else {}
        response = requests.get(url, headers=req_headers, stream=True, timeout=DEFAULT_TIMEOUT)
        try:
            if response.status_code == 416:
                self.log(f"File already complete: {name}")
                return

            if response.status_code == 206:
                content_range = response.headers.get("Content-Range", "")
                match = re.search(r"/(\d+)$", content_range)
                total_size = (
                    int(match.group(1))
                    if match
                    else existing_size + int(response.headers.get("content-length", 0))
                )
                if existing_size >= total_size > 0:
                    self.log(f"File already complete: {name}")
                    return
                mode = "ab"
                initial = existing_size
                self.log(f"Resuming {name} from {existing_size} bytes")
            elif response.status_code == 200:
                total_size = int(response.headers.get("content-length", 0) or 0)
                if existing_size > 0 and total_size and existing_size >= total_size:
                    self.log(f"File already complete: {name}")
                    return
                if existing_size > 0:
                    self.log(f"Server ignored resume request; restarting {name}")
                mode = "wb"
                initial = 0
            elif (
                urlparse(url).hostname == "dl.fuckingfast.co"
                and response.status_code in {401, 403, 404, 410}
            ):
                raise LinkExpired(
                    "This direct link has expired or is unavailable. Paste the original share link "
                    "to prepare a fresh download URL."
                )
            else:
                raise RuntimeError(f"Failed to download file (HTTP {response.status_code})")

            self._stream(response, working, mode, initial, total_size)
        finally:
            response.close()

    def _stream(self, response, working: Path, mode: str, initial: int, total_size: int) -> None:
        done = initial
        meter = SpeedMeter()
        meter.update(done)
        speed = 0.0
        reported = 0.0
        with working.open(mode) as handle:
            self.progress(initial, total_size, 0.0)
            try:
                for data in response.iter_content(STREAM_BLOCK_SIZE):
                    if self.checkpoint():
                        meter.reset()
                        meter.update(done)
                    if not data:
                        continue
                    handle.write(data)
                    done += len(data)
                    now = time.monotonic()
                    if now - reported >= REPORT_INTERVAL:
                        reported = now
                        speed = meter.update(done, now)
                        self.progress(done, total_size, speed)
            except (DownloadCancelled, *TRANSIENT_ERRORS):
                self.progress(done, total_size, 0.0)
                raise
        self.progress(done, total_size, speed)

        if total_size and done < total_size:
            raise requests.ConnectionError(f"Download incomplete: {done}/{total_size} bytes")


def _content_length(response: requests.Response) -> int | None:
    if response.status_code == 200:
        length = response.headers.get("Content-Length", "").strip()
        if re.fullmatch(r"[0-9]{1,20}", length):
            return int(length)
    return None
