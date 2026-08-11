# Fucking Fast Downloader

A focused PyQt5 desktop downloader for public FuckingFast share links, with FitGirl page link extraction, HTMX resolution, validation/copy workflow, parallel ranged downloads, pause/resume and a modern desktop UI.

## Architecture

```text
ff_downloader/
├── core/
│   ├── resolver.py      # browser-impersonated HTMX resolver
│   └── downloader.py    # ranged/streaming download engine
├── ui/
│   └── main_window.py   # PyQt desktop UI
├── config.py            # runtime settings
├── workers.py           # QThread adapters
└── __main__.py          # application entry point
main.py                  # compatibility launcher
```

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Resolver flow

The resolver keeps a Chrome-impersonating `curl_cffi` session, warms the share page, then performs the same-origin HTMX POST used by the site and reads `HX-Redirect`/`Location`. It retries transient 403/429-style failures with a delay instead of hammering the endpoint.

## External managers

Use **Resolve links**, then **Copy resolved** to copy one quoted direct URL per line for tools such as JDownloader.

Only download content you are authorized to access.
