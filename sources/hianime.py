"""HiAnime (Zoro) source backend — DISABLED: site shut down May 2026."""
import re
import httpx

BASE = "https://hianime.to"
API = "https://hianime.to/ajax"
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
HEADERS = {"User-Agent": AGENT, "Referer": BASE, "X-Requested-With": "XMLHttpRequest"}

_OFFLINE = True


async def search(query: str, dub: bool = False) -> list[dict]:
    if _OFFLINE:
        return []
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(f"{BASE}/search", params={"keyword": query})
        html = r.text

    results = []
    # Parse search results from HTML
    for m in re.finditer(
        r'href="/([^"?]+)\?ref=search"[^>]*>.*?<span[^>]*class="[^"]*film-name[^"]*"[^>]*>([^<]+)',
        html, re.DOTALL
    ):
        slug = m.group(1)
        title = m.group(2).strip()
        results.append({
            "id": slug,
            "title": title,
            "episodes": 0,
            "source": "hianime",
        })

    return results[:20]


async def get_episode_id(show_slug: str, ep_num: int) -> str | None:
    """Get the internal episode ID for a show slug + episode number."""
    # First get the show detail page to find the show ID
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(f"{BASE}/{show_slug}")
        html = r.text
        m = re.search(r'data-id="(\d+)"', html)
        if not m:
            return None
        show_id = m.group(1)

        # Get episodes list
        r2 = await client.get(f"{API}/v2/episode/list/{show_id}")
        data = r2.json()
        ep_html = data.get("html", "")

    ep_matches = re.findall(r'data-id="(\d+)"[^>]*data-number="(\d+)"', ep_html)
    for ep_id, ep_no in ep_matches:
        if int(ep_no) == ep_num:
            return ep_id
    return None


async def get_stream_url(ep_id: str, dub: bool = False) -> str | None:
    """Get the stream URL for a given episode ID."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        # Get server list
        r = await client.get(f"{API}/v2/episode/servers", params={"episodeId": ep_id})
        data = r.json()
        servers_html = data.get("html", "")

    # Find server with desired type (dub/sub)
    server_type = "dub" if dub else "sub"
    server_matches = re.findall(
        rf'data-type="{server_type}"[^>]*data-id="(\d+)"[^>]*data-server-id="(\d+)"',
        servers_html
    )
    if not server_matches:
        # Fallback to any type
        server_matches = re.findall(r'data-id="(\d+)"[^>]*data-server-id="(\d+)"', servers_html)

    if not server_matches:
        return None

    for server_data_id, server_id in server_matches[:3]:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            r = await client.get(
                f"{API}/v2/episode/sources",
                params={"id": server_data_id}
            )
            src_data = r.json()

        link = src_data.get("link") or src_data.get("url")
        if link:
            # Try to extract stream from embed
            if ".m3u8" in link:
                return link
            from .playwright_extractor import extract_stream
            stream = await extract_stream(link)
            if stream:
                return stream

    return None
