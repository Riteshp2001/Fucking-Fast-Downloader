from __future__ import annotations

from itertools import pairwise
from pathlib import Path

from scripts import build_release

ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_installs_nsis_for_the_windows_build() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release-builds.yml").read_text(
        encoding="utf-8"
    )

    assert "choco install nsis" in workflow
    assert "innosetup" not in workflow


def test_nsis_installer_installs_bundle_and_supports_uninstall() -> None:
    script = (ROOT / "scripts" / "installer.nsi").read_text(encoding="utf-8")

    assert 'File /r "${BUNDLE_DIR}\\*"' in script
    assert "Section \"Uninstall\"" in script
    assert "RequestExecutionLevel user" in script


def test_release_builder_selects_nsis_on_windows() -> None:
    builder = (ROOT / "scripts" / "build_release.py").read_text(encoding="utf-8")

    assert "def build_nsis_windows_installer" in builder
    assert "return build_nsis_windows_installer(bundle, output_dir, work_root, version)" in builder


def test_bundle_collects_fingerprint_datapoints(monkeypatch, tmp_path) -> None:
    captured: list[str] = []

    def run(command: list[str], cwd: Path, check: bool) -> None:
        captured.extend(command)
        dist_dir = Path(command[command.index("--distpath") + 1])
        (dist_dir / build_release.APP_BASENAME).mkdir()

    monkeypatch.setattr(build_release.platform, "system", lambda: "Linux")
    monkeypatch.setattr(build_release.subprocess, "run", run)

    build_release.build_bundle(ROOT, tmp_path / "build")

    assert any(
        option == "--collect-all" and package == "apify_fingerprint_datapoints"
        for option, package in pairwise(captured)
    )


def test_nsis_builder_passes_bundle_and_output_to_makensis(monkeypatch, tmp_path) -> None:
    bundle = tmp_path / "FuckingFastDownloader"
    bundle.mkdir()
    output_dir = tmp_path / "release"
    output_dir.mkdir()
    captured: list[str] = []

    def run(command: list[str], check: bool) -> None:
        captured.extend(command)
        output_definition = next(item for item in command if item.startswith("/DOUTPUT_FILE="))
        Path(output_definition.removeprefix("/DOUTPUT_FILE=")).write_bytes(b"installer")

    monkeypatch.setattr(build_release, "_find_nsis", lambda: "makensis")
    monkeypatch.setattr(build_release.platform, "system", lambda: "Windows")
    monkeypatch.setattr(build_release.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(build_release.subprocess, "run", run)

    installer = build_release.build_nsis_windows_installer(
        bundle, output_dir, tmp_path, "2.1.0"
    )

    assert installer.exists()
    assert "makensis" in captured
    assert any(item.startswith("/DBUNDLE_DIR=") for item in captured)
    assert any(item.startswith("/DOUTPUT_FILE=") for item in captured)
