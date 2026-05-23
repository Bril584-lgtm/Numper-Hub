"""hanime.tv — search and stream via unofficial API."""
import json
import urllib.parse
import httpx

SEARCH_URL = "https://search.htv-services.com/"
API_URL    = "https://hanime.tv/api/v8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://hanime.tv/",
}


def _parse_hits(data: dict) -> list:
    raw = data.get("hits") or data.get("results") or []
    return json.loads(raw) if isinstance(raw, str) else raw


def _proxied_img(url: str) -> str:
    if not url:
        return ""
    return f"/api/imgproxy?url={urllib.parse.quote(url, safe='')}"


def _pd_stream(dl_url: str) -> str:
    """Convert pixeldrain share URL to direct API stream URL."""
    if dl_url and "pixeldrain.com/u/" in dl_url:
        pid = dl_url.split("/u/")[-1].split("?")[0].strip()
        return f"https://pixeldrain.com/api/file/{pid}"
    return ""


def _card(item: dict) -> dict:
    return {
        "id":    item.get("slug") or str(item.get("id", "")),
        "title": item.get("name", ""),
        "thumb": _proxied_img(item.get("cover_url", "") or item.get("poster_url", "")),
        "brand": item.get("brand", ""),
        "views": item.get("views", 0),
        "tags":  [t.get("text", "") for t in (item.get("hentai_tags") or []) if isinstance(t, dict)],
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
    return [_card(i) for i in _parse_hits(r.json())]


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
    return [_card(i) for i in _parse_hits(r.json())]


async def get_video(slug: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.get(f"{API_URL}/video", params={"id": slug})
    d = r.json()
    v = d.get("hentai_video") or {}
    tags = [t.get("text", "") for t in (d.get("hentai_tags") or []) if isinstance(t, dict)]

    stream = _pd_stream(d.get("dl_url", ""))
    stream_type = "mp4" if stream else ""

    # Fallback: try HLS servers if no Pixeldrain link
    if not stream:
        for server in (d.get("videos_manifest") or {}).get("servers") or []:
            for s in (server.get("streams") or []):
                url = s.get("url", "")
                if url and ".m3u8" in url and "streamable.cloud" not in url:
                    stream = url
                    stream_type = "hls"
                    break
            if stream:
                break

    return {
        "id":          slug,
        "title":       v.get("name", ""),
        "thumb":       _proxied_img(v.get("cover_url", "") or v.get("poster_url", "")),
        "brand":       v.get("brand", ""),
        "synopsis":    v.get("description", ""),
        "tags":        tags,
        "stream":      stream,
        "stream_type": stream_type,
    }
