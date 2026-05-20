# Numper Hub

A local web app for browsing and watching Movies, TV shows, and Spanish content — no ads, no accounts, launches straight from your PC.

## Sections

| Section | Theme | Content |
|---|---|---|
| Movies & TV | Crimson | Hollywood films, TV series, trending content |
| Spanish | Amber/Gold | Telenovelas, películas, series en español |

## Features

- Auto-rotating hero banner with trending titles
- Genre rows with horizontal scroll
- Live search with poster suggestions
- Full details modal — synopsis, genres, rating, year
- TV shows: season selector + full episode grid
- Inline player — no redirects, plays inside the app
- 30-minute response cache for fast repeat loads

## Requirements

- Python 3.10+
- A free TMDB API key — [get one here](https://www.themoviedb.org/settings/api)

## Setup

```bash
git clone https://github.com/Bril584-lgtm/Numper-Hub.git
cd Numper-Hub
pip install -r requirements.txt
playwright install chromium
```

## Run

**Windows:**
```
set TMDB_API_KEY=your_token_here
python main.py
```

Or set `TMDB_API_KEY` permanently in your system environment variables and just double-click `run.bat`.

The app opens automatically at `http://127.0.0.1:7778`.

## Stack

- **Backend:** FastAPI + uvicorn
- **Metadata:** TMDB API
- **Streams:** vidsrc.to / vidsrc.me / embed.su
- **Embed extraction:** Playwright (headless Chromium)
- **Frontend:** Vanilla JS, no frameworks
