"""Numper Hub — FastAPI backend."""
import time
from pathlib import Path

import httpx
import urllib.parse
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from config import TMDB_API_KEY

app = FastAPI(title="Numper Hub", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC = Path(__file__).parent / "static"

_cache: dict = {}
_CACHE_TTL = 1800  # 30 min

_PROXY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "*/*",
}


def _cached(key: str, ttl: int = _CACHE_TTL):
    entry = _cache.get(key)
    if entry and time.time() - entry[1] < ttl:
        return entry[0]
    return None


def _store(key: str, val):
    _cache[key] = (val, time.time())
    return val


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def hub():
    return (STATIC / "hub.html").read_text(encoding="utf-8")


@app.get("/movies", response_class=HTMLResponse)
async def movies_page():
    return (STATIC / "movies.html").read_text(encoding="utf-8")


@app.get("/spanish", response_class=HTMLResponse)
async def spanish_page():
    return (STATIC / "spanish.html").read_text(encoding="utf-8")


# ─── Health / key check ───────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    return {"tmdb_key": bool(TMDB_API_KEY), "ok": bool(TMDB_API_KEY)}


# ─── Movies home ──────────────────────────────────────────────────────────────

@app.get("/api/movies/home")
async def api_movies_home():
    cached = _cached("movies_home")
    if cached:
        return cached
    from sources.tmdb import fetch_home
    data = await fetch_home()
    return _store("movies_home", data)


@app.get("/api/spanish/home")
async def api_spanish_home():
    cached = _cached("spanish_home")
    if cached:
        return cached
    from sources.tmdb import fetch_spanish_home
    data = await fetch_spanish_home()
    return _store("spanish_home", data)


# ─── Search ───────────────────────────────────────────────────────────────────

@app.get("/api/movies/search")
async def api_movies_search(q: str = Query(..., min_length=1)):
    from sources.tmdb import search
    return {"results": await search(q)}


@app.get("/api/spanish/search")
async def api_spanish_search(q: str = Query(..., min_length=1)):
    from sources.tmdb import search_spanish
    return {"results": await search_spanish(q)}


# ─── Details ──────────────────────────────────────────────────────────────────

@app.get("/api/details")
async def api_details(id: int = Query(...), type: str = Query(...), lang: str = Query(default="en-US")):
    cache_key = f"details:{id}:{type}:{lang}"
    cached = _cached(cache_key, 3600)
    if cached:
        return cached
    from sources.tmdb import get_details
    data = await get_details(id, type, lang)
    return _store(cache_key, data)


@app.get("/api/season")
async def api_season(id: int = Query(...), season: int = Query(..., ge=1)):
    cache_key = f"season:{id}:{season}"
    cached = _cached(cache_key, 3600)
    if cached:
        return cached
    from sources.tmdb import get_season_episodes
    eps = await get_season_episodes(id, season)
    return _store(cache_key, {"episodes": eps})


# ─── Streaming ────────────────────────────────────────────────────────────────

@app.get("/api/stream/movie")
async def api_stream_movie(id: int = Query(...)):
    cache_key = f"stream:movie:{id}"
    cached = _cached(cache_key, 2700)
    if cached:
        return cached
    from sources.vidsrc import get_movie_stream
    result = await get_movie_stream(id)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return _store(cache_key, result)


@app.get("/api/stream/tv")
async def api_stream_tv(id: int = Query(...), season: int = Query(..., ge=1), ep: int = Query(..., ge=1)):
    cache_key = f"stream:tv:{id}:{season}:{ep}"
    cached = _cached(cache_key, 2700)
    if cached:
        return cached
    from sources.vidsrc import get_tv_stream
    result = await get_tv_stream(id, season, ep)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return _store(cache_key, result)


# ─── Suggest ──────────────────────────────────────────────────────────────────

@app.get("/api/suggest")
async def api_suggest(q: str = Query(..., min_length=1), lang: str = Query(default="en-US")):
    from sources.tmdb import search
    results = await search(q, language=lang)
    return {"results": [{"title": r["title"], "thumb": r["thumb"], "type": r["type"], "year": r["year"]} for r in results[:8]]}


# ─── Proxy ────────────────────────────────────────────────────────────────────

@app.get("/api/proxy")
async def proxy(url: str = Query(...), request: Request = None):
    range_header = request.headers.get("range") if request else None
    req_headers = {**_PROXY_HEADERS}
    if range_header:
        req_headers["Range"] = range_header
    async with httpx.AsyncClient(headers=req_headers, follow_redirects=True, timeout=30) as c:
        r = await c.get(url)
    ctype = r.headers.get("content-type", "application/octet-stream")
    resp_headers = {"Access-Control-Allow-Origin": "*"}
    for h in ("content-range", "accept-ranges", "content-length"):
        if h in r.headers:
            resp_headers[h] = r.headers[h]
    if ".m3u8" in url or "mpegurl" in ctype.lower():
        resp_headers["Cache-Control"] = "no-cache"
        return Response(content=r.content, media_type="application/vnd.apple.mpegurl", headers=resp_headers)
    return Response(content=r.content, status_code=r.status_code, media_type=ctype, headers=resp_headers)
