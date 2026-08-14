from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtWidgets

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


def test_empty_window_shows_a_compact_linear_download_flow() -> None:
    app = _application()
    window = main_window.MainWindow()

    assert window.queue_stack.currentWidget() is window.resolve_empty
    assert window.download_card.isHidden()
    assert window.link_input.minimumHeight() <= 180

    window.close()
    app.processEvents()
