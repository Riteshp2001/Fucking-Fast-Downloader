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
