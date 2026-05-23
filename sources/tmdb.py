"""TMDB metadata — movies, TV, and Spanish content."""
import datetime
import httpx
from config import TMDB_API_KEY

_TODAY = datetime.date.today().isoformat()  # "YYYY-MM-DD"

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"


def _headers():
    return {"User-Agent": AGENT}


def _params(extra: dict | None = None) -> dict:
    p = {"api_key": TMDB_API_KEY}
    if extra:
        p.update(extra)
    return p


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
        return [_card(i, mt) for i in (r.get("results") or [])
                if (i.get("title") or i.get("name"))
                and (i.get("release_date") or i.get("first_air_date") or "9999") <= _TODAY]

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
        return [_card(i, mt) for i in (r.get("results") or [])
                if (i.get("title") or i.get("name"))
                and (i.get("release_date") or i.get("first_air_date") or "9999") <= _TODAY]

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
        r = await c.get(f"{BASE}/search/multi", params=_params({"query": query, "language": language, "page": 1}))
    results = []
    for item in (r.json().get("results") or []):
        mt = item.get("media_type", "movie")
        if mt not in ("movie", "tv"):
            continue
        results.append(_card(item, mt))
    return results


async def search_spanish(query: str) -> list[dict]:
    async with httpx.AsyncClient(headers=_headers(), timeout=10) as c:
        r = await c.get(f"{BASE}/search/multi", params=_params({"query": query, "language": "es-MX", "page": 1}))
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
        r = await c.get(f"{BASE}/{path}/{tmdb_id}", params=_params({"language": language}))
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
        r = await c.get(f"{BASE}/tv/{tmdb_id}/season/{season}", params=_params())
    eps = []
    for e in (r.json().get("episodes") or []):
        eps.append({
            "number": e.get("episode_number"),
            "name": e.get("name", ""),
            "thumb": _img(e.get("still_path", ""), "w300"),
            "overview": e.get("overview", ""),
        })
    return eps


# ─── TV Home ──────────────────────────────────────────────────────────────────

async def fetch_tv_home(language: str = "en-US") -> dict:
    """Trending + genre rows for the TV Shows homepage."""
    async with httpx.AsyncClient(headers=_headers(), timeout=15) as c:
        trending_r, popular_r, drama_r, scifi_r, crime_r, comedy_r, reality_r = await _gather(c, [
            f"/trending/tv/week?language={language}",
            f"/tv/popular?language={language}",
            f"/discover/tv?with_genres=18&sort_by=popularity.desc&language={language}",
            f"/discover/tv?with_genres=10765&sort_by=popularity.desc&language={language}",
            f"/discover/tv?with_genres=80&sort_by=popularity.desc&language={language}",
            f"/discover/tv?with_genres=35&sort_by=popularity.desc&language={language}",
            f"/discover/tv?with_genres=10764&sort_by=popularity.desc&language={language}",
        ])

    def extract(r, mt="tv"):
        return [_card(i, mt) for i in (r.get("results") or [])
                if (i.get("title") or i.get("name"))
                and (i.get("release_date") or i.get("first_air_date") or "9999") <= _TODAY]

    return {
        "trending": extract(trending_r),
        "rows": [
            {"label": "Popular TV Shows", "items": extract(popular_r)},
            {"label": "Drama",            "items": extract(drama_r)},
            {"label": "Sci-Fi & Fantasy", "items": extract(scifi_r)},
            {"label": "Crime",            "items": extract(crime_r)},
            {"label": "Comedy",           "items": extract(comedy_r)},
            {"label": "Reality",          "items": extract(reality_r)},
        ],
    }


async def fetch_spanish_tv_home() -> dict:
    """Telenovelas and Spanish TV home."""
    async with httpx.AsyncClient(headers=_headers(), timeout=15) as c:
        trending_r, novelas_r, drama_r, comedy_r, crime_r, reality_r = await _gather(c, [
            "/trending/tv/week?language=es-MX&region=MX",
            "/discover/tv?with_original_language=es&with_genres=10766&sort_by=popularity.desc",
            "/discover/tv?with_original_language=es&with_genres=18&sort_by=popularity.desc",
            "/discover/tv?with_original_language=es&with_genres=35&sort_by=popularity.desc",
            "/discover/tv?with_original_language=es&with_genres=80&sort_by=popularity.desc",
            "/discover/tv?with_original_language=es&with_genres=10764&sort_by=popularity.desc",
        ])

    def extract(r, mt="tv"):
        return [_card(i, mt) for i in (r.get("results") or [])
                if (i.get("title") or i.get("name"))
                and (i.get("release_date") or i.get("first_air_date") or "9999") <= _TODAY]

    return {
        "trending": extract(trending_r),
        "rows": [
            {"label": "Telenovelas",      "items": extract(novelas_r)},
            {"label": "Drama",            "items": extract(drama_r)},
            {"label": "Comedia",          "items": extract(comedy_r)},
            {"label": "Crimen",           "items": extract(crime_r)},
            {"label": "Reality",          "items": extract(reality_r)},
        ],
    }


