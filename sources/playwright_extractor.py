"""Playwright-based extractor — persistent browser pool for speed."""
import asyncio
import re
from playwright.async_api import async_playwright, Browser, Playwright

_MP4_RE = re.compile(r'https?://[^\s"\']+\.mp4(?:\?[^\s"\']*)?(?=$|["\'\s])')
_IGNORE = {"doubleclick", "googlesyndication", "adservice", "analytics", "pixel",
           "facebook", "clarity.ms", "hotjar", "intercom", "crisp.chat"}
_BLOCK_RES = re.compile(
    r'\.(png|jpe?g|gif|svg|ico|webp|woff2?|ttf|eot|otf)(\?|$)',
    re.IGNORECASE
)

_pw: Playwright | None = None
_browser: Browser | None = None
_browser_lock = asyncio.Lock()


async def _get_browser() -> Browser:
    """Return a shared persistent Chromium instance, launching it if needed."""
    global _pw, _browser
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            if _pw is None:
                _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
    return _browser


async def extract_stream(embed_url: str, timeout: int = 14000, target_domain: str = "") -> str | None:
    """Open a new page in the shared browser, intercept network, return first m3u8/mp4 URL."""
    priority: list[str] = []
    fallback: list[str] = []

    browser = await _get_browser()
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = await ctx.new_page()

    async def _block(route, request):
        url = request.url
        if _BLOCK_RES.search(url) or any(d in url for d in _IGNORE):
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", _block)

    _M3U8_IN_BODY = re.compile(r'https?://[^\s"\'\\]+\.m3u8[^\s"\'\\]*')
    _MP4_IN_BODY = re.compile(r'https?://[^\s"\'\\]+\.mp4[^\s"\'\\]*')

    def on_request(req):
        url = req.url
        if any(d in url for d in _IGNORE):
            return
        if target_domain and target_domain in url:
            priority.append(url)
        if ".m3u8" in url:
            fallback.append(url)
        elif _MP4_RE.search(url):
            fallback.append(url)

    async def on_response(resp):
        ctype = resp.headers.get("content-type", "")
        if not any(x in ctype for x in ("json", "text", "javascript")):
            return
        try:
            body = await resp.text()
            for m in _M3U8_IN_BODY.finditer(body):
                url = m.group(0)
                if not any(d in url for d in _IGNORE):
                    fallback.append(url)
            for m in _MP4_IN_BODY.finditer(body):
                url = m.group(0)
                if not any(d in url for d in _IGNORE) and not any(x in url for x in ("thumbnail","poster","image")):
                    fallback.append(url)
        except Exception:
            pass

    ctx.on("request", on_request)
    ctx.on("response", on_response)

    try:
        await page.goto(embed_url, wait_until="domcontentloaded", timeout=timeout)
    except Exception:
        pass

    # Wait for initial autoplay (up to 4s)
    for _ in range(8):
        if priority or fallback:
            break
        await asyncio.sleep(0.5)

    if not priority and not fallback:
        # Try up to 3 rounds of clicking to trigger stream load
        for _round in range(3):
            # Click known play button selectors
            for sel in (
                ".jw-icon-display", ".vjs-big-play-button", "button.play",
                ".play-btn", "[class*='play']", "video", ".plyr__control--overlaid",
                "div[class*='play']", "button[class*='play']", ".fp-play",
            ):
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.click()
                        break
                except Exception:
                    continue
            # Click center of page (catches fullscreen overlays)
            try:
                await page.mouse.click(640, 360)
            except Exception:
                pass

            for _ in range(8):  # wait up to 4s per click round
                if priority or fallback:
                    break
                await asyncio.sleep(0.5)

            if priority or fallback:
                break

    # Last resort: scan page HTML for any m3u8/mp4 URL
    if not priority and not fallback:
        try:
            html = await page.content()
            for m in re.finditer(r'https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*', html):
                u = m.group(0)
                if not any(d in u for d in _IGNORE):
                    fallback.append(u)
                    break
        except Exception:
            pass

    await ctx.close()

    result = (priority or fallback or [None])[0]
    print(f"[extractor] {embed_url[:60]} -> {result and result[:80]}")
    return result


async def extract_from_allanime_source(clock_url: str, timeout: int = 20000) -> str | None:
    """Navigate the allanime clock URL through Playwright to extract stream."""
    import httpx
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Referer": "https://allmanga.to",
    }

    if not clock_url.startswith("http"):
        full_url = f"https://allanime.day{clock_url}"
    else:
        full_url = clock_url

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            r = await client.get(full_url)
            data = r.json()
            links = data.get("links", [])
            if not links:
                return None
            embed_url = links[0].get("link") or links[0].get("hls") or links[0].get("mp4")
            if not embed_url:
                return None
    except Exception:
        return None

    if embed_url.endswith(".m3u8") or embed_url.endswith(".mp4"):
        return embed_url

    return await extract_stream(embed_url, timeout=timeout)
