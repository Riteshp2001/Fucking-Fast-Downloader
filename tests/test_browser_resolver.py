import asyncio

import pytest
from camoufox.exceptions import CamoufoxNotInstalled, UnsupportedVersion

from ff_downloader.core.browser_resolver import HeadlessBrowserResolver, ensure_browser_installed
from ff_downloader.core.errors import ResolutionError


def test_fetches_browser_and_announces_first_run_when_missing(monkeypatch) -> None:
    messages: list[str] = []
    calls: list[bool] = []

    def fake_path(download_if_missing: bool = True):
        calls.append(download_if_missing)
        if not download_if_missing:
            raise CamoufoxNotInstalled("not installed")

    monkeypatch.setattr(
        "ff_downloader.core.browser_resolver.camoufox_path", fake_path
    )
    HeadlessBrowserResolver(messages.append)._ensure_browser_installed()

    assert calls == [False, True]
    assert messages == [
        "Downloading the browser engine (one-time, ~660 MB)…",
        "Browser engine ready",
    ]


def test_skips_fetch_when_browser_already_installed(monkeypatch) -> None:
    messages: list[str] = []
    calls: list[bool] = []

    def fake_path(download_if_missing: bool):
        calls.append(download_if_missing)

    monkeypatch.setattr(
        "ff_downloader.core.browser_resolver.camoufox_path", fake_path
    )
    HeadlessBrowserResolver(messages.append)._ensure_browser_installed()

    assert calls == [False]
    assert messages == []


def test_replaces_an_outdated_browser(monkeypatch) -> None:
    calls: list[bool] = []

    def fake_path(download_if_missing: bool = True):
        calls.append(download_if_missing)
        if not download_if_missing:
            raise UnsupportedVersion("Camoufox executable is outdated.")

    monkeypatch.setattr("ff_downloader.core.browser_resolver.camoufox_path", fake_path)
    ensure_browser_installed(lambda _message: None)

    assert calls == [False, True]


def test_stop_interrupts_the_verification_wait() -> None:
    class _Page:
        async def evaluate(self, _script):
            return ""

    resolver = HeadlessBrowserResolver(lambda _message: None)
    resolver.cancel()

    with pytest.raises(ResolutionError, match="Stopped"):
        asyncio.run(resolver._wait_for_turnstile(_Page()))
