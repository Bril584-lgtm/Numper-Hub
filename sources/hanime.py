"""hanime.tv — search and stream via unofficial API."""
import httpx

SEARCH_URL = "https://search.htv-services.com/"
API_URL    = "https://hanime.tv/api/v8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://hanime.tv/",
}


def _card(item: dict) -> dict:
    return {
        "id":    item.get("slug") or item.get("id", ""),
        "title": item.get("name", ""),
        "thumb": item.get("cover_url", ""),
        "brand": item.get("brand", ""),
        "views": item.get("views", 0),
        "tags":  [t.get("text", "") for t in (item.get("hentai_tags") or [])],
    }


async def browse(order_by: str = "views_month", page: int = 0) -> list[dict]:
    payload = {
        "search_text": "",
        "tags": [],
        "tags_mode": "AND",
        "brands": [],
        "blacklist": [],
        "order_by": order_by,
        "ordering": "desc",
        "page": page,
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.post(SEARCH_URL, json=payload)
    data = r.json()
    items = data if isinstance(data, list) else (data.get("hits") or data.get("results") or [])
    return [_card(i) for i in items]


async def search(query: str, page: int = 0) -> list[dict]:
    payload = {
        "search_text": query,
        "tags": [],
        "tags_mode": "AND",
        "brands": [],
        "blacklist": [],
        "order_by": "views_month",
        "ordering": "desc",
        "page": page,
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.post(SEARCH_URL, json=payload)
    data = r.json()
    items = data if isinstance(data, list) else (data.get("hits") or data.get("results") or [])
    return [_card(i) for i in items]


async def get_video(slug: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.get(f"{API_URL}/video", params={"id": slug})
    d = r.json()
    v = d.get("hentai_video") or {}
    manifest = d.get("videos_manifest") or {}
    servers = manifest.get("servers") or []

    streams = []
    for server in servers:
        for s in (server.get("streams") or []):
            url = s.get("url", "")
            if url and ".m3u8" in url:
                streams.append({"url": url, "height": s.get("height", 0)})

    streams.sort(key=lambda x: x["height"], reverse=True)
    best = streams[0]["url"] if streams else ""

    return {
        "id":       slug,
        "title":    v.get("name", ""),
        "thumb":    v.get("cover_url", ""),
        "brand":    v.get("brand", ""),
        "synopsis": v.get("description", ""),
        "tags":     [t.get("text", "") for t in (v.get("hentai_tags") or [])],
        "streams":  streams,
        "stream":   best,
    }
