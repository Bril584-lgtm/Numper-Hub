"""AllAnime source backend — mirrors ani-cli's AllAnime implementation."""
import base64
import hashlib
import json
import re
import httpx
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

BASE = "https://api.allanime.day"
REFERER = "https://allmanga.to"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
HEADERS = {"User-Agent": AGENT, "Referer": REFERER}

_AES_KEY = hashlib.sha256(b"Xot36i3lK3:v1").digest()

# Substitution table from ani-cli's provider_init sed chain
_SUB = {
    "79": "A", "7a": "B", "7b": "C", "7c": "D", "7d": "E", "7e": "F", "7f": "G",
    "70": "H", "71": "I", "72": "J", "73": "K", "74": "L", "75": "M", "76": "N", "77": "O",
    "68": "P", "69": "Q", "6a": "R", "6b": "S", "6c": "T", "6d": "U", "6e": "V", "6f": "W",
    "60": "X", "61": "Y", "62": "Z",
    "59": "a", "5a": "b", "5b": "c", "5c": "d", "5d": "e", "5e": "f", "5f": "g",
    "50": "h", "51": "i", "52": "j", "53": "k", "54": "l", "55": "m", "56": "n", "57": "o",
    "48": "p", "49": "q", "4a": "r", "4b": "s", "4c": "t", "4d": "u", "4e": "v", "4f": "w",
    "40": "x", "41": "y", "42": "z",
    "08": "0", "09": "1", "0a": "2", "0b": "3", "0c": "4", "0d": "5", "0e": "6", "0f": "7",
    "00": "8", "01": "9",
    "15": "-", "16": ".", "67": "_", "46": "~",
    "02": ":", "17": "/", "07": "?", "1b": "#",
    "63": "[", "65": "]", "78": "@",
    "19": "!", "1c": "$", "1e": "&",
    "10": "(", "11": ")", "12": "*", "13": "+", "14": ",",
    "03": ";", "05": "=", "1d": "%",
}

SEARCH_GQL = (
    "query($search:SearchInput $limit:Int $page:Int $translationType:VaildTranslationTypeEnumType"
    " $countryOrigin:VaildCountryOriginEnumType){"
    "shows(search:$search limit:$limit page:$page translationType:$translationType"
    " countryOrigin:$countryOrigin){edges{_id name availableEpisodes thumbnail thumbnails __typename}}}"
)

EPISODE_GQL = (
    "query($showId:String! $translationType:VaildTranslationTypeEnumType! $episodeString:String!){"
    "episode(showId:$showId translationType:$translationType episodeString:$episodeString)"
    "{episodeString sourceUrls}}"
)

EPISODE_QUERY_HASH = "d405d0edd690624b66baba3068e0edc3ac90f1597d898a1ec8db4e5c43c00fec"


def _decode_hex_url(hex_str: str) -> str:
    """Decode a hex-encoded URL using the AllAnime substitution cipher."""
    chunks = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
    return "".join(_SUB.get(c, c) for c in chunks).replace("/clock", "/clock.json")


def _decrypt_tobeparsed(blob: str) -> list[dict]:
    """Decrypt a tobeparsed blob → list of {name, url} source dicts."""
    try:
        raw = base64.b64decode(blob + "==")
        iv = raw[1:13]
        ct = raw[13:len(raw) - 16]
        ctr_iv = iv + b"\x00\x00\x00\x02"
        cipher = Cipher(algorithms.AES(_AES_KEY), modes.CTR(ctr_iv), backend=default_backend())
        dec = cipher.decryptor()
        plain = (dec.update(ct) + dec.finalize()).decode("utf-8", errors="ignore")
    except Exception:
        return []

    # New format: sourceUrls contain direct embed URLs (not --hex encoded)
    # Try JSON parse first
    try:
        data = json.loads(plain)
        source_urls = (
            data.get("episode", {}).get("sourceUrls", [])
            or data.get("sourceUrls", [])
        )
        sources = []
        for s in source_urls:
            url = s.get("sourceUrl", "")
            name = s.get("sourceName", "unknown")
            stype = s.get("stype", "")
            if url:
                # Old hex-encoded format still used by some providers
                if url.startswith("--"):
                    url = _decode_hex_url(url[2:])
                sources.append({"name": name, "url": url, "stype": stype})
        return sources
    except json.JSONDecodeError:
        pass

    # Fallback: regex parse for old hex-encoded --url format
    sources = []
    for chunk in plain.replace("{", "\n").replace("}", "\n").split("\n"):
        m = re.search(r'"sourceUrl":"--([^"]+)".*?"sourceName":"([^"]+)"', chunk)
        if not m:
            m = re.search(r'"sourceName":"([^"]+)".*?"sourceUrl":"--([^"]+)"', chunk)
            if m:
                name, hex_url = m.group(1), m.group(2)
            else:
                continue
        else:
            hex_url, name = m.group(1), m.group(2)
        sources.append({"name": name, "url": _decode_hex_url(hex_url), "stype": ""})
    return sources


_ANILIST_GQL = """
query ($search: String) {
  Page(page: 1, perPage: 50) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      title { romaji english native }
      coverImage { extraLarge large }
      genres format status averageScore seasonYear idMal
    }
  }
}
"""


def _words(t: str) -> set[str]:
    """Lowercase words, strip punctuation, ignore 1-char tokens."""
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", t.lower()).split() if len(w) > 1}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


