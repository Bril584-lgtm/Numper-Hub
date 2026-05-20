"""AniList home data — single combined query for all homepage rows."""
import re
from datetime import date
import httpx

ANILIST_URL = "https://graphql.anilist.co"
_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def _current_season() -> tuple[str, int]:
    month = date.today().month
    year = date.today().year
    if month in (1, 2, 3): return "WINTER", year
    if month in (4, 5, 6): return "SPRING", year
    if month in (7, 8, 9): return "SUMMER", year
    return "FALL", year


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                          ("&quot;", '"'), ("&#039;", "'"), ("&nbsp;", " ")]:
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def _to_card(m: dict) -> dict:
    titles = m.get("title") or {}
    title = titles.get("english") or titles.get("romaji") or ""
    cover = m.get("coverImage") or {}
    thumb = cover.get("extraLarge") or cover.get("large") or ""
    return {
        "title": title,
        "thumb": thumb,
        "banner": m.get("bannerImage") or "",
        "synopsis": _strip_html(m.get("description") or ""),
        "genres": (m.get("genres") or [])[:5],
        "score": m.get("averageScore") or 0,
        "year": m.get("seasonYear") or 0,
        "episodes": m.get("episodes") or 0,
        "format": m.get("format") or "",
        "status": m.get("status") or "",
        "mal_id": m.get("idMal") or 0,
    }


_F = "id idMal title{romaji english}coverImage{extraLarge large}bannerImage description(asHtml:false)genres format status averageScore episodes seasonYear"

_HOME_QUERY = """
query($season:MediaSeason,$seasonYear:Int){
  trending:Page(page:1,perPage:25){media(sort:TRENDING_DESC,type:ANIME,isAdult:false){""" + _F + """}}
  seasonal:Page(page:1,perPage:20){media(sort:POPULARITY_DESC,type:ANIME,season:$season,seasonYear:$seasonYear,isAdult:false){""" + _F + """}}
  topRated:Page(page:1,perPage:20){media(sort:SCORE_DESC,type:ANIME,isAdult:false,format_in:[TV],averageScore_greater:75){""" + _F + """}}
  action:Page(page:1,perPage:20){media(genre:"Action",sort:POPULARITY_DESC,type:ANIME,isAdult:false){""" + _F + """}}
  romance:Page(page:1,perPage:20){media(genre:"Romance",sort:POPULARITY_DESC,type:ANIME,isAdult:false){""" + _F + """}}
  fantasy:Page(page:1,perPage:20){media(genre:"Fantasy",sort:POPULARITY_DESC,type:ANIME,isAdult:false){""" + _F + """}}
  comedy:Page(page:1,perPage:20){media(genre:"Comedy",sort:POPULARITY_DESC,type:ANIME,isAdult:false){""" + _F + """}}
  scifi:Page(page:1,perPage:20){media(genre:"Sci-Fi",sort:POPULARITY_DESC,type:ANIME,isAdult:false){""" + _F + """}}
}
"""

_NSFW_QUERY = """
query($season:MediaSeason,$seasonYear:Int){
  trending:Page(page:1,perPage:25){media(sort:TRENDING_DESC,type:ANIME,genre:"Ecchi",isAdult:false){""" + _F + """}}
  seasonal:Page(page:1,perPage:20){media(sort:POPULARITY_DESC,type:ANIME,genre:"Ecchi",season:$season,seasonYear:$seasonYear,isAdult:false){""" + _F + """}}
  topEcchi:Page(page:1,perPage:20){media(sort:SCORE_DESC,type:ANIME,genre:"Ecchi",isAdult:false,averageScore_greater:60){""" + _F + """}}
  adult:Page(page:1,perPage:20){media(sort:POPULARITY_DESC,type:ANIME,isAdult:true){""" + _F + """}}
  romance:Page(page:1,perPage:20){media(sort:SCORE_DESC,type:ANIME,genre:"Romance",isAdult:false,averageScore_greater:60){""" + _F + """}}
  harem:Page(page:1,perPage:20){media(genre:"Harem",sort:POPULARITY_DESC,type:ANIME,isAdult:false){""" + _F + """}}
}
"""


async def fetch_home_data(nsfw: bool = False) -> dict:
    season, year = _current_season()
    query = _NSFW_QUERY if nsfw else _HOME_QUERY
    try:
        async with httpx.AsyncClient(timeout=20, headers=_HEADERS) as client:
            r = await client.post(
                ANILIST_URL,
                json={"query": query, "variables": {"season": season, "seasonYear": year}},
            )
            data = r.json().get("data") or {}
    except Exception:
        data = {}

    def extract(key: str) -> list[dict]:
        page = data.get(key) or {}
        return [_to_card(m) for m in (page.get("media") or []) if (m.get("title") or {}).get("romaji")]

    if nsfw:
        return {
            "trending": extract("trending"),
            "rows": [
                {"label": "Ecchi This Season", "items": extract("seasonal")},
                {"label": "Top Ecchi", "items": extract("topEcchi")},
                {"label": "Adult / Explicit", "items": extract("adult")},
                {"label": "Ecchi Romance", "items": extract("romance")},
                {"label": "Harem", "items": extract("harem")},
            ],
        }

    return {
        "trending": extract("trending"),
        "rows": [
            {"label": "Popular This Season", "items": extract("seasonal")},
            {"label": "Top Rated All Time", "items": extract("topRated")},
            {"label": "Action", "items": extract("action")},
            {"label": "Romance", "items": extract("romance")},
            {"label": "Fantasy", "items": extract("fantasy")},
            {"label": "Comedy", "items": extract("comedy")},
            {"label": "Sci-Fi", "items": extract("scifi")},
        ],
    }
