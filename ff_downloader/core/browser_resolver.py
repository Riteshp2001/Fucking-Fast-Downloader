from __future__ import annotations

import asyncio
import json
import os
import threading
from collections.abc import Callable
from urllib.parse import urlparse

from camoufox.async_api import AsyncCamoufox

from ff_downloader.config import (
    BROWSER_PROFILE_DIR,
    BROWSER_RESOLVE_ATTEMPTS,
    BROWSER_RETRY_DELAY,
    CF_WAIT_SECS,
    HEADLESS_BROWSER,
    TURNSTILE_WAIT_SECS,
)
from ff_downloader.core.errors import ResolutionError

LogFn = Callable[[str], None]


class HeadlessBrowserResolver:
    """Resolve share links in a user-visible Camoufox browser session.

    A persistent profile retains the browser's normal session state. If the
    host asks for a Cloudflare or Turnstile check, the user completes it in the
    visible browser window before the app requests a fresh direct URL.
    """

    def __init__(self, log: LogFn | None = None):
        self.log = log or (lambda _message: None)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._loop_ready = threading.Event()
        self._browser = None
        self._camoufox: AsyncCamoufox | None = None
        self._page = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ loop

    def _ensure_loop(self) -> None:
        with self._lock:
            if self._loop is not None:
                return
            self._loop_ready.clear()

            def _run() -> None:
                asyncio.set_event_loop(asyncio.new_event_loop())
                self._loop = asyncio.get_event_loop()
                self._loop_ready.set()
                self._loop.run_forever()

            self._loop_thread = threading.Thread(target=_run, name="ff-browser-loop", daemon=True)
            self._loop_thread.start()
            self._loop_ready.wait()

    def _submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    # --------------------------------------------------------------- browser

    async def _ensure_browser(self):
        if self._browser is None:
            self.log("Opening a browser window to prepare the download…")
            os.makedirs(BROWSER_PROFILE_DIR, exist_ok=True)
            self._camoufox = AsyncCamoufox(
                headless=HEADLESS_BROWSER,
                persistent_context=True,
                user_data_dir=str(BROWSER_PROFILE_DIR),
                disable_coop=True,
                humanize=True,
                window=(1280, 720),
            )
            self._browser = await self._camoufox.__aenter__()
            self._page = await self._browser.new_page()
        return self._page

    # ---------------------------------------------------------------- helper

    @staticmethod
    def _file_id(link: str) -> str:
        path = urlparse(link).path.strip("/")
        if path.startswith("f/"):
            path = path[2:].split("/", 1)[0]
        else:
            path = path.split("/", 1)[0]
        return path

    async def _page_ready(self, page) -> bool:
        try:
            state = await page.evaluate(
                """() => {
                    const title = document.title || '';
                    const body = (document.body && document.body.innerText) || '';
                    const hasChallenge = title.includes('Just a moment')
                        || body.includes('Verifying you are human')
                        || !!document.querySelector('#challenge-running, #cf-challenge-running, .cf-browser-verification');
                    const hasDownload = !!document.querySelector('a.link-button')
                        || !!document.querySelector('#cf-turnstile')
                        || !!document.querySelector('meta[name="title"]')
                        || /DOWNLOAD/i.test(body);
                    return { hasChallenge, hasDownload, title };
                }"""
            )
        except Exception:
            return False
        if not isinstance(state, dict):
            return False
        return bool(not state.get("hasChallenge") and state.get("hasDownload"))

    async def _wait_for_cf_clear(self, page) -> bool:
        self.log("Waiting for Cloudflare check…")
        for i in range(CF_WAIT_SECS):
            try:
                if await self._page_ready(page):
                    self.log(f"Cloudflare cleared after {i + 1}s")
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
            if i and i % 15 == 0:
                self.log(f"Still waiting for download page ({i}s)")
        return False

    async def _wait_for_turnstile(self, page) -> str | None:
        self.log("Complete verification in the browser window, then return here…")
        for i in range(TURNSTILE_WAIT_SECS):
            try:
                token = await page.evaluate(
                    """() => window.turnstileToken
                        || (document.querySelector('[name="cf-turnstile-response"]') || {}).value
                        || ''"""
                )
                if isinstance(token, str) and len(token) > 20:
                    self.log(f"Turnstile ready after {i + 1}s")
                    return token
            except Exception:
                pass

            await asyncio.sleep(1)
        return None

    async def _post_go(self, page, file_id: str, token: str):
        try:
            return await page.evaluate(
                f"""async () => {{
                    const response = await fetch('/f/{file_id}/go', {{
                        method: 'POST',
                        headers: {{
                            'content-type': 'application/x-www-form-urlencoded',
                            'hx-request': 'true',
                            'hx-current-url': location.href,
                            'referer': location.href,
                        }},
                        body: new URLSearchParams({{ 'cf-turnstile-response': {json.dumps(token)} }}),
                    }});
                    const redirect = response.headers.get('HX-Redirect')
                        || response.headers.get('hx-redirect');
                    const body = await response.text();
                    return {{
                        status: response.status,
                        redirect: redirect,
                        body: body.slice(0, 200),
                    }};
                }}"""
            )
        except Exception:
            return None

    async def _resolve(self, link: str) -> str:
        page = await self._ensure_browser()
        file_id = self._file_id(link)
        last_error = "unknown error"

        for attempt in range(1, BROWSER_RESOLVE_ATTEMPTS + 1):
            try:
                await page.goto(link, wait_until="domcontentloaded")
            except Exception as exc:
                last_error = f"Could not open the share page: {exc}"
                if attempt < BROWSER_RESOLVE_ATTEMPTS:
                    await asyncio.sleep(BROWSER_RETRY_DELAY)
                    continue
                break

            if not await self._wait_for_cf_clear(page):
                last_error = "Stuck on Cloudflare 'Just a moment' page"
            else:
                has_widget = False
                try:
                    has_widget = bool(await page.evaluate("() => !!document.getElementById('cf-turnstile')"))
                except Exception:
                    pass

                if has_widget:
                    token = await self._wait_for_turnstile(page)
                else:
                    self.log("No captcha widget on page, session already trusted")
                    token = ""

                if token is None:
                    last_error = "Turnstile token not ready"
                else:
                    result = await self._post_go(page, file_id, token)
                    if not isinstance(result, dict):
                        last_error = f"Unexpected browser response: {result!r}"
                    elif result.get("redirect"):
                        return result["redirect"]
                    else:
                        last_error = f"No HX-Redirect ({result.get('body') or result.get('status')})"

            if attempt < BROWSER_RESOLVE_ATTEMPTS:
                self.log(f"Retrying link ({attempt + 1}/{BROWSER_RESOLVE_ATTEMPTS}) — {last_error}")
                await asyncio.sleep(BROWSER_RETRY_DELAY)

        raise ResolutionError(last_error)

    # ------------------------------------------------------------------ sync

    def resolve(self, link: str) -> str:
        self._ensure_loop()
        try:
            return self._submit(self._resolve(link)).result()
        except ResolutionError:
            raise
        except Exception as exc:
            raise ResolutionError(str(exc)) from exc

    def close(self) -> None:
        loop = self._loop
        if loop is None:
            return

        async def _shutdown():
            if self._camoufox is not None:
                try:
                    await self._camoufox.__aexit__(None, None, None)
                except Exception:
                    pass
            pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        try:
            self._submit(_shutdown()).result(timeout=15)
        except Exception:
            pass

        loop.call_soon_threadsafe(loop.stop)
        if self._loop_thread and self._loop_thread is not threading.current_thread():
            self._loop_thread.join(timeout=5)

        self._page = None
        self._browser = None
        self._camoufox = None
        self._loop = None
        self._loop_thread = None
