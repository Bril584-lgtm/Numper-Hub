"""Music streaming via JioSaavn unofficial API (saavn.dev) — full tracks, no key needed."""
import asyncio
import httpx

BASE = "https://saavn.dev/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "application/json",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _best_image(images: list) -> str:
    if not images:
        return ""
    for img in reversed(images):  # last entry is usually largest
        url = img.get("url") or img.get("link") or ""
        if url:
            return url.replace("150x150", "500x500").replace("50x50", "500x500")
    return ""

def _best_url(download_urls: list) -> str:
    if not download_urls:
        return ""
    for quality in ["320kbps", "160kbps", "96kbps", "48kbps", "12kbps"]:
        for d in download_urls:
            if d.get("quality") == quality and d.get("url"):
                return d["url"]
    return (download_urls[0].get("url") or "") if download_urls else ""

def _primary_artist(song: dict) -> str:
    # saavn.dev returns artists as dict with "primary" list, or plain string
    artists = song.get("artists") or {}
    if isinstance(artists, dict):
        primary = artists.get("primary") or []
        if primary and isinstance(primary, list):
            return ", ".join(a.get("name", "") for a in primary if a.get("name"))
    # fallback: plain string field
    return song.get("primaryArtists") or song.get("artist") or ""

def _card(song: dict) -> dict:
    album = song.get("album") or {}
    return {
        "id":       song.get("id", ""),
        "title":    song.get("name", "") or song.get("title", ""),
        "artist":   _primary_artist(song),
        "album":    album.get("name", "") if isinstance(album, dict) else str(album),
        "year":     str(song.get("year", "") or ""),
        "duration": int(song.get("duration") or 0),
        "thumb":    _best_image(song.get("image", [])),
        "url":      _best_url(song.get("downloadUrl", [])),
        "language": song.get("language", ""),
    }


# ── Search ────────────────────────────────────────────────────────────────────

async def search(query: str, limit: int = 20) -> list[dict]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.get(f"{BASE}/search/songs", params={"query": query, "limit": limit})
    data = r.json()
    songs = (data.get("data") or {}).get("results") or []
    return [_card(s) for s in songs if s.get("id")]


# ── Single song (stream URL on demand) ───────────────────────────────────────

async def get_song(song_id: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.get(f"{BASE}/songs/{song_id}")
    data = r.json()
    songs = data.get("data") or []
    return _card(songs[0]) if songs else {}


# ── Home ──────────────────────────────────────────────────────────────────────

_ROWS = [
    ("🔥 Trending Now",    "top hits 2025"),
    ("🎵 Pop",             "pop songs 2025"),
    ("🎤 Hip-Hop",         "hip hop rap 2025"),
    ("💿 R&B",             "rnb soul 2025"),
    ("🎸 Rock",            "rock hits 2025"),
    ("🌙 Chill / Lo-fi",   "chill lofi 2025"),
    ("💃 Latin",           "latin reggaeton 2025"),
    ("🎹 Electronic",      "edm electronic 2025"),
    ("🎬 Movie Hits",      "movie soundtrack hits 2025"),
]


async def get_home() -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as c:
        async def _row(label: str, query: str) -> dict:
            try:
                r = await c.get(f"{BASE}/search/songs", params={"query": query, "limit": 20})
                songs = (r.json().get("data") or {}).get("results") or []
                items = [_card(s) for s in songs if s.get("id")]
                return {"label": label, "items": items}
            except Exception:
                return {"label": label, "items": []}

        results = await asyncio.gather(*[_row(lbl, q) for lbl, q in _ROWS])

    rows = [r for r in results if r["items"]]
    trending = rows[0]["items"][:8] if rows else []
    return {"trending": trending, "rows": rows}
