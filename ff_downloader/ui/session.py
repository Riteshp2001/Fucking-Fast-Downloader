"""Keeps the queue between launches so unfinished downloads can be resumed."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt5 import QtCore

SESSION_VERSION = 1


def session_path() -> Path:
    base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppDataLocation)
    return (Path(base) if base else Path.home() / ".ff_downloader") / "session.json"


def load_session() -> dict:
    try:
        data = json.loads(session_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("version") != SESSION_VERSION:
        return {}
    return data


def save_session(data: dict) -> bool:
    path = session_path()
    temp = path.with_name(f"{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps({**data, "version": SESSION_VERSION}), encoding="utf-8")
        temp.replace(path)
    except OSError:
        return False
    return True
