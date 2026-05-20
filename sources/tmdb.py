"""TMDB metadata — movies, TV, and Spanish content."""
import httpx
from config import TMDB_API_KEY

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"


def _headers():
    return {"User-Agent": AGENT, "Authorization": f"Bearer {TMDB_API_KEY}"}


def _img(path: str, size: str = "w500") -> str:
    return f"{IMG}/{size}{path}" if path else ""


def _card(item: dict, media_type: str = "") -> dict:
    mt = media_type or item.get("media_type", "movie")
    is_tv = mt == "tv"
    title = item.get("title") or item.get("name") or ""
    return {
        "id": item.get("id"),
        "title": title,
        "thumb": _img(item.get("poster_path", ""), "w342"),
        "banner": _img(item.get("backdrop_path", ""), "w1280"),
        "synopsis": item.get("overview", ""),
        "score": round((item.get("vote_average") or 0) * 10),
        "year": (item.get("release_date") or item.get("first_air_date") or "")[:4],
        "type": "tv" if is_tv else "movie",
        "genres": [],
    }


# ─── Home data ────────────────────────────────────────────────────────────────

async def fetch_home(language: str = "en-US") -> dict:
    """Trending + genre rows for the movies homepage."""
    async with httpx.AsyncClient(headers=_headers(), timeout=15) as c:
        trending_r, popular_movies_r, popular_tv_r, action_r, comedy_r, drama_r, thriller_r = await _gather(c, [
            f"/trending/all/week?language={language}",
            f"/movie/popular?language={language}",
            f"/tv/popular?language={language}",
            f"/discover/movie?with_genres=28&sort_by=popularity.desc&language={language}",
            f"/discover/movie?with_genres=35&sort_by=popularity.desc&language={language}",
            f"/discover/tv?with_genres=18&sort_by=popularity.desc&language={language}",
            f"/discover/movie?with_genres=53&sort_by=popularity.desc&language={language}",
        ])

    def extract(r, mt=""):
        return [_card(i, mt) for i in (r.get("results") or []) if (i.get("title") or i.get("name"))]

    trending = extract(trending_r)
    return {
        "trending": trending,
        "rows": [
            {"label": "Popular Movies",    "items": extract(popular_movies_r, "movie")},
            {"label": "Popular TV Shows",  "items": extract(popular_tv_r, "tv")},
            {"label": "Action",            "items": extract(action_r, "movie")},
            {"label": "Comedy",            "items": extract(comedy_r, "movie")},
            {"label": "Drama",             "items": extract(drama_r, "tv")},
            {"label": "Thriller",          "items": extract(thriller_r, "movie")},
        ],
    }


async def fetch_spanish_home() -> dict:
    """Trending + genre rows for Spanish content."""
    async with httpx.AsyncClient(headers=_headers(), timeout=15) as c:
        trending_r, telenovelas_r, movies_r, action_r, comedy_r, crime_r = await _gather(c, [
            "/trending/all/week?language=es-MX&region=MX",
            "/discover/tv?with_original_language=es&sort_by=popularity.desc&with_genres=10766",
            "/discover/movie?with_original_language=es&sort_by=popularity.desc",
            "/discover/movie?with_original_language=es&with_genres=28&sort_by=popularity.desc",
            "/discover/tv?with_original_language=es&with_genres=35&sort_by=popularity.desc",
            "/discover/tv?with_original_language=es&with_genres=80&sort_by=popularity.desc",
        ])

    def extract(r, mt=""):
        return [_card(i, mt) for i in (r.get("results") or []) if (i.get("title") or i.get("name"))]

    return {
        "trending": extract(trending_r),
        "rows": [
            {"label": "Telenovelas",        "items": extract(telenovelas_r, "tv")},
            {"label": "Spanish Movies",     "items": extract(movies_r, "movie")},
            {"label": "Acción",             "items": extract(action_r, "movie")},
            {"label": "Comedia",            "items": extract(comedy_r, "tv")},
            {"label": "Crimen & Drama",     "items": extract(crime_r, "tv")},
        ],
    }


# ─── Search ───────────────────────────────────────────────────────────────────

async def search(query: str, language: str = "en-US") -> list[dict]:
    async with httpx.AsyncClient(headers=_headers(), timeout=10) as c:
        r = await c.get(f"{BASE}/search/multi", params={"query": query, "language": language, "page": 1})
    results = []
    for item in (r.json().get("results") or []):
        mt = item.get("media_type", "movie")
        if mt not in ("movie", "tv"):
            continue
        results.append(_card(item, mt))
    return results


async def search_spanish(query: str) -> list[dict]:
    async with httpx.AsyncClient(headers=_headers(), timeout=10) as c:
        r = await c.get(f"{BASE}/search/multi", params={"query": query, "language": "es-MX", "page": 1})
    results = []
    for item in (r.json().get("results") or []):
        mt = item.get("media_type", "movie")
        if mt not in ("movie", "tv"):
            continue
        lang = item.get("original_language", "")
        if lang != "es":
            continue
        results.append(_card(item, mt))
    return results


# ─── Details ──────────────────────────────────────────────────────────────────

async def get_details(tmdb_id: int, media_type: str, language: str = "en-US") -> dict:
    path = "tv" if media_type == "tv" else "movie"
    async with httpx.AsyncClient(headers=_headers(), timeout=10) as c:
        r = await c.get(f"{BASE}/{path}/{tmdb_id}", params={"language": language})
    d = r.json()
    card = _card(d, media_type)
    if media_type == "tv":
        card["seasons"] = d.get("number_of_seasons", 1)
        card["episodes"] = d.get("number_of_episodes", 0)
        seasons = []
        for s in (d.get("seasons") or []):
            if s.get("season_number", 0) > 0:
                seasons.append({
                    "number": s["season_number"],
                    "name": s.get("name", f"Season {s['season_number']}"),
                    "episodes": s.get("episode_count", 0),
                })
        card["season_list"] = seasons
    card["genres"] = [g["name"] for g in (d.get("genres") or [])]
    return card


async def get_season_episodes(tmdb_id: int, season: int) -> list[dict]:
    async with httpx.AsyncClient(headers=_headers(), timeout=10) as c:
        r = await c.get(f"{BASE}/tv/{tmdb_id}/season/{season}")
    eps = []
    for e in (r.json().get("episodes") or []):
        eps.append({
            "number": e.get("episode_number"),
            "name": e.get("name", ""),
            "thumb": _img(e.get("still_path", ""), "w300"),
            "overview": e.get("overview", ""),
        })
    return eps


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _gather(c: httpx.AsyncClient, paths: list[str]) -> list[dict]:
    import asyncio
    async def _get(path):
        try:
            r = await c.get(f"{BASE}{path}")
            return r.json()
        except Exception:
            return {}
    return await asyncio.gather(*[_get(p) for p in paths])
