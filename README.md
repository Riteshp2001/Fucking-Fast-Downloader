# Fucking Fast Downloader 🔽

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/riteshp2001/e/367661)

A modern GUI application for downloading Fucking Fast Links with pause/resume functionality and progress tracking.

![Application Preview](/preview/preview.png)

## Features ✨
- **Modern Dark Theme** 🌙  
- **Pause/Resume Downloads** ⏯️  
- **Real-Time Speed Tracking** 🚀  
- **Automatic Link Management** 🔄  
- **Multi-Platform Support** 💻  
- **Progress Visualization** 📊  
- **Error Handling & Retry** ❗  
- **Custom Icons & Styling** 🎨  

## Installation 🛠️
```bash
# Clone repository
git clone https://github.com/Riteshp2001/Fucking-Fast-Downloader
cd Fucking-Fast-Downloader

# Install dependencies
pip install -r requirements.txt
```

## Usage Guide 📖
1. Add links to `input.txt`:
2. Launch the application:
   ```bash
   python main.py
   ```
3. Click **Load Links** → **Download All**

## Build Executable 🏗️
1. Add build.spec file in folder directory 
2. Copy paste this spec file template:
```bash
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
import os
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.building.build_main import PYZ, EXE, COLLECT

# Application name and version
APP_NAME = 'Test Application'
APP_VERSION = '1.0'

# Platform-specific configurations
if sys.platform == 'win32':
    ICON_PATH = os.path.join('icons', 'fuckingfasticon.ico')

# List of data files to include
data_files = []

# Collect qt_material files
data_files.extend(collect_data_files('qt_material'))

# Application icons
data_files.append((ICON_PATH, 'iconfoldername'))
data_files.append((os.path.join('iconfoldername', 'test.png'), 'iconfoldername'))

# Required files
data_files.append(('input.txt', '.'))

# Windows specific DLLs
if sys.platform == 'win32':
    dll_path = os.path.join(sys.base_prefix, 'DLLs', 'libcrypto-1_1.dll')
    if os.path.exists(dll_path):
        data_files.append((dll_path, '.'))


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'PyQt5.sip',
        'bs4',
        'requests'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# Executable configuration
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
    version_info={
        'CompanyName': 'CompanyName',
        'FileDescription': APP_NAME,
        'ProductName': APP_NAME,
        'ProductVersion': APP_VERSION,
        'OriginalFilename': APP_NAME + '.exe'
    }
)

# Collect build artifacts
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME
)
```

3. In Terminal type :
```bash
pyinstaller build.spec
```

## Support Development ☕  
Help keep this project updated:  
[![Buy Me A Coffee](https://img.shields.io/badge/Support-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/riteshp2001/e/367661)

---

**Disclaimer**: This tool is unofficial and not affiliated with Fucking Fast. Always verify game ownership before downloading.

*Created with ❤️ by [Ritesh Pandit](https://riteshpandit.vercel.app)*  