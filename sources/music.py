"""Music streaming via JioSaavn unofficial API — full tracks, no key needed."""
import asyncio
import httpx

BASE = "https://jiosavan-api2.vercel.app/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "application/json",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _best_image(images: list) -> str:
    if not images:
        return ""
    for img in reversed(images):
        url = img.get("url") or img.get("link") or ""
        if url:
            return url.replace("150x150", "500x500").replace("50x50", "500x500")
    return ""

def _best_url(download_urls: list) -> str:
    """Always pick highest available quality. JioSaavn tops at 320kbps AAC."""
    if not download_urls:
        return ""
    for quality in ["320kbps", "160kbps", "96kbps", "48kbps", "12kbps"]:
        for d in download_urls:
            if d.get("quality") == quality and d.get("url"):
                return d["url"]
    # fallback: last entry (usually highest)
    return download_urls[-1].get("url") or ""

def _primary_artist(song: dict) -> str:
    artists = song.get("artists") or {}
    if isinstance(artists, dict):
        primary = artists.get("primary") or []
        if primary and isinstance(primary, list):
            return ", ".join(a.get("name", "") for a in primary if a.get("name"))
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
        r = await c.get(f"{BASE}/songs", params={"ids": song_id})
    data = r.json()
    songs = data.get("data") or []
    return _card(songs[0]) if songs else {}


# ── Home ──────────────────────────────────────────────────────────────────────

# Only these languages appear on the front page; search is unrestricted
_HOME_LANGUAGES = {"english", "spanish"}

# Each row has multiple distinct queries — merged & globally deduplicated
# so no song ever appears twice across the whole home page.
_ROWS = [
    ("🔥 Trending Now", [
        "billboard hot 100 2025",
        "top 40 english hits 2025",
        "number one songs english 2025",
    ]),
    ("🎵 Pop", [
        "taylor swift sabrina carpenter 2025",
        "ariana grande dua lipa english pop",
        "pop radio hits english 2025",
    ]),
    ("🎤 Hip-Hop", [
        "drake kendrick lamar 2025",
        "travis scott future hip hop english",
        "rap hits english 2025 new",
    ]),
    ("💿 R&B", [
        "the weeknd sza usher rnb english",
        "beyonce frank ocean rnb soul",
        "rnb slow jam english 2025",
    ]),
    ("🎸 Rock", [
        "imagine dragons coldplay english rock 2025",
        "alternative rock english hits",
        "linkin park green day english rock",
    ]),
    ("🌙 Chill / Lo-fi", [
        "chill indie english 2025",
        "lo-fi beats study english",
        "bedroom pop english slow 2025",
    ]),
    ("💃 Latin", [
        "bad bunny karol g 2025",
        "j balvin ozuna reggaeton 2025",
        "shakira maluma latin pop 2025",
    ]),
    ("🎹 Electronic", [
        "calvin harris david guetta edm english",
        "electronic dance music english 2025",
        "martin garrix tiesto english edm",
    ]),
    ("🎬 Movie & TV Hits", [
        "guardians of the galaxy soundtrack english",
        "marvel disney english movie songs 2025",
        "top gun interstellar english film score",
    ]),
]


async def get_home() -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=25) as c:

        async def _fetch_row(label: str, queries: list[str]) -> tuple[str, list]:
            """Fetch multiple queries in parallel, merge, deduplicate within row."""
            tasks = [
                c.get(f"{BASE}/search/songs", params={"query": q, "limit": 30})
                for q in queries
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            seen_in_row: set[str] = set()
            merged: list[dict] = []
            for resp in responses:
                if isinstance(resp, Exception):
                    continue
                try:
                    songs = (resp.json().get("data") or {}).get("results") or []
                    for s in songs:
                        sid = s.get("id")
                        lang = s.get("language", "").lower()
                        if sid and sid not in seen_in_row and lang in _HOME_LANGUAGES:
                            merged.append(s)
                            seen_in_row.add(sid)
                except Exception:
                    pass
            return label, merged

        # All rows fetch in parallel
        fetched = await asyncio.gather(*[_fetch_row(lbl, qs) for lbl, qs in _ROWS])

    # Global deduplication — earlier rows (Trending) have priority
    global_seen: set[str] = set()
    rows: list[dict] = []
    for label, songs in fetched:
        unique = [s for s in songs if s.get("id") not in global_seen]
        global_seen.update(s["id"] for s in unique)
        items = [_card(s) for s in unique[:20]]
        if items:
            rows.append({"label": label, "items": items})

    trending = rows[0]["items"][:8] if rows else []
    return {"trending": trending, "rows": rows}
