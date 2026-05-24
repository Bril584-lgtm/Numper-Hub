"""Numper Music — standalone FastAPI server."""
import time
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

app = FastAPI(title="Numper Music", docs_url=None, redoc_url=None)

STATIC = Path(__file__).parent / "static"

_cache: dict = {}
_CACHE_TTL = 1800  # 30 min

def _cached(key: str, ttl: int = _CACHE_TTL):
    entry = _cache.get(key)
    if entry and time.time() - entry[1] < ttl:
        return entry[0]
    return None

def _store(key: str, val):
    _cache[key] = (val, time.time())
    return val


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC / "music.html").read_text(encoding="utf-8")


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/api/music/home")
async def api_music_home():
    cached = _cached("music_home")
    if cached:
        return cached
    from sources.music import get_home
    data = await get_home()
    return _store("music_home", data)


@app.get("/api/music/search")
async def api_music_search(q: str = Query(..., min_length=1)):
    from sources.music import search
    return {"results": await search(q, limit=20)}


@app.get("/api/music/suggest")
async def api_music_suggest(q: str = Query(..., min_length=1)):
    from sources.music import search
    return {"results": await search(q, limit=8)}


@app.get("/api/music/song")
async def api_music_song(id: str = Query(...)):
    cached = _cached(f"music:song:{id}", 3600)
    if cached:
        return cached
    from sources.music import get_song
    data = await get_song(id)
    if not data or not data.get("url"):
        raise HTTPException(status_code=404, detail="Song not found or no stream available")
    return _store(f"music:song:{id}", data)


@app.get("/api/music/album")
async def api_music_album(id: str = Query(...)):
    cached = _cached(f"music:album:{id}", 3600)
    if cached:
        return cached
    from sources.music import get_album
    data = await get_album(id)
    if not data:
        raise HTTPException(status_code=404, detail="Album not found")
    return _store(f"music:album:{id}", data)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7779, reload=False)
