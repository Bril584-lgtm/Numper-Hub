"""Numper Hub — FastAPI backend."""
import asyncio
import json
import re
import time
from pathlib import Path

import httpx
import urllib.parse
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from config import TMDB_API_KEY

HISTORY_FILE = Path(__file__).parent / "history.json"

_stream_cache: dict = {}
_STREAM_TTL = 2700

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


@app.get("/hentai", response_class=HTMLResponse)
async def hentai_page():
    return (STATIC / "hentai.html").read_text(encoding="utf-8")


@app.get("/anime", response_class=HTMLResponse)
async def anime_page():
    return (STATIC / "anime.html").read_text(encoding="utf-8")


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


# ─── Anime ────────────────────────────────────────────────────────────────────

def _load_history() -> dict:
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text())
        except Exception: pass
    return {}

def _save_history(h: dict):
    HISTORY_FILE.write_text(json.dumps(h, indent=2))

def _rewrite_m3u8(content: str, base_url: str) -> str:
    base = base_url.rsplit("/", 1)[0] + "/"
    lines = []
    for line in content.splitlines():
        s = line.strip()
        if not s:
            lines.append(line); continue
        if s.startswith("#"):
            def _rep(m):
                uri = m.group(1)
                abs_uri = uri if uri.startswith("http") else base + uri
                return f'URI="/api/proxy?url={urllib.parse.quote(abs_uri, safe="")}"'
            lines.append(re.sub(r'URI="([^"]+)"', _rep, s))
        else:
            abs_url = s if s.startswith("http") else base + s
            lines.append(f"/api/proxy?url={urllib.parse.quote(abs_url, safe='')}")
    return "\n".join(lines)

_JIKAN_BASE = "https://api.jikan.moe/v4"
_JIKAN_BATCH = 3

async def _jikan_page(c, lup, jpage, sfw=True):
    params = {"page": jpage, "limit": 25, "order_by": "popularity", "sort": "asc"}
    if lup and lup != "#": params["letter"] = lup
    if sfw: params["sfw"] = "true"
    try:
        r = await c.get(f"{_JIKAN_BASE}/anime", params=params)
        if r.status_code == 429: return {}
        return r.json()
    except Exception: return {}

@app.get("/api/anime/home")
async def api_anime_home(nsfw: bool = False):
    cache_key = f"anime_home:{'nsfw' if nsfw else 'safe'}"
    cached = _cached(cache_key)
    if cached: return cached
    from sources.anilist_home import fetch_home_data
    data = await fetch_home_data(nsfw=nsfw)
    return _store(cache_key, data)

@app.get("/api/anime/suggest")
async def api_anime_suggest(q: str = Query(..., min_length=1)):
    gql = "query($s:String){Page(page:1,perPage:8){media(search:$s,type:ANIME,sort:SEARCH_MATCH){title{romaji english}coverImage{medium}format}}}"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post("https://graphql.anilist.co",
                json={"query": gql, "variables": {"s": q}},
                headers={"Content-Type": "application/json", "Accept": "application/json"})
            media = r.json().get("data", {}).get("Page", {}).get("media", [])
        results = []
        for m in media:
            t = m.get("title") or {}
            title = t.get("english") or t.get("romaji") or ""
            if title:
                results.append({"title": title, "thumb": (m.get("coverImage") or {}).get("medium", ""), "format": m.get("format", "")})
        return {"results": results}
    except Exception:
        return {"results": []}

@app.get("/api/anime/browse")
async def api_anime_browse(letter: str = Query(default="A"), page: int = Query(default=1, ge=1), nsfw: bool = False, dub: bool = False):
    lup = letter.upper() if letter.upper().isalpha() else "#"
    jikan_start = (page - 1) * _JIKAN_BATCH + 1
    sfw = not nsfw
    async with httpx.AsyncClient(timeout=20) as c:
        pages_data = await asyncio.gather(*[_jikan_page(c, lup, jikan_start + i, sfw=sfw) for i in range(_JIKAN_BATCH)])
    _ADULT = {"rx - hentai", "r+ - mild nudity"}
    results, has_next, total = [], False, 0
    for data in pages_data:
        if not data: continue
        pag = data.get("pagination") or {}
        if not total: total = (pag.get("items") or {}).get("total", 0)
        has_next = pag.get("has_next_page", False)
        for m in (data.get("data") or []):
            title = (m.get("title_english") or m.get("title") or "").strip()
            if not title: continue
            first = title[0].upper()
            if lup == "#":
                if first.isalpha(): continue
            elif first != lup: continue
            rating = (m.get("rating") or "").lower()
            if not nsfw and any(r in rating for r in _ADULT): continue
            imgs = m.get("images") or {}
            jpg = imgs.get("jpg") or {}
            results.append({"title": title, "thumb": jpg.get("large_image_url") or jpg.get("image_url") or "", "format": m.get("type") or "", "score": int((m.get("score") or 0) * 10), "year": m.get("year") or 0})
    return {"results": results, "has_next": has_next, "total": total}

