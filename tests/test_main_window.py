from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5 import QtCore, QtWidgets

from ff_downloader.ui import main_window, session

SOURCE = "https://fuckingfast.co/example-file#example.bin"
DIRECT = "https://dl.fuckingfast.co/download/fresh-example"


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture(autouse=True)
def _isolated_session(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(session, "session_path", lambda: tmp_path / "session.json")


def test_download_uses_the_prepared_links_displayed_in_the_window(monkeypatch, tmp_path) -> None:
    app = _application()
    window = main_window.MainWindow()
    source = "https://fuckingfast.co/example-file#example.bin"
    prepared = [(source, "https://dl.fuckingfast.co/download/fresh-example")]

    window.link_input.setPlainText(source)
    app.processEvents()

    assert window.resolve_btn.isEnabled()
    assert not window.download_btn.isEnabled()

    window._show_resolution(prepared, [])

    assert window.download_btn.isEnabled()
    monkeypatch.setattr(main_window.DownloadWorker, "start", lambda _worker: None)
    window.download_dir = tmp_path
    window.download_all()

    assert window.download_worker is not None
    assert window.download_worker.resolved_links == prepared
    window.close()


def test_title_bar_uses_distinct_standard_window_control_icons() -> None:
    app = _application()
    window = main_window.MainWindow()

    assert window.title_bar.min_button.property("solarIcon") == "minimize"
    assert window.title_bar.max_button.property("solarIcon") == "maximize"
    assert window.title_bar.close_button.property("solarIcon") == "close"

    window.close()
    app.processEvents()


def test_empty_window_keeps_a_compact_download_dock_visible() -> None:
    app = _application()
    window = main_window.MainWindow()

    assert window.queue_stack.currentWidget() is window.resolve_empty
    assert not window.download_card.isHidden()
    assert window.link_input.minimumHeight() >= 120

    window.close()
    app.processEvents()


def test_workspace_uses_readable_file_queue_instead_of_raw_direct_urls() -> None:
    app = _application()
    window = main_window.MainWindow()

    assert window.link_splitter.orientation() == QtCore.Qt.Horizontal
    assert [window.resolved_list.headerItem().text(column) for column in range(2)] == [
        "File",
        "Status",
    ]

    window.close()
    app.processEvents()


def test_prepared_queue_shows_a_file_name_and_status(monkeypatch) -> None:
    app = _application()
    window = main_window.MainWindow()
    source = "https://fuckingfast.co/example-file#example.bin"
    direct = "https://dl.fuckingfast.co/download/a-very-long-temporary-url"
    monkeypatch.setattr(window, "source_links", lambda: [source])

    window._show_resolution([(source, direct)], [])

    item = window.resolved_list.topLevelItem(0)
    assert item.text(0) == "example.bin"
    assert item.text(1) == "Ready"
    assert direct not in (item.text(0), item.text(1))

    window.close()
    app.processEvents()


def test_workspace_stays_usable_at_a_compact_desktop_height(monkeypatch) -> None:
    app = _application()
    window = main_window.MainWindow()
    source = "https://fuckingfast.co/example-file#example.bin"
    monkeypatch.setattr(window, "source_links", lambda: [source])
    window._show_resolution([(source, "https://dl.fuckingfast.co/download/fresh")], [])
    window.resize(1366, 660)
    window.show()
    app.processEvents()

    assert window.link_input.height() >= 120
    assert window.resolved_list.viewport().height() >= 100
    assert window.download_card.height() <= 190
    assert isinstance(window.workspace_scroll, QtWidgets.QScrollArea)
    assert window.link_splitter.maximumHeight() > 10_000

    window.close()
    app.processEvents()


def test_pasted_direct_links_are_ready_without_preparing() -> None:
    app = _application()
    window = main_window.MainWindow()

    window.link_input.setPlainText(DIRECT)
    app.processEvents()

    assert window.download_btn.isEnabled()
    assert not window.resolve_btn.isEnabled()
    assert window.resolved_list.topLevelItem(0).text(1) == "Ready"

    window.close()
    app.processEvents()


def test_unchecked_files_are_left_out_of_the_download(monkeypatch, tmp_path) -> None:
    app = _application()
    window = main_window.MainWindow()
    optional = "https://fuckingfast.co/optional-file#optional.bin"
    optional_direct = "https://dl.fuckingfast.co/download/optional"
    window.link_input.setPlainText(f"{SOURCE}\n{optional}")
    window._show_resolution([(SOURCE, DIRECT), (optional, optional_direct)], [])

    window.resolved_list.topLevelItem(1).setCheckState(0, QtCore.Qt.Unchecked)
    monkeypatch.setattr(main_window.DownloadWorker, "start", lambda _worker: None)
    window.download_dir = tmp_path
    window.download_all()

    assert window.download_worker is not None
    assert window.download_worker.resolved_links == [(SOURCE, DIRECT)]

    window.close()
    app.processEvents()


def test_adding_a_link_keeps_files_that_are_already_prepared() -> None:
    app = _application()
    window = main_window.MainWindow()
    window.link_input.setPlainText(SOURCE)
    window._show_resolution([(SOURCE, DIRECT)], [])

    second = "https://fuckingfast.co/second-file#second.bin"
    window.link_input.setPlainText(f"{SOURCE}\n{second}")

    assert window.entries[SOURCE].state == main_window.READY
    assert window.entries[second].state == main_window.PENDING
    assert window.download_btn.isEnabled()
    assert window.resolve_btn.isEnabled()

    window.close()
    app.processEvents()


def test_an_expired_download_link_goes_back_to_prepare() -> None:
    app = _application()
    window = main_window.MainWindow()
    window.link_input.setPlainText(SOURCE)
    window._show_resolution([(SOURCE, DIRECT)], [])

    window._download_expired(SOURCE, "This direct link has expired")
    window._sync_actions()

    entry = window.entries[SOURCE]
    assert (entry.state, entry.direct) == (main_window.FAILED, "")
    assert window.resolve_btn.isEnabled()
    assert not window.download_btn.isEnabled()

    window.close()
    app.processEvents()


def test_a_fitgirl_page_expands_into_its_files() -> None:
    app = _application()
    window = main_window.MainWindow()
    page = "https://fitgirl-repacks.site/example-game/"
    parts = ["https://fuckingfast.co/a1#game.part1.rar", "https://fuckingfast.co/b2#game.part2.rar"]
    window.link_input.setPlainText(page)

    window._resolve_expanded(page, parts)

    count = window.resolved_list.topLevelItemCount()
    labels = [window.resolved_list.topLevelItem(row).text(0) for row in range(count)]
    assert labels == ["game.part1.rar", "game.part2.rar"]
    assert page not in window.entries

    window.close()
    app.processEvents()


def test_the_queue_is_restored_after_a_restart() -> None:
    app = _application()
    first = main_window.MainWindow()
    first.link_input.setPlainText(SOURCE)
    first._show_resolution([(SOURCE, DIRECT)], [])
    first.close()
    app.processEvents()

    second = main_window.MainWindow()
    entry = second.entries[SOURCE]

    assert second.link_input.toPlainText() == SOURCE
    assert (entry.state, entry.direct) == (main_window.READY, DIRECT)
    assert second.download_btn.isEnabled()

    second.close()
    app.processEvents()


def test_restored_links_older_than_a_day_are_prepared_again() -> None:
    app = _application()
    session.save_session(
        {
            "links": SOURCE,
            "entries": [{"source": SOURCE, "direct": DIRECT, "state": "ready", "prepared_at": 0}],
        }
    )

    window = main_window.MainWindow()
    entry = window.entries[SOURCE]

    assert (entry.state, entry.direct) == (main_window.PENDING, "")
    assert window.resolve_btn.isEnabled()

    window.close()
    app.processEvents()
