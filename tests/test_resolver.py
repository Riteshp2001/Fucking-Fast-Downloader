import pytest

from ff_downloader.core.resolver import FuckingFastResolver, ResolutionError


def test_extracts_regular_file_id():
    assert FuckingFastResolver._file_id("https://fuckingfast.co/abc_DEF-123") == "abc_DEF-123"


def test_extracts_htmx_file_id():
    assert FuckingFastResolver._file_id("https://fuckingfast.co/f/abc123/go") == "abc123"


def test_extracts_file_id_with_filename_fragment():
    link = "https://fuckingfast.co/71z90yzzrd1y#Montabi_--_fitgirl-repacks.site_--_.rar"
    assert FuckingFastResolver._file_id(link) == "71z90yzzrd1y"


def test_fragment_filename_is_not_treated_as_fitgirl_page(monkeypatch):
    link = "https://fuckingfast.co/71z90yzzrd1y#Montabi_--_fitgirl-repacks.site_--_.rar"
    resolver = FuckingFastResolver(log=lambda _m: None)
    monkeypatch.setattr(resolver, "resolve", lambda l: f"direct://{l}")
    assert resolver.expand_sources([link]) == [link]


def test_rejects_other_hosts():
    with pytest.raises(ResolutionError):
        FuckingFastResolver._file_id("https://example.com/abc123")


def test_accepts_only_the_real_direct_download_host() -> None:
    resolver = FuckingFastResolver(log=lambda _m: None)

    assert (
        resolver.resolve("https://dl.fuckingfast.co/download/file.part")
        == "https://dl.fuckingfast.co/download/file.part"
    )

    with pytest.raises(ResolutionError):
        resolver.resolve("https://example.com/dl.fuckingfast.co/download/file.part")


def test_extracts_share_links_from_page_text_as_well_as_anchors(monkeypatch) -> None:
    class _Response:
        text = """
            <a href=\"https://fuckingfast.co/from-anchor#one.rar\">one</a>
            <p>Backup: https://fuckingfast.co/from-text#two.rar</p>
        """

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr("ff_downloader.core.resolver.requests.get", lambda *_a, **_k: _Response())
    resolver = FuckingFastResolver(log=lambda _m: None)

    assert resolver.extract_fitgirl_links("https://fitgirl-repacks.site/example/") == [
        "https://fuckingfast.co/from-anchor#one.rar",
        "https://fuckingfast.co/from-text#two.rar",
    ]


def test_resolve_available_keeps_working_when_one_share_link_has_expired(monkeypatch) -> None:
    resolver = FuckingFastResolver(log=lambda _m: None)
    monkeypatch.setattr(resolver, "expand_sources", lambda links: list(links))

    def resolve(link: str) -> str:
        if link.endswith("expired"):
            raise ResolutionError("This share link is no longer available")
        return f"https://dl.fuckingfast.co/{link.rsplit('/', 1)[-1]}"

    monkeypatch.setattr(resolver, "resolve", resolve)

    batch = resolver.resolve_available(
        ["https://fuckingfast.co/ready", "https://fuckingfast.co/expired"]
    )

    assert [(item.source_url, item.direct_url) for item in batch.links] == [
        ("https://fuckingfast.co/ready", "https://dl.fuckingfast.co/ready")
    ]
    assert batch.failures == [
        ("https://fuckingfast.co/expired", "This share link is no longer available")
    ]