async def _enrich_anilist_covers(results: list[dict], query: str = "") -> None:
    """Enrich results with AniList cover art, genres, format, status, score (in-place)."""
    if not results:
        return
    search_term = query or results[0]["title"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://graphql.anilist.co",
                json={"query": _ANILIST_GQL, "variables": {"search": search_term}},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            page = (resp.json().get("data") or {}).get("Page") or {}
            media_list = page.get("media") or []

        # Build lookup: all title variants → (words_set, media)
        candidates: list[tuple[set, dict]] = []
        for m in media_list:
            titles = m.get("title") or {}
            title_words: set[str] = set()
            for t in [titles.get("romaji"), titles.get("english"), titles.get("native")]:
                if t:
                    title_words |= _words(t)
            if title_words:
                candidates.append((title_words, m))

        for r in results:
            key_words = _words(r["title"])
            if not key_words:
                continue

            best_score = 0.0
            best_media = None
            for cand_words, m in candidates:
                score = _jaccard(key_words, cand_words)
                if score > best_score:
                    best_score = score
                    best_media = m

            # Require at least 40% word overlap to avoid false matches
            if best_score < 0.4 or best_media is None:
                continue

            cover = best_media.get("coverImage") or {}
            img = cover.get("extraLarge") or cover.get("large")
            if img:
                r["thumb"] = img
            r["genres"] = best_media.get("genres") or []
            r["format"] = best_media.get("format") or ""
            r["status"] = best_media.get("status") or ""
            r["score"] = best_media.get("averageScore") or 0
            r["year"] = best_media.get("seasonYear") or 0
            r["mal_id"] = best_media.get("idMal") or 0
    except Exception:
        pass  # keep AllAnime data if AniList is down


async def search(query: str, dub: bool = False, nsfw: bool = False) -> list[dict]:
    mode = "dub" if dub else "sub"
    variables = {
        "search": {"allowAdult": nsfw, "allowUnknown": False, "query": query},
        "limit": 40,
        "page": 1,
        "translationType": mode,
        "countryOrigin": "ALL",
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        r = await client.post(
            f"{BASE}/api",
            json={"variables": variables, "query": SEARCH_GQL},
        )
        data = r.json()

    results = []
    for edge in data.get("data", {}).get("shows", {}).get("edges", []):
        ep_count = edge.get("availableEpisodes", {}).get(mode, 0)
        if ep_count:
            thumb = edge.get("thumbnail", "")
            results.append({
                "id": edge["_id"],
                "title": edge["name"],
                "episodes": ep_count,
                "thumb": thumb,
                "source": "allanime",
            })

    await _enrich_anilist_covers(results, query)
    return results


async def get_episode_sources(show_id: str, ep: str, dub: bool = False) -> list[dict]:
    """Return list of {name, clock_url} for a given episode."""
    mode = "dub" if dub else "sub"

    import urllib.parse
    variables = json.dumps({"showId": show_id, "translationType": mode, "episodeString": ep})
    extensions = json.dumps({"persistedQuery": {"version": 1, "sha256Hash": EPISODE_QUERY_HASH}})

    async with httpx.AsyncClient(timeout=15) as client:
        # Try persisted query first
        r = await client.get(
            f"{BASE}/api",
            params={"variables": variables, "extensions": extensions},
            headers={**HEADERS, "Origin": "https://youtu-chan.com", "Referer": "https://youtu-chan.com"},
        )
        resp_text = r.text

        if "tobeparsed" not in resp_text:
            # Fallback to POST
            r = await client.post(
                f"{BASE}/api",
                json={"variables": {"showId": show_id, "translationType": mode, "episodeString": ep},
                      "query": EPISODE_GQL},
                headers=HEADERS,
            )
            resp_text = r.text

    data = {}
    try:
        data = r.json()
    except Exception:
        pass

    blob_match = re.search(r'"tobeparsed":"([^"]+)"', resp_text)
    if blob_match:
        return _decrypt_tobeparsed(blob_match.group(1))

    # Parse sourceUrls directly (non-encrypted fallback)
    sources = []
    try:
        parsed = r.json()
        source_urls = (
            parsed.get("data", {}).get("episode", {}).get("sourceUrls", [])
            or parsed.get("episode", {}).get("sourceUrls", [])
        )
        for s in source_urls:
            url = s.get("sourceUrl", "")
            name = s.get("sourceName", "unknown")
            stype = s.get("stype", "")
            if url:
                if url.startswith("--"):
                    url = _decode_hex_url(url[2:])
                sources.append({"name": name, "url": url, "stype": stype})
        return sources
    except Exception:
        pass

    for chunk in resp_text.replace("{", "\n").replace("}", "\n").split("\n"):
        m = re.search(r'"sourceUrl":"([^"]+)".*?"sourceName":"([^"]+)"', chunk)
        if m:
            url = m.group(1).replace("\\u002F", "/").replace("\\", "")
            name = m.group(2)
            if url.startswith("--"):
                url = _decode_hex_url(url[2:])
            sources.append({"name": name, "url": url, "stype": ""})
    return sources


async def resolve_clock(clock_path: str) -> str | None:
    """Fetch a clock.json URL and extract the direct stream URL."""
    if not clock_path.startswith("http"):
        url = f"https://allanime.day{clock_path}"
    else:
        url = clock_path
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        try:
            r = await client.get(url)
            data = r.json()
            # Wixmp / default format
            links = data.get("links", [])
            if links:
                return links[0].get("link") or links[0].get("hls")
            # mp4 format
            if data.get("mp4"):
                return None  # broken mp4 endpoint
        except Exception:
            pass
    return None
