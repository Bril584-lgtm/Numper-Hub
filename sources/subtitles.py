"""Subtitle fetcher — Jimaku.cc (anime-specific, no API key required)."""
import httpx

JIMAKU = "https://jimaku.cc/api"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
_HEADERS = {"User-Agent": AGENT, "Accept": "application/json"}
_SUB_EXTS = (".srt", ".vtt", ".ass", ".ssa")


async def fetch(title: str, ep: int) -> list[dict]:
    """Return list of {name, url} subtitle files for an episode. Empty list on any failure."""
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10, follow_redirects=True) as client:
            # 1. Search for the anime entry
            r = await client.get(f"{JIMAKU}/entries/search", params={"query": title})
            entries = r.json() if r.status_code == 200 else []
            if not entries:
                return []

            # Pick best matching entry (first result from Jimaku's ranked search)
            entry = entries[0]
            entry_id = entry.get("anilist_id") or entry.get("id")
            if not entry_id:
                return []

            # 2. Get files for this specific episode
            r2 = await client.get(
                f"{JIMAKU}/entries/{entry_id}/files",
                params={"episode": ep},
            )
            files = r2.json() if r2.status_code == 200 else []

        result = []
        for f in files if isinstance(files, list) else []:
            name = f.get("name", "")
            url = f.get("url", "")
            if url and any(name.lower().endswith(ext) for ext in _SUB_EXTS):
                result.append({"name": name, "url": url})
        return result
    except Exception:
        return []
