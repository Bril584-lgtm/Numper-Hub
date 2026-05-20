"""Source router — AllAnime primary, GogoAnime + AnimePahe independent fallbacks."""
import asyncio
import urllib.parse
import httpx
from . import allanime, hianime, gogoanime, playwright_extractor, animepahe

_ANILIST_CORRECT_GQL = "query($s:String){Page(page:1,perPage:1){media(search:$s,type:ANIME,sort:SEARCH_MATCH){title{romaji english}}}}"


async def _anilist_correct(query: str) -> str:
    """Return AniList's best-guess title for a potentially misspelled query."""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post("https://graphql.anilist.co",
                json={"query": _ANILIST_CORRECT_GQL, "variables": {"s": query}},
                headers={"Content-Type": "application/json"})
            media = r.json().get("data", {}).get("Page", {}).get("media", [])
            if media:
                t = media[0].get("title") or {}
                return t.get("english") or t.get("romaji") or ""
    except Exception:
        pass
    return ""


def _merge(*buckets) -> list[dict]:
    seen, out = set(), []
    for bucket in buckets:
        for r in (bucket if not isinstance(bucket, Exception) else []):
            key = r["title"].lower().strip()
            if key not in seen:
                seen.add(key)
                out.append(r)
    return out


async def search_all(query: str, dub: bool = False, nsfw: bool = False) -> list[dict]:
    results_aa, results_hi, results_gogo, results_pahe = await asyncio.gather(
        allanime.search(query, dub=dub, nsfw=nsfw),
        hianime.search(query, dub=dub),
        gogoanime.search(query, dub=dub),
        animepahe.search(query, dub=dub),
        return_exceptions=True,
    )
    merged = _merge(results_aa, results_hi, results_gogo, results_pahe)

    # Fuzzy fallback: if few results, ask AniList for corrected title and retry
    if len(merged) < 3:
        corrected = await _anilist_correct(query)
        if corrected and corrected.lower() != query.lower():
            extra = await allanime.search(corrected, dub=dub, nsfw=nsfw)
            if not isinstance(extra, Exception):
                seen = {r["title"].lower() for r in merged}
                for r in extra:
                    if r["title"].lower() not in seen:
                        merged.append(r)
    return merged


async def get_episode_count(source: str, show_id: str) -> int:
    if source == "gogoanime":
        return await gogoanime.get_episode_count(show_id)
    if source == "animepahe":
        return await animepahe.get_episode_count(show_id)
    return 0


async def get_stream(source: str, show_id: str, ep: int, dub: bool = False) -> dict:
    """
    Return {"url": "...", "type": "hls"|"mp4", "source": "..."} or {"error": "..."}.
    Tries multiple providers within the source with auto-fallback.
    """
    if source == "allanime":
        return await _resolve_allanime(show_id, str(ep), dub)
    elif source == "gogoanime":
        return await gogoanime.get_stream(show_id, ep, dub=dub)
    elif source == "hianime":
        return await _resolve_hianime(show_id, ep, dub)
    elif source == "animepahe":
        return await animepahe.get_stream(show_id, ep, dub=dub)
    return {"error": "Unknown source"}


_CLOCK_PREFIXES = ("/apivtwo/", "/clock", "allanime.day/")
_DIRECT_STREAM = (".m3u8", ".mp4", "cdnfile", "cdn.plyr", "storage.googleapis")
_PROXY_DIRECT = ("fast4speed",)  # direct MP4 URLs that need the proxy for CORS


def _is_clock_url(url: str) -> bool:
    return any(p in url for p in _CLOCK_PREFIXES)


def _is_direct_stream(url: str) -> bool:
    return any(p in url for p in _DIRECT_STREAM)


async def _resolve_allanime(show_id: str, ep: str, dub: bool) -> dict:
    try:
        sources = await allanime.get_episode_sources(show_id, ep, dub=dub)
    except Exception as e:
        return {"error": f"AllAnime fetch failed: {e}"}

    if not sources:
        return {"error": "No sources found on AllAnime"}

    # Priority: proven reliable sources first; Luf-Mp4 deprioritised (HiAnime CDN offline)
    priority = ["Default", "S-mp4", "Fm-Hls", "Vid-mp4", "Yt-mp4", "Ok", "Sw", "Vg", "Mp4", "Luf-Mp4"]

    def source_rank(s):
        try:
            return priority.index(s["name"])
        except ValueError:
            return 99

    sources.sort(key=source_rank)

    for src in sources:
        url = src.get("url", "")
        name = src.get("name", "unknown")
        if not url:
            continue

        # fast4speed and similar: direct MP4, needs proxy for CORS
        if any(p in url for p in _PROXY_DIRECT):
            return {"url": f"/api/proxy?url={urllib.parse.quote(url, safe='')}", "type": "mp4", "source": f"allanime:{name}"}

        # If it's already a direct stream, serve it
        if _is_direct_stream(url):
            stream_type = "hls" if ".m3u8" in url else "mp4"
            return {"url": url, "type": stream_type, "source": f"allanime:{name}"}

        # If it's a clock.json path, resolve via API
        if _is_clock_url(url):
            direct = await allanime.resolve_clock(url)
            if direct:
                stream_type = "hls" if ".m3u8" in direct else "mp4"
                return {"url": direct, "type": stream_type, "source": f"allanime:{name}"}
            # clock failed → try Playwright on it
            try:
                stream = await playwright_extractor.extract_from_allanime_source(url)
                if stream:
                    stream_type = "hls" if ".m3u8" in stream else "mp4"
                    return {"url": stream, "type": stream_type, "source": f"allanime:{name} (pw)"}
            except Exception:
                continue
        else:
            # Embed URL (iframe): use Playwright to extract stream
            try:
                stream = await playwright_extractor.extract_stream(url)
                if stream:
                    stream_type = "hls" if ".m3u8" in stream else "mp4"
                    return {"url": stream, "type": stream_type, "source": f"allanime:{name} (pw)"}
            except Exception:
                continue

    return {"error": "All AllAnime sources failed"}


async def _resolve_hianime(show_slug: str, ep_num: int, dub: bool) -> dict:
    try:
        ep_id = await hianime.get_episode_id(show_slug, ep_num)
        if not ep_id:
            return {"error": "Episode not found on HiAnime"}
        url = await hianime.get_stream_url(ep_id, dub=dub)
        if url:
            stream_type = "hls" if ".m3u8" in url else "mp4"
            return {"url": url, "type": stream_type, "source": "hianime"}
    except Exception as e:
        return {"error": f"HiAnime failed: {e}"}
    return {"error": "HiAnime: no stream found"}
