"""Playwright-based extractor for JS-protected embed sources (Streamwish, Filemoon, etc.)."""
import asyncio
import re
from playwright.async_api import async_playwright, Page

_M3U8_RE = re.compile(r'https?://[^\s"\']+\.m3u8[^\s"\']*')
# Require .mp4 to be a file extension (not part of a domain like mp4upload.com)
_MP4_RE = re.compile(r'https?://[^\s"\']+\.mp4(?:[^a-zA-Z0-9]|$)')

EMBED_BASES = {
    "streamwish": ["streamwish.com", "swdyu.com", "sfastwish.com"],
    "filemoon": ["filemoon.sx", "bysekoze.com", "filemoon.to", "kerapoxy.cc"],
    "mp4upload": ["mp4upload.com"],
    "doodstream": ["doodstream.com", "dood.wf"],
}


def _classify_embed(url: str) -> str:
    for name, domains in EMBED_BASES.items():
        for d in domains:
            if d in url:
                return name
    return "unknown"


async def extract_stream(embed_url: str, timeout: int = 20000) -> str | None:
    """Launch headless browser, intercept network, return first m3u8/mp4 URL found."""
    found: list[str] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        )
        page = await ctx.new_page()

        def on_request(req):
            url = req.url
            if ".m3u8" in url:
                found.append(url)
            elif _MP4_RE.search(url) and any(x in url for x in ["cdn", "storage", "media", "video", "edge"]):
                found.append(url)

        page.on("request", on_request)

        try:
            await page.goto(embed_url, wait_until="domcontentloaded", timeout=timeout)
        except Exception:
            pass  # timeout is fine — requests may still fire

        # Wait up to 20s for stream URL regardless of goto result
        for _ in range(40):
            if found:
                break
            await asyncio.sleep(0.5)

        await browser.close()

    return found[0] if found else None


async def extract_from_allanime_source(clock_url: str, timeout: int = 20000) -> str | None:
    """Navigate the allanime clock URL through Playwright to extract stream."""
    # First fetch the clock URL to get the embed URL
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
