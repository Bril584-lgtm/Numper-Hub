"""Subtitle fetcher — SubDL (https://subdl.com, free API key required)."""
import io
import os
import re
import zipfile
import httpx

_API = "https://api.subdl.com/api/v1/subtitles/"
_DL  = "https://dl.subdl.com"
_EXTS = (".srt", ".vtt", ".ass", ".ssa")


def _ass_ts(t: str) -> str:
    try:
        h, m, rest = t.strip().split(":")
        s, cs = rest.split(".")
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{int(cs) * 10:03d}"
    except Exception:
        return t


def _ass_to_vtt(text: str) -> str:
    lines = text.splitlines()
    out = ["WEBVTT", ""]
    in_events = False
    fields: list[str] = []
    for line in lines:
        s = line.strip()
        if s == "[Events]":
            in_events = True
            continue
        if in_events:
            if s.startswith("["):
                break
            if s.startswith("Format:"):
                fields = [f.strip() for f in s[7:].split(",")]
                continue
            if s.startswith("Dialogue:") and fields:
                parts = s[9:].split(",", len(fields) - 1)
                if len(parts) < len(fields):
                    continue
                fmap = dict(zip(fields, parts))
                body = fmap.get("Text", "")
                body = re.sub(r"\{[^}]*\}", "", body)
                body = body.replace("\\N", "\n").replace("\\n", "\n").strip()
                if body:
                    out += [f"{_ass_ts(fmap.get('Start',''))} --> {_ass_ts(fmap.get('End',''))}", body, ""]
    return "\n".join(out)


def _to_vtt(name: str, content: str) -> str:
    lo = name.lower()
    if lo.endswith(".srt"):
        return "WEBVTT\n\n" + re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", content)
    if lo.endswith((".ass", ".ssa")):
        return _ass_to_vtt(content)
    return content


def _pick_from_zip(z: zipfile.ZipFile, ep: int) -> tuple[str, str] | None:
    ep_tag = f"E{ep:02d}"
    all_subs = [n for n in z.namelist() if any(n.lower().endswith(e) for e in _EXTS)]
    # Prefer file matching the episode number
    candidates = [n for n in all_subs if ep_tag in n.upper()] or all_subs
    if not candidates:
        return None
    # Prefer srt/vtt over ass
    name = next((n for n in candidates if n.lower().endswith((".srt", ".vtt"))), candidates[0])
    content = z.read(name).decode("utf-8", errors="replace")
    return name.split("/")[-1], _to_vtt(name, content)


async def fetch(title: str, ep: int) -> list[dict]:
    """Return [{name, content}] with VTT subtitle text. Empty list on failure."""
    api_key = os.getenv("SUBDL_API_KEY", "")
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Step 1 — find show sd_id; try tv first, fall back to no-type filter
            sd_id = None
            for extra in [{"type": "tv"}, {}]:
                r1 = await client.get(_API, params={"api_key": api_key, "film_name": title, **extra})
                if r1.status_code == 200:
                    shows = r1.json().get("results") or []
                    if shows:
                        sd_id = shows[0]["sd_id"]
                        break
            if not sd_id:
                return []

            # Step 2 — get subtitle entries for this episode (no season filter — anime varies)
            r2 = await client.get(_API, params={
                "api_key": api_key,
                "sd_id": sd_id,
                "episode_number": ep,
                "languages": "EN",
            })
            if r2.status_code != 200:
                return []
            entries = r2.json().get("subtitles") or []
            if not entries:
                return []

            # Prefer single-episode packs; fall back to batch packs
            single = [e for e in entries if e.get("episode_from") == e.get("episode_end") == ep]
            ordered = single + [e for e in entries if e not in single]

            for entry in ordered:
                r3 = await client.get(_DL + entry["url"])
                if r3.status_code != 200:
                    continue
                with zipfile.ZipFile(io.BytesIO(r3.content)) as z:
                    result = _pick_from_zip(z, ep)
                    if result:
                        name, content = result
                        return [{"name": name, "content": content}]
    except Exception:
        pass
    return []
