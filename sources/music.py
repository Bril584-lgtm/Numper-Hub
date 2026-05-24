"""Music streaming via JioSaavn unofficial API — full tracks, no key needed."""
import asyncio
import httpx

BASE = "https://jiosavan-api2.vercel.app/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "application/json",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _best_image(images: list) -> str:
    if not images:
        return ""
    for img in reversed(images):
        url = img.get("url") or img.get("link") or ""
        if url:
            return url.replace("150x150", "500x500").replace("50x50", "500x500")
    return ""

def _best_url(download_urls: list) -> str:
    """Always pick highest available quality. JioSaavn tops at 320kbps AAC."""
    if not download_urls:
        return ""
    for quality in ["320kbps", "160kbps", "96kbps", "48kbps", "12kbps"]:
        for d in download_urls:
            if d.get("quality") == quality and d.get("url"):
                return d["url"]
    # fallback: last entry (usually highest)
    return download_urls[-1].get("url") or ""

def _primary_artist(song: dict) -> str:
    artists = song.get("artists") or {}
    if isinstance(artists, dict):
        primary = artists.get("primary") or []
        if primary and isinstance(primary, list):
            return ", ".join(a.get("name", "") for a in primary if a.get("name"))
    return song.get("primaryArtists") or song.get("artist") or ""

def _primary_artist_id(song: dict) -> str:
    artists = song.get("artists") or {}
    if isinstance(artists, dict):
        primary = artists.get("primary") or []
        if primary and isinstance(primary, list):
            return str(primary[0].get("id", ""))
    return ""

def _card(song: dict) -> dict:
    album = song.get("album") or {}
    return {
        "id":       song.get("id", ""),
        "title":    song.get("name", "") or song.get("title", ""),
        "artist":   _primary_artist(song),
        "artistId": _primary_artist_id(song),
        "album":    album.get("name", "") if isinstance(album, dict) else str(album),
        "albumId":  album.get("id", "")  if isinstance(album, dict) else "",
        "year":     str(song.get("year", "") or ""),
        "duration": int(song.get("duration") or 0),
        "thumb":    _best_image(song.get("image", [])),
        "url":      _best_url(song.get("downloadUrl", [])),
        "language": song.get("language", ""),
    }


# ── Search ────────────────────────────────────────────────────────────────────

async def search(query: str, limit: int = 20) -> list[dict]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.get(f"{BASE}/search/songs", params={"query": query, "limit": limit})
    data = r.json()
    songs = (data.get("data") or {}).get("results") or []
    return [_card(s) for s in songs if s.get("id")]


# ── Single song (stream URL on demand) ───────────────────────────────────────

async def get_song(song_id: str) -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.get(f"{BASE}/songs", params={"ids": song_id})
    data = r.json()
    songs = data.get("data") or []
    return _card(songs[0]) if songs else {}


# ── Album ─────────────────────────────────────────────────────────────────────

