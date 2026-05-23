"""Navigate the cloudnestra player and capture stream URL."""
import asyncio
from playwright.async_api import async_playwright

CLOUDNESTRA_URL = "https://cloudnestra.com/rcp/NjI5MDk5NTdhZGQ4ZWUxYTdhZWM3MzgxNDAzMDc1NmU6UTFCdlZ6VkxRa1IxU0RCQ2QwbG1UaXRXUW5SMWFtaHdiRkpy"

async def main():
    all_urls = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={"Referer": "https://vidsrc.me/"},
        )
        await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await ctx.new_page()

        def on_req(req):
            u = req.url
            all_urls.append(u)
            if any(x in u for x in [".m3u8", ".mp4", "stream", "hls", "playlist", "master"]):
                print(f"[STREAM] {u[:140]}")

        ctx.on("request", on_req)

        try:
            await page.goto(CLOUDNESTRA_URL, wait_until="domcontentloaded", timeout=20000)
            print(f"Title: {await page.title()}")
        except Exception as e:
            print(f"[NAV] {e}")

        # Try clicking video
        for sel in ["video", ".play-button", ".jw-icon-playback", "button", ".vjs-big-play-button"]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click(timeout=3000)
                    print(f"Clicked: {sel}")
                    break
            except Exception:
                pass

        for _ in range(60):  # 30s
            await asyncio.sleep(0.5)
            if any(".m3u8" in u or ".mp4" in u for u in all_urls):
                break

        print(f"\nTotal requests: {len(all_urls)}")
        print("\nAll requests:")
        for u in all_urls:
            print(f"  {u[:140]}")

        await browser.close()

asyncio.run(main())
