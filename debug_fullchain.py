"""Full HLS chain test: stream URL -> master m3u8 -> sub-playlist -> segment."""
import asyncio
import httpx
import urllib.parse

BASE = "http://127.0.0.1:7778"

async def main():
    async with httpx.AsyncClient(timeout=60) as c:
        # 1. Get stream URL
        print("[1] Getting stream URL...")
        r = await c.get(f"{BASE}/api/stream/movie?id=550&source=vidlink")
        data = r.json()
        stream_url = data["url"]
        print(f"    URL: {stream_url[:80]}")
        print(f"    Cached: {r.elapsed.total_seconds():.1f}s")

        # 2. Fetch master m3u8 through proxy
        print("\n[2] Fetching master m3u8 through proxy...")
        proxy_url = f"{BASE}/api/proxy?url={urllib.parse.quote(stream_url, safe='')}"
        r = await c.get(proxy_url)
        print(f"    Status: {r.status_code}")
        master = r.text
        lines = master.splitlines()
        print(f"    Lines: {len(lines)}")
        # Find 720p sub-playlist proxy URL
        sub_line = next((l for l in lines if "/api/proxy" in l and "NzIw" in l), None)
        if not sub_line:
            # Try any sub-playlist
            sub_line = next((l for l in lines if "/api/proxy" in l and ".m3u8" in l), None)
        if not sub_line:
            print("    No sub-playlist found. First 10 lines:")
            for l in lines[:10]: print(f"      {l[:100]}")
            return
        print(f"    Sub-playlist proxy URL found (720p)")

        # 3. Fetch sub-playlist
        print("\n[3] Fetching sub-playlist...")
        sub_url = f"{BASE}{sub_line}"
        r = await c.get(sub_url)
        print(f"    Status: {r.status_code}")
        sub = r.text
        sub_lines = sub.splitlines()
        print(f"    Lines: {len(sub_lines)}")
        # Find first segment proxy URL
        seg_line = next((l for l in sub_lines if "/api/proxy" in l and not l.startswith("#")), None)
        if not seg_line:
            print("    No segment found. First 15 lines:")
            for l in sub_lines[:15]: print(f"      {l[:100]}")
            return
        print(f"    First segment proxy URL found")

        # 4. Fetch first segment
        print("\n[4] Fetching first segment...")
        seg_url = f"{BASE}{seg_line}"
        r = await c.get(seg_url)
        print(f"    Status: {r.status_code}")
        print(f"    Size: {len(r.content)} bytes")
        print(f"    Content-Type: {r.headers.get('content-type', 'unknown')}")
        if r.status_code == 200 and len(r.content) > 1000:
            print("\n=== SUCCESS: Full HLS chain works! ===")
        else:
            print(f"\n=== FAIL: Segment fetch failed ===")
            print(f"    Body preview: {r.text[:200]}")

asyncio.run(main())
