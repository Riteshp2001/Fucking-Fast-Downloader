from __future__ import annotations

import io
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from camoufox import pkgman


def patch_camoufox_fast_download(num_threads: int = 16) -> None:
    """Patch Camoufox pkgman webdl to use multi-threaded HTTP Range requests
    for faster browser package downloads."""

    original_webdl = getattr(pkgman, "webdl", None)

    def fast_webdl(
        url: str,
        desc: str | None = None,
        buffer: io.BytesIO | None = None,
        bar: bool = True,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> io.BytesIO:
        headers = (
            {"Authorization": f"Bearer {pkgman.GITHUB_TOKEN}"}
            if "api.github" in url and pkgman.GITHUB_TOKEN
            else {}
        )
        session = requests.Session()
        try:
            head = session.head(url, allow_redirects=True, headers=headers, timeout=15)
            final_url = head.url
            total_size = int(head.headers.get("content-length", 0))
        except Exception:
            if original_webdl:
                return original_webdl(
                    url, desc=desc, buffer=buffer, bar=bar, progress_callback=progress_callback
                )
            raise

        if buffer is None:
            buffer = io.BytesIO()

        if (
            total_size < 5 * 1024 * 1024 or head.headers.get("Accept-Ranges") != "bytes"
        ) and original_webdl:
            return original_webdl(
                url, desc=desc, buffer=buffer, bar=bar, progress_callback=progress_callback
            )

        chunk_size = total_size // num_threads
        ranges = []
        for i in range(num_threads):
            start = i * chunk_size
            end = total_size - 1 if i == num_threads - 1 else (start + chunk_size - 1)
            ranges.append((start, end, i))

        parts: list[bytes | None] = [None] * num_threads

        def download_range(start: int, end: int, index: int) -> tuple[int, bytes]:
            req_headers = dict(headers)
            req_headers["Range"] = f"bytes={start}-{end}"
            resp = session.get(final_url, headers=req_headers, stream=True, timeout=30)
            resp.raise_for_status()
            data = bytearray()
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    data.extend(chunk)
                    if progress_callback:
                        progress_callback(len(data), total_size)
            return index, bytes(data)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(download_range, s, e, i) for s, e, i in ranges]
            for future in as_completed(futures):
                idx, data = future.result()
                parts[idx] = data

        for part in parts:
            if part:
                buffer.write(part)
        buffer.seek(0)
        return buffer

    pkgman.webdl = fast_webdl
