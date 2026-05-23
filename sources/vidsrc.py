"""Stream extraction — race all embed sources via Playwright for fastest result."""
import asyncio
from .playwright_extractor import extract_stream

_SOURCES = {
    # ── Tier 1: confirmed working, fast CDNs ──────────────────────────────────
    "vidlink": {
        "movie": lambda i: f"https://vidlink.pro/movie/{i}",
        "tv": lambda i, s, e: f"https://vidlink.pro/tv/{i}/{s}/{e}",
        "target": "vodvidl",
        "referer": "https://vidlink.pro/",
        "origin": "https://vidlink.pro",
    },
    "vidsrc.cc": {
        "movie": lambda i: f"https://vidsrc.cc/v2/embed/movie/{i}",
        "tv": lambda i, s, e: f"https://vidsrc.cc/v2/embed/tv/{i}?season={s}&episode={e}",
        "target": "speedsterwave",
        "referer": "https://player.videasy.net/",
        "origin": "https://player.videasy.net",
    },
    # ── Tier 2: generally reliable ────────────────────────────────────────────
    "vidsrc.to": {
        "movie": lambda i: f"https://vidsrc.to/embed/movie/{i}",
        "tv": lambda i, s, e: f"https://vidsrc.to/embed/tv/{i}/{s}/{e}",
        "target": "",
        "referer": "https://vidsrc.to/",
        "origin": "https://vidsrc.to",
    },
    "embed.su": {
        "movie": lambda i: f"https://embed.su/embed/movie/{i}",
        "tv": lambda i, s, e: f"https://embed.su/embed/tv/{i}/{s}/{e}",
        "target": "",
        "referer": "https://embed.su/",
        "origin": "https://embed.su",
    },
    "vidsrc.xyz": {
        "movie": lambda i: f"https://vidsrc.xyz/embed/movie?tmdb={i}",
        "tv": lambda i, s, e: f"https://vidsrc.xyz/embed/tv?tmdb={i}&season={s}&episode={e}",
        "target": "",
        "referer": "https://vidsrc.xyz/",
        "origin": "https://vidsrc.xyz",
    },
    "autoembed": {
        "movie": lambda i: f"https://autoembed.co/movie/tmdb/{i}",
        "tv": lambda i, s, e: f"https://autoembed.co/tv/tmdb/{i}-{s}-{e}",
        "target": "",
        "referer": "https://autoembed.co/",
        "origin": "https://autoembed.co",
    },
    # ── Tier 3: hit-or-miss ───────────────────────────────────────────────────
    "vidsrc.icu": {
        "movie": lambda i: f"https://vidsrc.icu/embed/movie/{i}",
        "tv": lambda i, s, e: f"https://vidsrc.icu/embed/tv/{i}/{s}/{e}",
        "target": "",
        "referer": "https://vidsrc.icu/",
        "origin": "https://vidsrc.icu",
    },
    "2embed": {
        "movie": lambda i: f"https://www.2embed.skin/movie/{i}",
        "tv": lambda i, s, e: f"https://www.2embed.skin/tv/{i}/{s}/{e}",
        "target": "vodvidl",
        "referer": "https://www.2embed.skin/",
        "origin": "https://www.2embed.skin",
    },
    "moviesapi": {
        "movie": lambda i: f"https://moviesapi.club/movie/{i}",
        "tv": lambda i, s, e: f"https://moviesapi.club/tv/{i}-{s}-{e}",
        "target": "",
        "referer": "https://moviesapi.club/",
        "origin": "https://moviesapi.club",
    },
    "vidsrc.me": {
        "movie": lambda i: f"https://vidsrc.me/embed/movie?tmdb={i}",
        "tv": lambda i, s, e: f"https://vidsrc.me/embed/tv?tmdb={i}&season={s}&episode={e}",
        "target": "",
        "referer": "https://vidsrc.me/",
        "origin": "https://vidsrc.me",
    },
    "superembed": {
        "movie": lambda i: f"https://multiembed.mov/directstream.php?video_id={i}&tmdb=1",
        "tv": lambda i, s, e: f"https://multiembed.mov/directstream.php?video_id={i}&tmdb=1&s={s}&e={e}",
        "target": "",
        "referer": "https://multiembed.mov/",
        "origin": "https://multiembed.mov",
    },
}

# Priority: T1 proven → T2 reliable → T3 fallbacks
_PRIORITY = [
    "vidlink", "vidsrc.cc",                          # T1 — confirmed fast
    "vidsrc.to", "embed.su", "vidsrc.xyz", "autoembed",  # T2 — reliable
    "vidsrc.icu", "2embed", "moviesapi", "vidsrc.me", "superembed",  # T3 — fallback
]


async def _try_source(name: str, embed_url: str, cfg: dict) -> dict | None:
    try:
        stream = await extract_stream(embed_url, target_domain=cfg["target"])
        if stream:
            return {
                "url": stream,
                "type": "hls" if ".m3u8" in stream else "mp4",
                "source": name,
                "referer": cfg["referer"],
                "origin": cfg["origin"],
            }
    except Exception:
        pass
    return None


async def _race(embeds: list[tuple]) -> dict:
    """Launch all sources concurrently, return the first working stream."""
    tasks = {asyncio.create_task(_try_source(name, url, cfg)): name for name, url, cfg in embeds}
    pending = set(tasks.keys())
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                result = task.result()
            except Exception:
                result = None
            if result:
                for t in pending:
                    t.cancel()
                print(f"[vidsrc] winner: {result['source']} url={result['url'][:60]}")
                return result
    return {"error": "All sources exhausted — no stream found"}


async def get_movie_stream(tmdb_id: int, source: str = "auto") -> dict:
    if source != "auto" and source in _SOURCES:
        cfg = _SOURCES[source]
        result = await _try_source(source, cfg["movie"](tmdb_id), cfg)
        return result or {"error": f"Source {source} returned no stream"}
    embeds = [(name, _SOURCES[name]["movie"](tmdb_id), _SOURCES[name]) for name in _PRIORITY]
    return await _race(embeds)


async def get_tv_stream(tmdb_id: int, season: int, episode: int, source: str = "auto") -> dict:
    if source != "auto" and source in _SOURCES:
        cfg = _SOURCES[source]
        result = await _try_source(source, cfg["tv"](tmdb_id, season, episode), cfg)
        return result or {"error": f"Source {source} returned no stream"}
    embeds = [(name, _SOURCES[name]["tv"](tmdb_id, season, episode), _SOURCES[name]) for name in _PRIORITY]
    return await _race(embeds)
