import asyncio

import pytest
import requests
from camoufox import pkgman
from camoufox.browser_pin import BrowserPin
from camoufox.exceptions import CamoufoxNotInstalled, UnsupportedVersion

from ff_downloader.core import browser_resolver
from ff_downloader.core.browser_resolver import HeadlessBrowserResolver, ensure_browser_installed
from ff_downloader.core.errors import ResolutionError


@pytest.fixture
def paired_browser(monkeypatch) -> BrowserPin:
    pin = BrowserPin(
        tag="v158.0.1-beta.41", repo="daijro/camoufox", repo_name="official",
        version="158.0.1", build="beta.41",
    )
    monkeypatch.setattr(browser_resolver, "effective_pin", lambda: pin)
    return pin


def test_fetches_browser_and_announces_first_run_when_missing(monkeypatch) -> None:
    messages: list[str] = []
    calls: list[bool] = []

    def fake_path(download_if_missing: bool = True):
        calls.append(download_if_missing)
        if not download_if_missing:
            raise CamoufoxNotInstalled("not installed")

    monkeypatch.setattr(browser_resolver, "effective_pin", lambda: None)
    monkeypatch.setattr(browser_resolver, "camoufox_path", fake_path)
    HeadlessBrowserResolver(messages.append)._ensure_browser_installed()

    assert calls == [False, True]
    assert messages == [
        "Downloading the browser engine (one-time download)…",
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

    monkeypatch.setattr(browser_resolver, "effective_pin", lambda: None)
    monkeypatch.setattr(browser_resolver, "camoufox_path", fake_path)
    ensure_browser_installed(lambda _message: None)

    assert calls == [False, True]


def test_fresh_install_fetches_paired_tag_and_passes_asset_checksum(
    monkeypatch, tmp_path, paired_browser
) -> None:
    pin = paired_browser
    expected_endpoint = f"repos/{pin.repo}/releases/tags/{pin.tag}"
    asset_url = f"https://github.com/{pin.repo}/releases/download/{pin.tag}/browser.zip"
    checksum = "a" * 64
    arch = pkgman.RepoConfig.get_default().get_arch()
    installed = False

    def fake_path(download_if_missing=True):
        assert not download_if_missing, "The implicit release-list lookup must not run"
        if not installed:
            raise CamoufoxNotInstalled("not installed")
        return tmp_path

    def github_api(endpoint):
        assert endpoint == expected_endpoint
        return {
            "tag_name": pin.tag,
            "assets": [{
                "name": f"camoufox-{pin.spec}-{pkgman.OS_NAME}.{arch}.zip",
                "browser_download_url": asset_url,
                "digest": f"sha256:{checksum}",
            }],
        }

    def install(fetcher):
        nonlocal installed
        assert (fetcher.verstr, fetcher.url, fetcher.installed_sha256) == (pin.spec, asset_url, checksum)
        installed = True

    monkeypatch.setattr(browser_resolver, "camoufox_path", fake_path)
    monkeypatch.setattr(pkgman, "github_api", github_api)
    monkeypatch.setattr(pkgman.CamoufoxFetcher, "install", install)

    ensure_browser_installed(lambda _message: None)

    assert installed


def test_browser_fetch_reports_the_official_tag_on_http_failure(monkeypatch, paired_browser) -> None:
    def unavailable(endpoint):
        assert endpoint == f"repos/{paired_browser.repo}/releases/tags/{paired_browser.tag}"
        response = requests.Response()
        response.status_code = 404
        raise requests.HTTPError(response=response)

    monkeypatch.setattr(browser_resolver, "browser_installed", lambda: False)
    monkeypatch.setattr(pkgman, "github_api", unavailable)

    with pytest.raises(ResolutionError, match=r"v158\.0\.1-beta\.41 from daijro/camoufox \(HTTP 404\)"):
        ensure_browser_installed(lambda _message: None)


def test_stop_interrupts_the_verification_wait() -> None:
    class _Page:
        async def evaluate(self, _script):
            return ""

    resolver = HeadlessBrowserResolver(lambda _message: None)
    resolver.cancel()

    with pytest.raises(ResolutionError, match="Stopped"):
        asyncio.run(resolver._wait_for_turnstile(_Page()))
