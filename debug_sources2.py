"""Debug: log network requests from new embed sources."""
import asyncio
import re
from playwright.async_api import async_playwright

_IGNORE = {"doubleclick", "googlesyndication", "adservice", "analytics", "pixel",
           "facebook", "clarity.ms", "hotjar", "intercom", "crisp.chat"}
_BLOCK_RES = re.compile(r'\.(png|jpe?g|gif|svg|ico|webp|woff2?|ttf|eot|otf|css)(\?|$)', re.IGNORECASE)

SOURCES = {
    "vidsrc.me":    "https://vidsrc.me/embed/movie?tmdb=550",
    "superembed":   "https://multiembed.mov/directstream.php?video_id=550&tmdb=1",
    "smashystream": "https://player.smashy.stream/movie/550",
    "2embed.skin":  "https://www.2embed.skin/movie/550",
    "frembed":      "https://frembed.pro/api/film.php?id=550",
}

async def probe(name, url):
    print(f"\n{'='*60}")
    print(f"SOURCE: {name}")
    print('='*60)
    hits = []

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
            if any(x in u for x in [".m3u8", ".mp4"]):
                hits.append(u)
                print(f"  [STREAM] {u[:120]}")

        ctx.on("request", on_req)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"  [NAV ERR] {e}")

        for _ in range(20):
            if hits:
                break
            await asyncio.sleep(0.5)

        await browser.close()

    if not hits:
        print("  No stream URL found")

for name, url in SOURCES.items():
    asyncio.run(probe(name, url))
