# Numper Hub

A local web app for browsing and watching Anime, Movies, TV shows, Spanish content, and Hentai — all in one place, no ads, no accounts, launches straight from your PC.

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

## Features

**Anime**
- AniList-powered home — trending hero, genre rows, continue watching
- Search across AllAnime, GogoAnime, and AnimePahe simultaneously
- A-Z browse with DUB / NSFW toggles
- Provider switcher — switch between sources with one click
- Full-screen HLS.js player — best quality locked automatically
- Skip Intro / Skip Recap buttons (AniSkip)
- Auto subtitles (Jimaku.cc)
- Watch history

**Movies & TV / Spanish**
- Auto-rotating hero banner with trending titles
- Genre rows with horizontal scroll
- Live search with poster suggestions
- Season selector + full episode grid for TV shows
- Inline iframe player

**Hentai**
- Browse by Trending, New, or All-Time
- Live search with suggestions
- HLS.js direct playback — best quality automatically

---

## Requirements

- Python 3.10+
- A free TMDB API key — [get one here](https://www.themoviedb.org/settings/api)

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/Bril584-lgtm/Numper-Hub.git
cd Numper-Hub
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Set up your TMDB API key

Create a `.env` file inside the `Numper-Hub` folder:

```
TMDB_API_KEY=your_token_here
```

Get a free key at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)

---

## Run

Double-click `launch_all.bat` — starts the server and opens your browser automatically.

Or from the terminal:

```bash
python main.py
```

Opens at **http://127.0.0.1:7778**

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
