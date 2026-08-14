# Fucking Fast Downloader

A focused PyQt5 desktop downloader for public FuckingFast share links. Paste links, prepare a queue, then download the files that are ready. It supports FitGirl page extraction, copying fresh direct URLs, resumable downloads, and pause/cancel controls.

## Architecture

```text
ff_downloader/
|- core/
|  |- resolver.py      # source-page and share-link resolver
|  `- downloader.py    # resumable streaming download engine
|- ui/
|  `- main_window.py   # PyQt desktop UI
|- config.py           # runtime settings
|- workers.py          # QThread adapters
`- __main__.py         # application entry point
main.py                # compatibility launcher
```

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## How it works

1. Paste original `fuckingfast.co` share URLs, a supported source page, or current `dl.fuckingfast.co` direct URLs.
2. Select **Prepare**. The prepared queue is stored in the window, so download always uses the links you reviewed—not a hidden cache.
3. If the host requests verification, complete it in the browser window that opens. This uses the browser's normal session; the app does not try to solve the challenge invisibly.
4. Select **Download ready files**, or use the copy button to send fresh direct URLs to another download manager.

Direct `dl.fuckingfast.co` URLs expire after 24 hours. A stale direct URL cannot be renewed by itself; paste its original share URL to prepare a fresh one. When a batch has stale share URLs, usable files remain in the queue and only the affected entries are marked for attention.

## External managers

Use **Prepare**, then the copy button to copy one fresh direct URL per line for tools such as JDownloader.

Only download content you are authorized to access.
