"""Stream sources — embed URLs for iframe playback (no extraction needed)."""


def movie_sources(tmdb_id: int) -> list[dict]:
    return [
        {"name": "vidsrc.to",  "url": f"https://vidsrc.to/embed/movie/{tmdb_id}"},
        {"name": "vidsrc.cc",  "url": f"https://vidsrc.cc/v2/embed/movie/{tmdb_id}"},
        {"name": "embed.su",   "url": f"https://embed.su/embed/movie/{tmdb_id}"},
        {"name": "2embed",     "url": f"https://www.2embed.cc/embed/{tmdb_id}"},
    ]


def tv_sources(tmdb_id: int, season: int, episode: int) -> list[dict]:
    return [
        {"name": "vidsrc.to",  "url": f"https://vidsrc.to/embed/tv/{tmdb_id}/{season}/{episode}"},
        {"name": "vidsrc.cc",  "url": f"https://vidsrc.cc/v2/embed/tv/{tmdb_id}?season={season}&episode={episode}"},
        {"name": "embed.su",   "url": f"https://embed.su/embed/tv/{tmdb_id}/{season}/{episode}"},
        {"name": "2embed",     "url": f"https://www.2embed.cc/embedtv/{tmdb_id}&s={season}&e={episode}"},
    ]


async def get_movie_stream(tmdb_id: int) -> dict:
    srcs = movie_sources(tmdb_id)
    return {"url": srcs[0]["url"], "type": "embed", "source": srcs[0]["name"], "sources": srcs}


async def get_tv_stream(tmdb_id: int, season: int, episode: int) -> dict:
    srcs = tv_sources(tmdb_id, season, episode)
    return {"url": srcs[0]["url"], "type": "embed", "source": srcs[0]["name"], "sources": srcs}
