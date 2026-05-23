"""Debug: log all network requests from embed sources."""
import asyncio
import re
from playwright.async_api import async_playwright

_IGNORE = {"doubleclick", "googlesyndication", "adservice", "analytics", "pixel",
           "facebook", "clarity.ms", "hotjar", "intercom", "crisp.chat"}
_BLOCK_RES = re.compile(r'\.(png|jpe?g|gif|svg|ico|webp|woff2?|ttf|eot|otf|css)(\?|$)', re.IGNORECASE)

SOURCES = {
    "vidsrc.xyz":  "https://vidsrc.xyz/embed/movie/550",
    "autoembed":   "https://autoembed.cc/movie/tmdb/550",
    "embed.su":    "https://embed.su/embed/movie/550",
    "vidsrc":      "https://vidsrc.to/embed/movie?tmdb=550",
    "2embed":      "https://www.2embed.cc/embed/550",
}

async def probe(name, url):
    print(f"\n{'='*60}")
    print(f"SOURCE: {name}  URL: {url}")
    print('='*60)
    captured = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        )
        page = await ctx.new_page()

        async def _block(route, request):
            u = request.url
            if _BLOCK_RES.search(u) or any(d in u for d in _IGNORE):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", _block)

        def on_req(req):
            u = req.url
            if any(d in u for d in _IGNORE): return
            captured.append(u)
            if any(x in u for x in [".m3u8", ".mp4", "stream", "video", "hls", "cdn", "media"]):
                print(f"  [HIT] {u[:120]}")

        ctx.on("request", on_req)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"  [NAV ERR] {e}")

        for _ in range(20):
            await asyncio.sleep(0.5)

        await browser.close()

    print(f"  Total requests: {len(captured)}")
    if not any(any(x in u for x in [".m3u8", ".mp4"]) for u in captured):
        print("  --- All captured URLs ---")
        for u in captured[:40]:
            print(f"    {u[:120]}")

asyncio.run(probe("vidsrc.xyz", SOURCES["vidsrc.xyz"]))
asyncio.run(probe("autoembed",  SOURCES["autoembed"]))
asyncio.run(probe("embed.su",   SOURCES["embed.su"]))
asyncio.run(probe("vidsrc",     SOURCES["vidsrc"]))
asyncio.run(probe("2embed",     SOURCES["2embed"]))
