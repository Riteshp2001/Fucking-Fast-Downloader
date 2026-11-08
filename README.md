# Fucking Fast Downloader

A focused PyQt5 desktop downloader for public FuckingFast share links. Paste links, prepare a queue, then download the files that are ready. It supports FitGirl page extraction, choosing which files to download, copying fresh direct URLs, resumable downloads, and sessions that survive a restart.

## Architecture

```text
ff_downloader/
|- core/
|  |- resolver.py          # source-page and share-link resolver
|  |- browser_resolver.py  # visible browser session for verification checks
|  |- fast_downloader.py   # parallel, resumable browser-engine download
|  `- downloader.py        # resumable streaming download engine
|- ui/
|  |- main_window.py       # PyQt desktop UI
|  `- session.py           # saves the queue between launches
|- config.py               # runtime settings
|- workers.py              # QThread adapters
`- __main__.py             # application entry point
main.py                    # compatibility launcher
```

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
camoufox fetch        # optional: otherwise the app downloads its browser engine (~660 MB) on first use
python main.py
```

## How it works

1. Paste share links, a FitGirl page, or direct `dl.fuckingfast.co` links. With **Prepare on paste** on, preparing starts right away; otherwise press **Prepare** (Ctrl+Enter).
2. On first use the app downloads its browser engine and shows the progress. If the host asks for verification, complete it in the browser window that opens.
3. Files appear in the queue as they are prepared. Untick anything you don't need, such as optional FitGirl parts, then press **Download**.
4. Pause, cancel, or close the app at any time. Unfinished files are kept as `.part` files and the queue is restored on the next launch, so **Resume** continues where it stopped.

Direct `dl.fuckingfast.co` URLs expire after 24 hours. Expired links are marked in the queue; press **Prepare** to get fresh ones. A stale direct URL cannot be renewed by itself, so paste its original share URL instead.

## External managers

Prepare the queue, then use the copy button to copy one fresh direct URL per line for tools such as JDownloader. Right-click a file to copy just its link.

Only download content you are authorized to access.