@app.get("/api/anime/search")
async def api_anime_search(q: str = Query(..., min_length=1), dub: bool = False, nsfw: bool = False):
    from sources import router as sr
    results = await sr.search_all(q, dub=dub, nsfw=nsfw)
    return {"results": results}

@app.get("/api/anime/stream")
async def api_anime_stream(source: str = Query(...), id: str = Query(...), ep: int = Query(..., ge=1), dub: bool = False):
    cache_key = f"astream:{source}:{id}:{ep}:{dub}"
    cached = _stream_cache.get(cache_key)
    if cached:
        result, ts = cached
        if time.time() - ts < _STREAM_TTL: return result
    from sources import router as sr
    result = await sr.get_stream(source, id, ep, dub=dub)
    if "error" in result: raise HTTPException(status_code=502, detail=result["error"])
    _stream_cache[cache_key] = (result, time.time())
    return result

@app.get("/api/anime/sources")
async def api_anime_sources(source: str = Query(...), id: str = Query(...), ep: int = Query(..., ge=1), dub: bool = False):
    from sources import allanime
    if source == "allanime":
        srcs = await allanime.get_episode_sources(id, str(ep), dub=dub)
        return {"sources": [{"name": s["name"], "url": s["url"], "stype": s.get("stype", "")} for s in srcs]}
    return {"sources": []}

@app.get("/api/anime/resolve")
async def api_anime_resolve(embed_url: str = Query(...), name: str = Query(default="")):
    from sources import allanime, playwright_extractor
    url = embed_url
    if "fast4speed" in url or (url.startswith("http") and url.endswith(".mp4")):
        return {"url": f"/api/proxy?url={urllib.parse.quote(url, safe='')}", "type": "mp4", "source": name}
    if ".m3u8" in url or ".mp4" in url.split("?")[0]:
        return {"url": url, "type": "hls" if ".m3u8" in url else "mp4", "source": name}
    if "/apivtwo/" in url or "/clock" in url:
        direct = await allanime.resolve_clock(url)
        if direct: return {"url": direct, "type": "hls" if ".m3u8" in direct else "mp4", "source": name}
    try:
        stream = await playwright_extractor.extract_stream(embed_url)
        if stream: return {"url": stream, "type": "hls" if ".m3u8" in stream else "mp4", "source": name}
    except Exception: pass
    raise HTTPException(status_code=502, detail=f"Could not resolve: {name}")

@app.get("/api/anime/episodes")
async def api_anime_episodes(source: str = Query(...), id: str = Query(...)):
    from sources import router as sr
    count = await sr.get_episode_count(source, id)
    return {"count": count}

@app.get("/api/anime/skiptimes")
async def api_anime_skiptimes(mal_id: int = Query(...), ep: int = Query(..., ge=1)):
    if not mal_id: return {"found": False, "results": []}
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"https://api.aniskip.com/v2/skip-times/{mal_id}/{ep}", params={"types[]": ["op", "recap", "ed"]})
            return r.json()
    except Exception:
        return {"found": False, "results": []}

@app.get("/api/anime/subtitles")
async def api_anime_subtitles(title: str = Query(...), ep: int = Query(..., ge=1)):
    from sources.subtitles import fetch as fetch_subs
    subs = await fetch_subs(title, ep)
    return {"subtitles": subs}

@app.get("/api/anime/history")
async def get_anime_history():
    return _load_history()

@app.post("/api/anime/history")
async def save_anime_history(body: dict):
    h = _load_history()
    key = f"{body['source']}:{body['id']}"
    h[key] = {"title": body.get("title",""), "source": body.get("source",""), "id": body.get("id",""), "ep": body.get("ep",1), "dub": body.get("dub",False), "thumb": body.get("thumb","")}
    _save_history(h)
    return {"ok": True}


# ─── Hentai ───────────────────────────────────────────────────────────────────

@app.get("/api/hentai/browse")
async def api_hentai_browse(order: str = Query(default="views_month"), page: int = Query(default=0, ge=0)):
    cache_key = f"hentai:browse:{order}:{page}"
    cached = _cached(cache_key, 1800)
    if cached:
        return cached
    from sources.hanime import browse
    results = await browse(order_by=order, page=page)
    return _store(cache_key, {"results": results})


@app.get("/api/hentai/search")
async def api_hentai_search(q: str = Query(..., min_length=1), page: int = Query(default=0, ge=0)):
    from sources.hanime import search
    results = await search(q, page=page)
    return {"results": results}


@app.get("/api/hentai/video")
async def api_hentai_video(id: str = Query(...)):
    cache_key = f"hentai:video:{id}"
    cached = _cached(cache_key, 3600)
    if cached:
        return cached
    from sources.hanime import get_video
    data = await get_video(id)
    return _store(cache_key, data)


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
