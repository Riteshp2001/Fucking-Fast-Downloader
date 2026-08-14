from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ff_downloader.config import APP_VERSION

APP_BASENAME = "FuckingFastDownloader"
APP_DISPLAY_NAME = "Fucking Fast Downloader"
PACKAGE_NAME = "fucking-fast-downloader"
APP_ASSETS_DIR = ROOT / "ff_downloader" / "ui" / "assets"
WINDOWS_ICON = APP_ASSETS_DIR / "ffdownloader-mark.ico"


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


def artifact_stem(version: str) -> str:
    normalized_version = version.removeprefix("v")
    return (
        f"{APP_BASENAME}-v{normalized_version}-"
        f"{platform_label()}-{normalize_arch(platform.machine())}"
    )


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
        "--optimize",
        "2",
        "--noupx",
        "--exclude-module",
        "tkinter",
        "--collect-all",
        "camoufox",
        "--collect-all",
        "apify_fingerprint_datapoints",
        "--copy-metadata",
        "camoufox",
        "--add-data",
        f"{APP_ASSETS_DIR}{os.pathsep}ff_downloader/ui/assets",
        "--name",
        APP_BASENAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(spec_dir),
        str(root / "main.py"),
    ]
    if platform.system() == "Windows":
        command[3:3] = ["--icon", str(WINDOWS_ICON)]
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
    stem = artifact_stem(version)

    if platform.system() == "Windows":
        archive = Path(
            shutil.make_archive(
                str(output_dir / f"{stem}-portable"),
                "zip",
                root_dir=bundle.parent,
                base_dir=bundle.name,
            )
        )
    elif platform.system() == "Darwin":
        archive = output_dir / f"{stem}-portable.zip"
        archive.unlink(missing_ok=True)
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
                str(output_dir / f"{stem}-portable"),
                "gztar",
                root_dir=bundle.parent,
                base_dir=bundle.name,
            )
        )

    _verify_artifact(archive)
    return archive


def _find_nsis() -> str:
    found = shutil.which("makensis") or shutil.which("makensis.exe")
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files (x86)\NSIS\makensis.exe"),
        Path(r"C:\Program Files\NSIS\makensis.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "NSIS (makensis.exe) is required for the Windows installer"
    )


def _find_inno_setup() -> str:
    found = shutil.which("ISCC") or shutil.which("iscc")
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "Inno Setup 6 (ISCC.exe) is required for the legacy installer"
    )


def build_windows_installer(
    bundle: Path, output_dir: Path, work_root: Path, version: str
) -> Path:
    stem = artifact_stem(version)
    output_base = f"{stem}-setup"
    installer = output_dir / f"{output_base}.exe"
    installer.unlink(missing_ok=True)

    inno_script = work_root / "installer.iss"
    bundle_path = str(bundle.resolve())
    output_path = str(output_dir.resolve())
    script = f'''[Setup]
AppId=Riteshp2001.FuckingFastDownloader
AppName={APP_DISPLAY_NAME}
AppVersion={version.removeprefix("v")}
AppPublisher=Riteshp2001
DefaultDirName={{localappdata}}\\Programs\\{APP_DISPLAY_NAME}
DefaultGroupName={APP_DISPLAY_NAME}
PrivilegesRequired=lowest
OutputDir={output_path}
OutputBaseFilename={output_base}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={{app}}\\{APP_BASENAME}.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{bundle_path}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\{APP_DISPLAY_NAME}"; Filename: "{{app}}\\{APP_BASENAME}.exe"
Name: "{{autodesktop}}\\{APP_DISPLAY_NAME}"; Filename: "{{app}}\\{APP_BASENAME}.exe"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{APP_BASENAME}.exe"; Description: "Launch {APP_DISPLAY_NAME}"; Flags: nowait postinstall skipifsilent
'''
    inno_script.write_text(script, encoding="utf-8")
    subprocess.run([_find_inno_setup(), str(inno_script)], check=True)
    _verify_artifact(installer)
    return installer


