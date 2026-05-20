# Numper Hub

A local web app for browsing and watching Anime, Movies, TV shows, Spanish content, and Hentai — all in one place, no ads, no subscriptions, launches straight from your terminal.

---

## Anime only?

If you just want the anime section as a standalone app, check out **[Numper Ani](https://github.com/Bril584-lgtm/Numper-Ani)**.

---

## ⚠️ Disclaimer

- This project is intended for **personal, educational use only**.
- Numper Hub does not host, store, or distribute any media content. All streams are sourced from third-party public embeds and APIs.
- The developers are not responsible for the content provided by third-party sources.
- Hentai content is **strictly 18+**. By using that section you confirm you are of legal age in your country.
- Use of this software is at your own risk. Always comply with the laws of your country.

---

## Sections

| Section | Theme | Content |
|---|---|---|
| ⛩️ Anime | Orange | Anime series and films — sub & dub, A-Z browse, skip intro |
| 🎬 Movies & TV | Crimson | Hollywood films, TV series, trending content |
| 🌎 Spanish | Amber/Gold | Telenovelas, películas, series en español |
| 🔞 Hentai | Pink | Adult anime — 18+ only |

---

## Setup

### Requirements

- **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads) *(check "Add Python to PATH" during install)*

No Git required — download the repo as a ZIP from the green **Code** button → **Download ZIP**, then extract it.

### Install dependencies

Open a terminal in the `Numper-Hub` folder and run:

```
pip install -r requirements.txt
playwright install chromium
```

### API Key (Movies & TV only)

The Movies and Spanish sections use TMDB for metadata. Get a free API key at **https://www.themoviedb.org/settings/api**.

When you launch the app for the first time without a key configured, it will prompt you to paste one in — the `.env` file is created automatically.

### Launch

```
python numper-hub.py
```

Your browser opens automatically at `http://127.0.0.1:7778`. Press `Ctrl+C` to stop.

---

## Every Time You Want to Use It

```
python numper-hub.py
```

---

## Troubleshooting

**`python` is not recognized**
→ Python isn't on your PATH. Reinstall it and check the "Add Python to PATH" box.

**`pip install` fails**
→ Try running the terminal as Administrator.

**Movies/Spanish shows nothing**
→ Your TMDB API key is missing or invalid. Delete `.env` and re-run the launcher to enter a new key.

**Stream doesn't play / 502 error**
→ The stream source may be temporarily down. Try a different title or wait a few minutes.

**`playwright install` takes a long time**
→ Normal — it's downloading a browser. Let it finish.

---

## Stack

- **Backend:** FastAPI + uvicorn
- **Anime metadata:** AniList GraphQL API + Jikan (MyAnimeList)
- **Anime streams:** AllAnime, GogoAnime, AnimePahe
- **Movies/TV metadata:** TMDB API
- **Movies/TV streams:** vidsrc.to / vidsrc.me / embed.su
- **Hentai streams:** hanime.tv unofficial API
- **Embed extraction:** Playwright (headless Chromium)
- **Frontend:** Vanilla JS, HLS.js — no frameworks
