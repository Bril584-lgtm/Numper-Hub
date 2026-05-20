# Numper Hub

A local web app for browsing and watching Movies, TV shows, Spanish content, Anime, and Hentai — no ads, no accounts, launches straight from your PC.

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
| 🎬 Movies & TV | Crimson | Hollywood films, TV series, trending content |
| 🌎 Spanish | Amber/Gold | Telenovelas, películas, series en español |
| ⛩️ Anime | Purple | Anime series and films via Numper Ani |
| 🔞 Hentai | Pink | Adult anime — 18+ only |

---

## Features

- Auto-rotating hero banner with trending titles
- Genre/category rows with horizontal scroll
- Live search with poster suggestions
- Full details modal — synopsis, tags, genres, rating
- TV shows: season selector + full episode grid
- HLS.js direct playback — best quality automatically selected
- 30-minute response cache for fast repeat loads
- Single launcher starts all servers at once

---

## Requirements

- Python 3.10+
- A free TMDB API key — [get one here](https://www.themoviedb.org/settings/api)
- Both **Numper Hub** and **Numper Ani** cloned into the same parent folder

---

## Installation

### 1. Clone both repos into the same folder

```
parent-folder/
├── Numper-Hub/
└── Numper-Ani/
```

```bash
git clone https://github.com/Bril584-lgtm/Numper-Hub.git
git clone https://github.com/Bril584-lgtm/Numper-Ani.git
```

### 2. Install dependencies for both

```bash
cd Numper-Hub
pip install -r requirements.txt

cd ../Numper-Ani
pip install -r requirements.txt
```

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Set up your TMDB API key

Create a file called `.env` inside the `Numper-Hub` folder:

```
TMDB_API_KEY=your_token_here
```

Get a free key at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)

---

## Run

Double-click `launch_all.bat` inside `Numper-Hub`.

This starts both servers and opens your browser to the Hub automatically.

| App | URL |
|---|---|
| Numper Hub | http://127.0.0.1:7778 |
| Numper Ani | http://127.0.0.1:8000 |

Press `Ctrl+C` in the terminal to stop both servers.

---

## Stack

- **Backend:** FastAPI + uvicorn
- **Metadata:** TMDB API
- **Movies/TV Streams:** vidsrc.to / vidsrc.me / embed.su
- **Hentai Streams:** hanime.tv unofficial API
- **Embed extraction:** Playwright (headless Chromium)
- **Frontend:** Vanilla JS, HLS.js — no frameworks
