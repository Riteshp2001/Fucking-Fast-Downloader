from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from ff_downloader.config import BETWEEN_LINK_DELAY, DEFAULT_TIMEOUT
from ff_downloader.core.browser_resolver import HeadlessBrowserResolver
from ff_downloader.core.errors import ResolutionError

LogFn = Callable[[str], None]


@dataclass(frozen=True)
class ResolvedLink:
    source_url: str
    direct_url: str


@dataclass(frozen=True)
class ResolutionBatch:
    """The usable links and the individual source links that need attention."""

    links: list[ResolvedLink]
    failures: list[tuple[str, str]]


class FuckingFastResolver:
    """Resolve public FuckingFast share URLs through the site's HTMX flow,
    using a headless Chrome session to pass Cloudflare / Turnstile."""

    def __init__(self, log: LogFn | None = None):
        self.log = log or (lambda _message: None)
        self._browser = HeadlessBrowserResolver(self.log)

    @staticmethod
    def _file_id(link: str) -> str:
        parsed = urlparse(link.strip())
        if parsed.hostname not in {"fuckingfast.co", "www.fuckingfast.co"}:
            raise ResolutionError(f"Unsupported FuckingFast URL: {link}")
        path = parsed.path.strip("/")
        if path.startswith("f/"):
            path = path[2:].split("/", 1)[0]
        else:
            path = path.split("/", 1)[0]
        if not path or not re.fullmatch(r"[A-Za-z0-9_-]+", path):
            raise ResolutionError(f"Could not determine file id from: {link}")
        return path

    @staticmethod
    def _is_direct_link(link: str) -> bool:
        parsed = urlparse(link.strip())
        return parsed.scheme in {"http", "https"} and parsed.hostname == "dl.fuckingfast.co"

    @staticmethod
    def _is_share_link(link: str) -> bool:
        return urlparse(link.strip()).hostname in {"fuckingfast.co", "www.fuckingfast.co"}

    def extract_fitgirl_links(self, url: str) -> list[str]:
        self.log("Scanning page for FuckingFast links…")
        try:
            response = requests.get(url, headers={"user-agent": "Mozilla/5.0"}, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
        except RequestException as exc:
            raise ResolutionError(f"Could not read source page: {exc}") from exc

        page_text = unescape(response.text)
        soup = BeautifulSoup(page_text, "html.parser")
        candidates: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "").strip()
            if href:
                candidates.append(href)

        candidates.extend(
            re.findall(
                r"https?://(?:www\.)?fuckingfast\.co/(?:f/)?[A-Za-z0-9_-]+[^\s\"'<>]*",
                page_text,
                flags=re.IGNORECASE,
            )
        )
        unique = list(
            dict.fromkeys(
                candidate.rstrip(".,;:!?)\\]}")
                for candidate in candidates
                if self._is_share_link(candidate)
            )
        )
        if not unique:
            raise ResolutionError("No FuckingFast share links were found on that page")
        self.log(f"Found {len(unique)} share link(s).")
        return unique

    def expand_sources(self, links: Iterable[str]) -> list[str]:
        expanded: list[str] = []
        for raw in links:
            link = raw.strip().strip('"').strip("'")
            if not link:
                continue
            if urlparse(link).netloc in {"fitgirl-repacks.site", "www.fitgirl-repacks.site"}:
                expanded.extend(self.extract_fitgirl_links(link))
            else:
                expanded.append(link)
        return list(dict.fromkeys(expanded))

    def resolve(self, link: str) -> str:
        link = link.strip()
        if self._is_direct_link(link):
            return link
        self._file_id(link)
        return self._browser.resolve(link)

    def resolve_available(self, links: Iterable[str]) -> ResolutionBatch:
        """Resolve every available source without discarding a usable batch for one failure."""

        expanded = self.expand_sources(links)
        resolved: list[ResolvedLink] = []
        failures: list[tuple[str, str]] = []
        for index, link in enumerate(expanded):
            try:
                resolved.append(ResolvedLink(source_url=link, direct_url=self.resolve(link)))
            except ResolutionError as exc:
                failures.append((link, str(exc)))
            if index + 1 < len(expanded):
                time.sleep(BETWEEN_LINK_DELAY)
        return ResolutionBatch(links=resolved, failures=failures)

    def resolve_many(self, links: Iterable[str]) -> list[ResolvedLink]:
        batch = self.resolve_available(links)
        if batch.failures:
            failed = "; ".join(f"{link}: {error}" for link, error in batch.failures)
            raise ResolutionError(failed)
        return batch.links

    def close(self) -> None:
        self._browser.close()
