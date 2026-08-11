from pathlib import Path

APP_NAME = "Fucking Fast Downloader"
APP_VERSION = "2.0.0"
DOWNLOADS_DIR = Path.home() / "Downloads" / "Fucking Fast Downloader"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT = 30
RESOLVE_RETRIES = 3
RESOLVE_RETRY_DELAY = 3.0
BETWEEN_LINK_DELAY = 1.5
DOWNLOAD_WORKERS = 8
DOWNLOAD_CHUNK_SIZE = 4 * 1024 * 1024
STREAM_BLOCK_SIZE = 256 * 1024

BASE_HEADERS = {
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://fitgirl-repacks.site/",
}
