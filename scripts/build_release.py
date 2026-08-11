from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from ff_downloader.config import APP_VERSION

APP_BASENAME = "FuckingFastDownloader"


def normalize_arch(machine: str) -> str:
    value = machine.lower()
    aliases = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    return aliases.get(value, value.replace(" ", "-"))


def platform_label() -> str:
    system = platform.system().lower()
    labels = {"windows": "windows", "linux": "linux", "darwin": "macos"}
    if system not in labels:
        raise RuntimeError(f"Unsupported release platform: {platform.system()}")
    return labels[system]


def build_bundle(root: Path, work_root: Path) -> Path:
    dist_dir = work_root / "dist"
    build_dir = work_root / "pyinstaller"
    spec_dir = work_root / "spec"

    shutil.rmtree(work_root, ignore_errors=True)
    dist_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        APP_BASENAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(spec_dir),
        "--collect-all",
        "curl_cffi",
        str(root / "main.py"),
    ]
    subprocess.run(command, cwd=root, check=True)

    if platform.system() == "Darwin":
        bundle = dist_dir / f"{APP_BASENAME}.app"
    else:
        bundle = dist_dir / APP_BASENAME

    if not bundle.exists():
        raise FileNotFoundError(f"PyInstaller output was not created: {bundle}")
    return bundle


def archive_bundle(bundle: Path, output_dir: Path, version: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_version = version.removeprefix("v")
    stem = (
        f"{APP_BASENAME}-v{normalized_version}-"
        f"{platform_label()}-{normalize_arch(platform.machine())}"
    )

    if platform.system() == "Windows":
        archive = Path(
            shutil.make_archive(
                str(output_dir / stem),
                "zip",
                root_dir=bundle.parent,
                base_dir=bundle.name,
            )
        )
    elif platform.system() == "Darwin":
        archive = output_dir / f"{stem}.zip"
        subprocess.run(
            [
                "ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(bundle),
                str(archive),
            ],
            check=True,
        )
    else:
        archive = Path(
            shutil.make_archive(
                str(output_dir / stem),
                "gztar",
                root_dir=bundle.parent,
                base_dir=bundle.name,
            )
        )

    if not archive.exists() or archive.stat().st_size == 0:
        raise RuntimeError(f"Release archive was not created correctly: {archive}")
    return archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a packaged desktop release")
    parser.add_argument("--output", type=Path, default=Path("release"))
    parser.add_argument("--version", default=APP_VERSION)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    output_dir = args.output if args.output.is_absolute() else root / args.output
    bundle = build_bundle(root, root / ".build")
    archive = archive_bundle(bundle, output_dir, args.version)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
