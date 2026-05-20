"""GogoAnime (anitaku.pe) source — independent fallback when AllAnime is down."""
import re
import httpx
from . import playwright_extractor

BASE = "https://anitaku.pe"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
HEADERS = {"User-Agent": AGENT, "Referer": BASE}


async def search(query: str, dub: bool = False) -> list[dict]:
    search_q = query + (" (Dub)" if dub else "")
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            r = await client.get(f"{BASE}/search.html", params={"keyword": search_q})
            html = r.text
    except Exception:
        return []

    results = []
    for m in re.finditer(
        r'class="name"><a href="/category/([^"]+)"[^>]*title="([^"]+)"', html
    ):
        slug = m.group(1).strip()
        title = m.group(2).strip()
        is_dub = "(dub)" in title.lower() or slug.endswith("-dub")
        if dub and not is_dub:
            continue
        if not dub and is_dub:
            continue
        results.append({
            "id": slug,
            "title": title,
            "episodes": 0,
            "thumb": "",
            "source": "gogoanime",
        })

    return results[:20]


async def get_episode_count(slug: str) -> int:
    """Fetch episode count from the category page."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10, follow_redirects=True) as client:
            r = await client.get(f"{BASE}/category/{slug}")
            html = r.text
        # Extract anime_id then hit AJAX endpoint
        m = re.search(r'data-id="(\d+)"', html)
        alias_m = re.search(r"data-alias=['\"]([^'\"]+)['\"]", html)
        if not m:
            return 0
        anime_id = m.group(1)
        alias = alias_m.group(1) if alias_m else slug
        async with httpx.AsyncClient(headers=HEADERS, timeout=10, follow_redirects=True) as client:
            r2 = await client.get(
                f"{BASE}/ajax/load-list-episode",
                params={"ep_start": 0, "ep_end": 9999, "id": anime_id,
                        "default_ep": 0, "alias": alias},
            )
            ep_html = r2.text
        ep_nums = re.findall(r'data-number="(\d+)"', ep_html)
        return max((int(x) for x in ep_nums), default=0)
    except Exception:
        return 0


async def get_stream(slug: str, ep: int, dub: bool = False) -> dict:
    """Return {url, type, source} or {error}."""
    ep_slug = f"{slug}-episode-{ep}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            r = await client.get(f"{BASE}/{ep_slug}")
            html = r.text
    except Exception as e:
        return {"error": f"GogoAnime fetch failed: {e}"}

    # Extract embed iframe URL
    m = re.search(r'<iframe[^>]+src="(https?://[^"]+)"', html)
    if not m:
        return {"error": "GogoAnime: no embed found"}

    embed_url = m.group(1)
    try:
        stream = await playwright_extractor.extract_stream(embed_url)
        if stream:
            stype = "hls" if ".m3u8" in stream else "mp4"
            return {"url": stream, "type": stype, "source": "gogoanime"}
    except Exception as e:
        return {"error": f"GogoAnime Playwright failed: {e}"}

    return {"error": "GogoAnime: stream extraction failed"}