# ─── A-Z Browse ───────────────────────────────────────────────────────────────

# Page offsets calibrated from live TMDB probes.
# Movies use vote_count.gte=400 → 457 pages total (fits in TMDB's 500-page cap).
# TV uses vote_count.gte=50 → 331 pages total.
_MOVIE_OFFSETS = {
    '#': 1,   'A': 12,  'B': 42,  'C': 72,  'D': 87,  'E': 102,
    'F': 117, 'G': 132, 'H': 147, 'I': 162, 'J': 172, 'K': 177,
    'L': 192, 'M': 208, 'N': 237, 'O': 247, 'P': 249, 'Q': 265,
    'R': 266, 'S': 282, 'T': 315, 'U': 407, 'V': 412, 'W': 416,
    'X': 426, 'Y': 429, 'Z': 432,
}
_TV_OFFSETS = {
    '#': 1,   'A': 4,   'B': 19,  'C': 38,  'D': 48,  'E': 68,
    'F': 71,  'G': 80,  'H': 88,  'I': 98,  'J': 101, 'K': 106,
    'L': 110, 'M': 128, 'N': 146, 'O': 148, 'P': 158, 'Q': 164,
    'R': 168, 'S': 180, 'T': 200, 'U': 240, 'V': 244, 'W': 246,
    'X': 254, 'Y': 256, 'Z': 257,
}
# Spanish-only catalogs — calibrated from live TMDB probes
# Movies: 149 total pages; TV: 50 total pages
_SPANISH_MOVIE_OFFSETS = {
    '#': 1,   'A': 4,   'B': 12,  'C': 16,  'D': 25,  'E': 32,
    'F': 56,  'G': 57,  'H': 60,  'I': 62,  'J': 64,  'K': 66,
    'L': 68,  'M': 96,  'N': 105, 'O': 110, 'P': 112, 'Q': 118,
    'R': 120, 'S': 122, 'T': 132, 'U': 137, 'V': 142, 'W': 144,
    'X': 145, 'Y': 145, 'Z': 148,
}
_SPANISH_TV_OFFSETS = {
    '#': 1,   'A': 2,   'B': 6,   'C': 7,   'D': 11,  'E': 13,
    'F': 19,  'G': 20,  'H': 20,  'I': 21,  'J': 22,  'K': 22,
    'L': 23,  'M': 33,  'N': 36,  'O': 37,  'P': 38,  'Q': 40,
    'R': 41,  'S': 42,  'T': 46,  'U': 47,  'V': 48,  'W': 48,
    'X': 48,  'Y': 49,  'Z': 50,
}


async def browse_by_letter(
    letter: str, page: int = 1, media_type: str = "movie",
    language: str = "en-US", spanish_only: bool = False,
) -> dict:
    """Return ~20 items whose original title starts with `letter`."""
    import asyncio
    L = letter.upper()
    path = "movie" if media_type == "movie" else "tv"
    title_field = "original_title" if media_type == "movie" else "original_name"
    if spanish_only:
        offsets = _SPANISH_MOVIE_OFFSETS if media_type == "movie" else _SPANISH_TV_OFFSETS
    else:
        offsets = _MOVIE_OFFSETS if media_type == "movie" else _TV_OFFSETS
    PER_PAGE = 20
    FETCH_CHUNK = 6  # TMDB pages fetched per browse page

    base = offsets.get(L, 1) + (page - 1) * FETCH_CHUNK

    if spanish_only:
        vc = 20
    elif media_type == "movie":
        vc = 400  # keeps total pages ≤500 (TMDB API cap)
    else:
        vc = 50
    extra = "&with_original_language=es" if spanish_only else ""
    paths = [
        f"/discover/{path}?sort_by=original_{title_field.split('_')[1]}.asc"
        f"&vote_count.gte={vc}&language={language}&page={base + i}{extra}"
        for i in range(FETCH_CHUNK + 2)  # +2 buffer to ensure we get enough
    ]

    async with httpx.AsyncClient(headers=_headers(), timeout=20) as c:
        raw = await _gather(c, paths)

    results = []
    for r in raw:
        for item in (r.get("results") or []):
            t = (item.get(title_field) or "").upper().strip()
            if not t:
                continue
            first = t[0]
            if L == '#':
                match = first.isdigit()
            else:
                match = first == L
            if match and (item.get("title") or item.get("name")):
                date = item.get("release_date") or item.get("first_air_date") or "9999"
                if date <= _TODAY:
                    results.append(_card(item, media_type))

    seen = set()
    unique = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)

    return {
        "results": unique[:PER_PAGE],
        "has_next": len(unique) > PER_PAGE,
        "page": page,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _gather(c: httpx.AsyncClient, paths: list[str]) -> list[dict]:
    import asyncio
    async def _get(path):
        try:
            sep = "&" if "?" in path else "?"
            r = await c.get(f"{BASE}{path}{sep}api_key={TMDB_API_KEY}")
            return r.json()
        except Exception:
            return {}
    return await asyncio.gather(*[_get(p) for p in paths])