def build_nsis_windows_installer(
    bundle: Path, output_dir: Path, _work_root: Path, version: str
) -> Path:
    stem = artifact_stem(version)
    installer = output_dir / f"{stem}-setup.exe"
    installer.unlink(missing_ok=True)

    nsis_script = ROOT / "scripts" / "installer.nsi"
    if not nsis_script.exists():
        raise FileNotFoundError(f"NSIS installer script was not found: {nsis_script}")

    subprocess.run(
        [
            _find_nsis(),
            f"/DAPP_VERSION={version.removeprefix('v')}",
            f"/DAPP_BASENAME={APP_BASENAME}",
            f"/DAPP_DISPLAY_NAME={APP_DISPLAY_NAME}",
            f"/DAPP_ICON={WINDOWS_ICON.resolve()}",
            f"/DBUNDLE_DIR={bundle.resolve()}",
            f"/DOUTPUT_FILE={installer.resolve()}",
            str(nsis_script),
        ],
        check=True,
    )
    _verify_artifact(installer)
    return installer


def linux_deb_arch() -> str:
    arch = normalize_arch(platform.machine())
    return {"x64": "amd64", "arm64": "arm64"}.get(arch, arch)


def build_linux_installer(
    bundle: Path, output_dir: Path, work_root: Path, version: str
) -> Path:
    normalized_version = version.removeprefix("v")
    arch = linux_deb_arch()
    package_root = work_root / "deb-root"
    shutil.rmtree(package_root, ignore_errors=True)

    app_dir = package_root / "opt" / PACKAGE_NAME
    shutil.copytree(bundle, app_dir)

    executable = app_dir / APP_BASENAME
    executable.chmod(0o755)

    bin_dir = package_root / "usr" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / PACKAGE_NAME
    launcher.write_text(
        f'#!/bin/sh\nexec /opt/{PACKAGE_NAME}/{APP_BASENAME} "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    applications_dir = package_root / "usr" / "share" / "applications"
    applications_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = applications_dir / f"{PACKAGE_NAME}.desktop"
    desktop_file.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                f"Name={APP_DISPLAY_NAME}",
                f"Exec=/opt/{PACKAGE_NAME}/{APP_BASENAME}",
                "Terminal=false",
                "Categories=Network;Utility;",
                "StartupNotify=true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    installed_kb = sum(
        path.stat().st_size for path in app_dir.rglob("*") if path.is_file()
    ) // 1024
    debian_dir = package_root / "DEBIAN"
    debian_dir.mkdir(parents=True, exist_ok=True)
    control = debian_dir / "control"
    control.write_text(
        "\n".join(
            [
                f"Package: {PACKAGE_NAME}",
                f"Version: {normalized_version}",
                "Section: net",
                "Priority: optional",
                f"Architecture: {arch}",
                "Maintainer: Riteshp2001",
                f"Installed-Size: {installed_kb}",
                f"Description: {APP_DISPLAY_NAME}",
                " Fast PyQt desktop downloader for supported public links.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    installer = output_dir / f"{artifact_stem(version)}.deb"
    installer.unlink(missing_ok=True)
    subprocess.run(
        [
            "dpkg-deb",
            "--build",
            "--root-owner-group",
            str(package_root),
            str(installer),
        ],
        check=True,
    )
    _verify_artifact(installer)
    return installer


def build_macos_installer(
    bundle: Path, output_dir: Path, work_root: Path, version: str
) -> Path:
    staging = work_root / "dmg-root"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, staging / bundle.name, symlinks=True)
    (staging / "Applications").symlink_to("/Applications")

    installer = output_dir / f"{artifact_stem(version)}.dmg"
    installer.unlink(missing_ok=True)
    subprocess.run(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_DISPLAY_NAME,
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(installer),
        ],
        check=True,
    )
    _verify_artifact(installer)
    return installer


def build_native_installer(
    bundle: Path, output_dir: Path, work_root: Path, version: str
) -> Path:
    system = platform.system()
    if system == "Windows":
        return build_nsis_windows_installer(bundle, output_dir, work_root, version)
    if system == "Linux":
        return build_linux_installer(bundle, output_dir, work_root, version)
    if system == "Darwin":
        return build_macos_installer(bundle, output_dir, work_root, version)
    raise RuntimeError(f"Unsupported release platform: {system}")


def _verify_artifact(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"Release artifact was not created correctly: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build portable and native installer release artifacts"
    )
    parser.add_argument("--output", type=Path, default=Path("release"))
    parser.add_argument("--version", default=APP_VERSION)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output if args.output.is_absolute() else ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    work_root = ROOT / ".build"
    bundle = build_bundle(ROOT, work_root)
    portable = archive_bundle(bundle, output_dir, args.version)
    installer = build_native_installer(bundle, output_dir, work_root, args.version)
    print(portable)
    print(installer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
