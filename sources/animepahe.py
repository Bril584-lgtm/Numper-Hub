"""AnimePahe source backend."""
import re
import httpx

BASE = "https://animepahe.ru"
API = f"{BASE}/api"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
HEADERS = {"User-Agent": AGENT, "Referer": BASE}


async def search(query: str, dub: bool = False) -> list[dict]:
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as c:
            r = await c.get(API, params={"m": "search", "q": query})
            if r.status_code != 200:
                return []
            data = r.json().get("data") or []
    except Exception:
        return []

    results = []
    for item in data:
        title = item.get("title", "").strip()
        if not title:
            continue
        score_raw = item.get("score") or 0
        results.append({
            "id": item.get("session", ""),
            "title": title,
            "episodes": item.get("episodes", 0),
            "thumb": item.get("poster", ""),
            "source": "animepahe",
            "year": item.get("year", 0),
            "score": int(float(score_raw) * 10) if score_raw else 0,
        })
    return results


async def get_episode_count(show_session: str) -> int:
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
            r = await c.get(API, params={"m": "release", "id": show_session, "sort": "episode_asc", "page": 1})
            return r.json().get("total", 0)
    except Exception:
        return 0


async def _get_episode_session(show_session: str, ep: int) -> str | None:
    page = (ep - 1) // 30 + 1
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
            r = await c.get(API, params={"m": "release", "id": show_session, "sort": "episode_asc", "page": page})
            items = r.json().get("data") or []
        idx = (ep - 1) % 30
        if idx < len(items):
            return items[idx].get("session")
    except Exception:
        pass
    return None


async def _resolve_kwik(kwik_url: str) -> str | None:
    """Resolve a Kwik embed URL to an m3u8/mp4 via form POST."""
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=20) as c:
            r = await c.get(kwik_url, headers={"User-Agent": AGENT, "Referer": BASE})
            if r.status_code != 200:
                return None
            text = r.text
            action_m = re.search(r'action="(https://kwik\.cx/f/[^"]+)"', text)
            token_m = re.search(r'name="_token"\s+value="([^"]+)"', text)
            if not action_m:
                return None
            action = action_m.group(1)
            token = token_m.group(1) if token_m else ""
            r2 = await c.post(action, data={"_token": token}, headers={
                "User-Agent": AGENT,
                "Referer": kwik_url,
                "Content-Type": "application/x-www-form-urlencoded",
            })
            if r2.status_code in (301, 302, 303):
                loc = r2.headers.get("location", "")
                if ".m3u8" in loc or ".mp4" in loc:
                    return loc
    except Exception:
        pass
    return None


async def get_stream(show_session: str, ep: int, dub: bool = False) -> dict:
    ep_session = await _get_episode_session(show_session, ep)
    if not ep_session:
        return {"error": "AnimePahe: episode not found"}

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
            r = await c.get(API, params={"m": "links", "id": ep_session, "p": "kwik"})
            links_data = r.json().get("data") or []
    except Exception:
        return {"error": "AnimePahe: failed to fetch links"}

    if not links_data:
        return {"error": "AnimePahe: no links found"}

    # Format: [{"720": {"kwik": "url", ...}}, {"1080": {"kwik": "url"}}]
    kwik_urls: list[tuple[int, str]] = []
    for item in links_data:
        for quality_str, v in item.items():
            kwik = v.get("kwik", "") if isinstance(v, dict) else (v if isinstance(v, str) else "")
            if not kwik:
                continue
            try:
                q = int(quality_str.replace("p", ""))
            except (ValueError, TypeError):
                q = 0
            kwik_urls.append((q, kwik))

    kwik_urls.sort(reverse=True)

    for _, kwik_url in kwik_urls:
        stream = await _resolve_kwik(kwik_url)
        if stream:
            return {"url": stream, "type": "hls" if ".m3u8" in stream else "mp4", "source": "animepahe"}
        try:
            from . import playwright_extractor
            stream = await playwright_extractor.extract_stream(kwik_url)
            if stream:
                return {"url": stream, "type": "hls" if ".m3u8" in stream else "mp4", "source": "animepahe"}
        except Exception:
            pass

    return {"error": "AnimePahe: all Kwik sources exhausted"}
