from ff_downloader.core.browser_resolver import CamoufoxNotInstalled, HeadlessBrowserResolver


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
        "First run: downloading the Camoufox browser (~660 MB). This happens once and may take a few minutes…",
        "Camoufox browser ready.",
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
