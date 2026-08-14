from pathlib import Path

APP_NAME = "Fucking Fast Downloader"
APP_VERSION = "2.1.0"
DOWNLOADS_DIR = Path.home() / "Downloads" / "Fucking Fast Downloader"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT = 30
BETWEEN_LINK_DELAY = 1.5
STREAM_BLOCK_SIZE = 256 * 1024

# Cloudflare verification is intentionally visible: it lets the person using the
# app complete any challenge in a real browser instead of silently retrying it.
HEADLESS_BROWSER = False
CF_WAIT_SECS = 120
TURNSTILE_WAIT_SECS = 120
BROWSER_RESOLVE_ATTEMPTS = 4
BROWSER_RETRY_DELAY = 3.0
BROWSER_PROFILE_DIR = Path.home() / ".ff_browser_profile"
