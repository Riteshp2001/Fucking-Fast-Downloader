"""Application identity assets shared by the desktop window and release builds."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
MARK_PNG = ASSETS_DIR / "ffdownloader-mark.png"
MARK_ICO = ASSETS_DIR / "ffdownloader-mark.ico"


def application_icon() -> QtGui.QIcon:
    """Return the multi-size Windows icon, with a PNG fallback for development."""
    path = MARK_ICO if MARK_ICO.exists() else MARK_PNG
    return QtGui.QIcon(str(path))


def brand_mark(size: int) -> QtGui.QPixmap:
    """Return a smooth, square version of the mark for the custom title bar."""
    source = QtGui.QPixmap(str(MARK_PNG))
    if source.isNull():
        return QtGui.QPixmap()
    return source.scaled(
        QtCore.QSize(size, size),
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation,
    )
