from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore, QtWidgets

from ff_downloader.ui import main_window


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_download_uses_the_prepared_links_displayed_in_the_window(monkeypatch, tmp_path) -> None:
    app = _application()
    window = main_window.MainWindow()
    source = "https://fuckingfast.co/example-file#example.bin"
    prepared = [(source, "https://dl.fuckingfast.co/download/fresh-example")]

    window.link_input.setPlainText(source)
    app.processEvents()

    assert window.resolve_btn.isEnabled()
    assert not window.download_btn.isEnabled()

    window._resolve_revision = source
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
    window._resolve_revision = source

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
    window._resolve_revision = source
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
