"""vidsrc streaming — extracts m3u8/mp4 from vidsrc.to embeds via Playwright."""
from .playwright_extractor import extract_stream

VIDSRC = "https://vidsrc.to/embed"
VIDSRC2 = "https://vidsrc.me/embed"
EMBED_SU = "https://embed.su/embed"


def _movie_urls(tmdb_id: int) -> list[tuple[str, str]]:
    return [
        (f"{VIDSRC}/movie/{tmdb_id}", "vidsrc.to"),
        (f"{VIDSRC2}/movie?tmdb={tmdb_id}", "vidsrc.me"),
        (f"{EMBED_SU}/movie/{tmdb_id}", "embed.su"),
    ]


def _tv_urls(tmdb_id: int, season: int, episode: int) -> list[tuple[str, str]]:
    return [
        (f"{VIDSRC}/tv/{tmdb_id}/{season}/{episode}", "vidsrc.to"),
        (f"{VIDSRC2}/tv?tmdb={tmdb_id}&season={season}&episode={episode}", "vidsrc.me"),
        (f"{EMBED_SU}/tv/{tmdb_id}/{season}/{episode}", "embed.su"),
    ]


async def get_movie_stream(tmdb_id: int) -> dict:
    for url, name in _movie_urls(tmdb_id):
        try:
            stream = await extract_stream(url)
            if stream:
                return {"url": stream, "type": "hls" if ".m3u8" in stream else "mp4", "source": name}
        except Exception:
            continue
    return {"error": "No stream found for this movie"}


async def get_tv_stream(tmdb_id: int, season: int, episode: int) -> dict:
    for url, name in _tv_urls(tmdb_id, season, episode):
        try:
            stream = await extract_stream(url)
            if stream:
                return {"url": stream, "type": "hls" if ".m3u8" in stream else "mp4", "source": name}
        except Exception:
            continue
    return {"error": "No stream found for this episode"}
