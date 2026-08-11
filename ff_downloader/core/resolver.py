from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException

from ff_downloader.config import (
    BASE_HEADERS,
    BETWEEN_LINK_DELAY,
    DEFAULT_TIMEOUT,
    RESOLVE_RETRIES,
    RESOLVE_RETRY_DELAY,
)

LogFn = Callable[[str], None]


class ResolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolvedLink:
    source_url: str
    direct_url: str


class FuckingFastResolver:
    """Resolve public FuckingFast share URLs through the site's HTMX flow."""

    def __init__(self, log: LogFn | None = None):
        self.log = log or (lambda _message: None)

    @staticmethod
    def _file_id(link: str) -> str:
        parsed = urlparse(link.strip())
        if parsed.netloc not in {"fuckingfast.co", "www.fuckingfast.co"}:
            raise ResolutionError(f"Unsupported FuckingFast URL: {link}")
        path = parsed.path.strip("/")
        if path.startswith("f/"):
            path = path[2:].split("/", 1)[0]
        else:
            path = path.split("/", 1)[0]
        if not path or not re.fullmatch(r"[A-Za-z0-9_-]+", path):
            raise ResolutionError(f"Could not determine file id from: {link}")
        return path

    def extract_fitgirl_links(self, url: str) -> list[str]:
        self.log("Scanning page for FuckingFast links…")
        try:
            response = requests.get(
                url,
                headers=BASE_HEADERS,
                impersonate="chrome",
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except RequestException as exc:
            raise ResolutionError(f"Could not read source page: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "").strip()
            if "fuckingfast.co" in href and "dl.fuckingfast" not in href:
                links.append(href)
        unique = list(dict.fromkeys(links))
        self.log(f"Found {len(unique)} share link(s).")
        return unique

    def expand_sources(self, links: Iterable[str]) -> list[str]:
        expanded: list[str] = []
        for raw in links:
            link = raw.strip().strip('"').strip("'")
            if not link:
                continue
            if "fitgirl-repacks.site" in link:
                expanded.extend(self.extract_fitgirl_links(link))
            else:
                expanded.append(link)
        return list(dict.fromkeys(expanded))

    def resolve(self, link: str) -> str:
        link = link.strip()
        if "dl.fuckingfast.co" in link:
            return link

        file_id = self._file_id(link)
        clean_url = f"https://fuckingfast.co/{file_id}"
        post_url = f"https://fuckingfast.co/f/{file_id}/go"
        last_error: RequestException | ResolutionError | None = None

        for attempt in range(1, RESOLVE_RETRIES + 1):
            try:
                with requests.Session(impersonate="chrome") as session:
                    get_headers = {
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "accept-language": "en-US,en;q=0.9",
                        "sec-fetch-dest": "document",
                        "sec-fetch-mode": "navigate",
                        "sec-fetch-site": "none",
                        "sec-fetch-user": "?1",
                        "upgrade-insecure-requests": "1",
                    }
                    self.log(f"Opening share page ({attempt}/{RESOLVE_RETRIES})…")
                    warmup = session.get(clean_url, headers=get_headers, timeout=DEFAULT_TIMEOUT)
                    if warmup.status_code != 200:
                        raise ResolutionError(f"Share page returned HTTP {warmup.status_code}")

                    time.sleep(1.25)
                    post_headers = {
                        "accept": "*/*",
                        "accept-language": "en-US,en;q=0.9",
                        "cache-control": "no-cache",
                        "content-type": "application/x-www-form-urlencoded",
                        "hx-current-url": clean_url,
                        "hx-request": "true",
                        "origin": "https://fuckingfast.co",
                        "pragma": "no-cache",
                        "referer": clean_url,
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "same-origin",
                    }
                    result = session.post(
                        post_url,
                        headers=post_headers,
                        timeout=DEFAULT_TIMEOUT,
                        allow_redirects=False,
                    )
                    if result.status_code == 403:
                        raise ResolutionError("HTMX request was rejected with HTTP 403")
                    if result.status_code == 429:
                        raise ResolutionError("Rate limited with HTTP 429")
                    if result.status_code >= 400:
                        raise ResolutionError(f"HTMX request returned HTTP {result.status_code}")

                    direct = result.headers.get("hx-redirect") or result.headers.get("location")
                    if not direct:
                        raise ResolutionError("HTMX response did not provide a download redirect")
                    return direct
            except (RequestException, ResolutionError) as exc:
                last_error = exc
                if attempt >= RESOLVE_RETRIES:
                    break
                self.log(f"Resolver retry: {exc}")
                time.sleep(RESOLVE_RETRY_DELAY)

        raise ResolutionError(str(last_error or "Could not resolve link"))

    def resolve_many(self, links: Iterable[str]) -> list[ResolvedLink]:
        expanded = self.expand_sources(links)
        output: list[ResolvedLink] = []
        for index, link in enumerate(expanded):
            output.append(ResolvedLink(source_url=link, direct_url=self.resolve(link)))
            if index + 1 < len(expanded):
                time.sleep(BETWEEN_LINK_DELAY)
        return output
