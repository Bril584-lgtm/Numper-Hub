"""Probe sources with click interaction and longer wait."""
import asyncio
import re
from playwright.async_api import async_playwright

_IGNORE = {"doubleclick", "googlesyndication", "adservice", "pixel",
           "facebook", "clarity.ms", "hotjar"}

SOURCES = {
    "vidsrc.me":    "https://vidsrc.me/embed/movie?tmdb=550",
    "superembed":   "https://multiembed.mov/directstream.php?video_id=550&tmdb=1",
    "smashystream": "https://player.smashy.stream/movie/550",
    "2embed.skin":  "https://www.2embed.skin/movie/550",
}

async def probe(name, url):
    print(f"\n{'='*60}\nSOURCE: {name}\n{'='*60}")
    hits = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()

        def on_req(req):
            u = req.url
            if any(d in u for d in _IGNORE): return
            if any(x in u for x in [".m3u8", ".mp4"]):
                hits.append(u)
                print(f"  [STREAM] {u[:140]}")

        ctx.on("request", on_req)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        except Exception as e:
            print(f"  [NAV] {e}")

        # Try clicking play button / video element
        for sel in ["video", "button.play", "#player", ".play-button", "[class*='play']", "button"]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click(timeout=2000)
                    print(f"  [CLICK] {sel}")
                    break
            except Exception:
                pass

        # Wait up to 25s
        for _ in range(50):
            if hits:
                break
            await asyncio.sleep(0.5)

        # Log all non-ignored requests if no stream found
        if not hits:
            all_urls = []
            def on_all(req):
                u = req.url
                if not any(d in u for d in _IGNORE):
                    all_urls.append(u)
            ctx.on("request", on_all)
            await asyncio.sleep(2)
            print(f"  No stream URL found. Sample URLs:")
            for u in all_urls[:20]:
                print(f"    {u[:120]}")

        await browser.close()

for name, url in SOURCES.items():
    asyncio.run(probe(name, url))