async def get_album(album_id: str) -> dict:
    """Return album metadata + full ordered tracklist."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as c:
        r = await c.get(f"{BASE}/albums", params={"id": album_id})
    data = r.json()
    album = data.get("data") or {}
    if not album:
        return {}

    artists_raw = album.get("artists") or {}
    primary = artists_raw.get("primary") or [] if isinstance(artists_raw, dict) else []
    artist_str = ", ".join(a.get("name", "") for a in primary if a.get("name"))
    artist_id   = str(primary[0].get("id", "")) if primary else ""

    songs = album.get("songs") or []
    return {
        "id":        album.get("id", ""),
        "name":      album.get("name", ""),
        "artist":    artist_str,
        "artistId":  artist_id,
        "year":      str(album.get("year", "") or ""),
        "thumb":     _best_image(album.get("image", [])),
        "songCount": len(songs),
        "tracks":    [_card(s) for s in songs if s.get("id")],
    }


# ── Artist songs (deduped) ────────────────────────────────────────────────────

async def get_artist_songs(artist_id: str, pages: int = 8) -> dict:
    """
    Fetch up to `pages` pages of an artist's songs in parallel (10 per page),
    deduplicate by normalised title, and strip non-original versions.
    Returns up to 50 unique original tracks sorted by popularity.
    """
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as c:
        tasks = [
            c.get(f"{BASE}/artists/{artist_id}/songs",
                  params={"page": p, "sortBy": "popularity", "sortOrder": "desc"})
            for p in range(pages)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    seen: set[str] = set()
    unique: list[dict] = []
    for resp in responses:
        if isinstance(resp, Exception):
            continue
        try:
            songs = (resp.json().get("data") or {}).get("songs") or []
            for s in songs:
                if not s.get("id") or not _is_original(s):
                    continue
                tk = _title_key(s)
                if tk not in seen:
                    seen.add(tk)
                    unique.append(s)
        except Exception:
            pass

    # Also grab the artist name / image from any successful response
    artist_name = ""
    artist_thumb = ""
    for resp in responses:
        if isinstance(resp, Exception):
            continue
        try:
            d = resp.json().get("data") or {}
            if d.get("name"):
                artist_name  = d["name"]
                artist_thumb = _best_image(d.get("image") or [])
                break
        except Exception:
            pass

    return {
        "name":   artist_name,
        "thumb":  artist_thumb,
        "total":  len(unique),
        "tracks": [_card(s) for s in unique[:50]],
    }


# ── Home ──────────────────────────────────────────────────────────────────────

# Only these languages appear on the front page; search is unrestricted
_HOME_LANGUAGES = {"english", "spanish"}

import re as _re
import unicodedata as _ud

# Substrings that flag a non-original/junk version — checked on lowercased title
_SKIP_PHRASES = [
    "karaoke", "instrumental", "slowed", "reverb", "sped up",
    "tribute", "orchestral", "cover version", "cover)", " cover ",
    "cover:", "made famous", "originally performed", "bootleg", "lofi version",
    "ultra slowed", "nightcore",
    "live from", "live at", "live in", "(live", "live version", "en vivo",
    "remix)", "rmix", "(edit", "hypertechno", "workout mix",
    "fitness version", "acoustic version", "acoustic)", "re-recorded",
    "remastered version", "dance mix", "stretch mix", "8d audio", "8d tunes",
    "restrung", "stripped)", "sampler",
]

def _is_original(song: dict) -> bool:
    name = (song.get("name") or "").lower()
    return not any(phrase in name for phrase in _SKIP_PHRASES)

def _title_key(song: dict) -> str:
    """Normalise title so all versions of the same song share one key.
    'Bohemian Rhapsody (Remastered)' == 'Bohemian Rhapsody'
    'Yeah! (feat. Lil Jon)' == 'Yeah! Usher featuring Lil Jon' == 'Yeah!'
    'Numb / Encore' → 'Numb'
    'Hawái' == 'Hawai'  (accent-normalised)
    """
    name = (song.get("name") or "")
    # Decompose accented characters → base letters (é→e, í→i, etc.)
    name = _ud.normalize("NFD", name)
    name = "".join(ch for ch in name if _ud.category(ch) != "Mn").lower()
    name = _re.sub(r'\s*[\(\[].*', '', name)                          # strip (…) […]
    name = _re.sub(r'\s*\b(feat\.|ft\.|featuring)\b.*', '', name)     # strip featuring X
    name = _re.sub(r'\s*/\s.*', '', name)                             # strip / Medley
    return "".join(ch for ch in name if ch.isalnum())

# Max songs from the same primary artist per row (prevents one artist flooding a section)
_MAX_PER_ARTIST = 2

# Each row has multiple distinct queries targeting different artists/subgenres
# so results stay unique and varied after global deduplication.
_ROWS = [
    ("🔥 Trending Now", [
        "Espresso Sabrina Carpenter",
        "APT Bruno Mars Rose",
        "Die With A Smile Bruno Mars Lady Gaga",
        "luther Kendrick Lamar SZA",
        "Not Like Us Kendrick Lamar",
        "Good Luck Babe Chappell Roan",
        "Please Please Please Sabrina Carpenter",
        "Birds Of A Feather Billie Eilish",
        "Taste Sabrina Carpenter",
        "Obsessed Olivia Rodrigo",
    ]),
    ("🎵 Pop", [
        "Anti Hero Taylor Swift",
        "Vampire Olivia Rodrigo",
        "As It Was Harry Styles",
        "Levitating Dua Lipa",
        "Watermelon Sugar Harry Styles",
        "bad guy Billie Eilish",
        "Shake It Off Taylor Swift",
        "Positions Ariana Grande",
        "Style Taylor Swift",
        "Break My Heart Dua Lipa",
    ]),
    ("🎤 Hip-Hop", [
        "Gods Plan Drake",
        "HUMBLE Kendrick Lamar",
        "Rockstar Post Malone",
        "SICKO MODE Travis Scott",
        "Lucid Dreams Juice WRLD",
        "Congratulations Post Malone",
        "One Dance Drake",
        "The Box Roddy Ricch",
        "Sunflower Post Malone Swae Lee",
        "Industry Baby Lil Nas X",
    ]),
    ("💿 R&B", [
        "Blinding Lights The Weeknd",
        "Good Days SZA",
        "Kill Bill SZA",
        "Starboy The Weeknd",
        "Lust For Life Lana Del Rey",
        "Location Khalid",
        "Young Dumb Broke Khalid",
        "Need To Know Doja Cat",
        "Say So Doja Cat",
        "Golden Harry Styles",
    ]),
    ("🎸 Rock", [
        "Radioactive Imagine Dragons",
        "Yellow Coldplay",
        "Numb Linkin Park",
        "Stressed Out Twenty One Pilots",
        "Mr Brightside The Killers",
        "Do I Wanna Know Arctic Monkeys",
        "Enemy Imagine Dragons",
        "Welcome To The Black Parade My Chemical Romance",
        "Smells Like Teen Spirit Nirvana",
        "Seven Nation Army The White Stripes",
    ]),
    ("🌙 Chill / Lo-fi", [
        "Heather Conan Gray",
        "Loving Is Easy Rex Orange County",
        "cardigan Taylor Swift",
        "Afterglow Ed Sheeran",
        "Sunset Lover Petit Biscuit",
        "exile Taylor Swift Bon Iver",
        "Falling Harry Styles",
        "Ribs Lorde",
        "Skinny Love Bon Iver",
        "Motion Sickness Phoebe Bridgers",
    ]),
    ("💃 Latin", [
        "Dakiti Bad Bunny Jhay Cortez",
        "BICHOTA Karol G",
        "Mi Gente J Balvin",
        "Waka Waka Shakira",
        "Pepas Farruko",
        "Hawai Maluma",
        "Baila Baila Baila Ozuna",
        "Con Calma Daddy Yankee",
        "X Nicky Jam J Balvin",
        "Despacito Luis Fonsi",
    ]),
    ("🎹 Electronic", [
        "Summer Calvin Harris",
        "Faded Alan Walker",
        "Happier Marshmello Bastille",
        "Titanium David Guetta Sia",
        "Clarity Zedd Foxes",
        "Lean On Major Lazer",
        "Scared To Be Lonely Martin Garrix Dua Lipa",
        "Stay With Me Kygo",
        "Rather Be Clean Bandit",
        "One More Time Daft Punk",
    ]),
    ("🎬 Movie & TV Hits", [
        "Hooked On A Feeling Blue Swede",
        "Bohemian Rhapsody Queen",
        "City Of Stars La La Land",
        "Running Up That Hill Kate Bush",
        "A Million Dreams Greatest Showman",
        "Shallow Lady Gaga Bradley Cooper",
        "Eye Of The Tiger Survivor",
        "Let It Go Frozen Idina Menzel",
        "Circle Of Life Lion King",
        "Jai Ho Slumdog Millionaire",
    ]),
]


async def get_home() -> dict:
    async with httpx.AsyncClient(headers=HEADERS, timeout=25) as c:

        async def _fetch_row(label: str, queries: list[str]) -> tuple[str, list]:
            """Fetch multiple queries in parallel, merge, deduplicate within row."""
            tasks = [
                c.get(f"{BASE}/search/songs", params={"query": q, "limit": 10})
                for q in queries
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            seen_in_row: set[str] = set()
            artist_count: dict[str, int] = {}
            merged: list[dict] = []
            for resp in responses:
                if isinstance(resp, Exception):
                    continue
                try:
                    songs = (resp.json().get("data") or {}).get("results") or []
                    for s in songs:
                        sid = s.get("id")
                        lang = s.get("language", "").lower()
                        tk = _title_key(s)
                        # Primary artist key for per-artist cap
                        artists = s.get("artists") or {}
                        primary = artists.get("primary") or [] if isinstance(artists, dict) else []
                        artist_key = (primary[0].get("name") or "").lower().strip() if primary else ""
                        if (sid and sid not in seen_in_row
                                and tk not in seen_in_row
                                and lang in _HOME_LANGUAGES
                                and _is_original(s)
                                and artist_count.get(artist_key, 0) < _MAX_PER_ARTIST):
                            merged.append(s)
                            seen_in_row.add(sid)
                            seen_in_row.add(tk)
                            if artist_key:
                                artist_count[artist_key] = artist_count.get(artist_key, 0) + 1
                except Exception:
                    pass
            return label, merged

        # All rows fetch in parallel
        fetched = await asyncio.gather(*[_fetch_row(lbl, qs) for lbl, qs in _ROWS])

    # Global deduplication by ID and title — earlier rows (Trending) have priority
    global_seen: set[str] = set()
    rows: list[dict] = []
    for label, songs in fetched:
        unique = []
        for s in songs:
            sid = s.get("id")
            tk = _title_key(s)
            if sid not in global_seen and tk not in global_seen:
                unique.append(s)
                global_seen.add(sid)
                global_seen.add(tk)
        items = [_card(s) for s in unique[:20]]
        if items:
            rows.append({"label": label, "items": items})

    trending = rows[0]["items"][:8] if rows else []
    return {"trending": trending, "rows": rows}
