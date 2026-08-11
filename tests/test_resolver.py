import pytest

from ff_downloader.core.resolver import FuckingFastResolver, ResolutionError


def test_extracts_regular_file_id():
    assert FuckingFastResolver._file_id("https://fuckingfast.co/abc_DEF-123") == "abc_DEF-123"


def test_extracts_htmx_file_id():
    assert FuckingFastResolver._file_id("https://fuckingfast.co/f/abc123/go") == "abc123"


def test_rejects_other_hosts():
    with pytest.raises(ResolutionError):
        FuckingFastResolver._file_id("https://example.com/abc123")
