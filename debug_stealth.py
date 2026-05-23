"""Probe with stealth flags to bypass headless detection."""
import asyncio
from playwright.async_api import async_playwright

SOURCES = {
    "vidsrc.me":  "https://vidsrc.me/embed/movie?tmdb=550",
    "superembed": "https://multiembed.mov/directstream.php?video_id=550&tmdb=1",
}

async def probe(name, url):
    print(f"\n{'='*60}\nSOURCE: {name}\n{'='*60}")
    all_urls = []
    stream_hits = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-web-security",
            ],
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        # Remove navigator.webdriver flag
        await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await ctx.new_page()

        def on_req(req):
            u = req.url
            all_urls.append(u)
            if any(x in u for x in [".m3u8", ".mp4", "master", "playlist"]):
                stream_hits.append(u)
                print(f"  [STREAM] {u[:140]}")

        ctx.on("request", on_req)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            print(f"  Page loaded, title: {await page.title()}")
        except Exception as e:
            print(f"  [NAV] {e}")

        # Try clicking video/play
        for sel in ["video", ".jw-icon-playback", ".play", "#player", "button"]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click(timeout=2000)
                    print(f"  Clicked: {sel}")
                    break
            except Exception:
                pass

        for _ in range(40):  # 20s
            if stream_hits:
                break
            await asyncio.sleep(0.5)

        await browser.close()

    print(f"  Total requests: {len(all_urls)}")
    if not stream_hits:
        print("  All URLs (first 30):")
        for u in all_urls[:30]:
            print(f"    {u[:120]}")
    else:
        print(f"  Found {len(stream_hits)} stream URL(s)")

for n, u in SOURCES.items():
    asyncio.run(probe(n, u))
