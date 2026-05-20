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

## Full Setup Guide

Follow every step carefully. This should take about 10 minutes total.

---

### Step 1 — Install Python

1. Go to **https://www.python.org/downloads**
2. Click the big yellow **Download Python** button
3. Run the installer
4. ⚠️ **IMPORTANT:** On the first screen, check the box that says **"Add Python to PATH"** before clicking Install
5. Click **Install Now** and wait for it to finish
6. To verify it worked, open Command Prompt and type:
   ```
   python --version
   ```
   You should see something like `Python 3.12.0`

---

### Step 2 — Install Git

1. Go to **https://git-scm.com/downloads**
2. Click **Download for Windows**
3. Run the installer — click Next through all the options, defaults are fine
4. To verify it worked, open Command Prompt and type:
   ```
   git --version
   ```
   You should see something like `git version 2.43.0`

---

### Step 3 — Download Numper Hub

Open **Command Prompt** and run these commands one at a time:

```
git clone https://github.com/Bril584-lgtm/Numper-Hub.git
cd Numper-Hub
```

This downloads the project to your PC into a folder called `Numper-Hub`.

---

### Step 4 — Install Dependencies

Still inside Command Prompt in the `Numper-Hub` folder, run:

```
pip install -r requirements.txt
```

Wait for it to finish. This installs FastAPI, Playwright, and all required libraries.

---

### Step 5 — Install the Browser (for stream extraction)

Run this command:

```
playwright install chromium
```

This downloads a small headless browser that Numper Hub uses to extract streams from video sites.

---

### Step 6 — Get a Free TMDB API Key

Numper Hub needs a free API key from TMDB (The Movie Database) to load movie and TV show info.

1. Go to **https://www.themoviedb.org/signup** and create a free account
2. Check your email and verify your account
3. Go to **https://www.themoviedb.org/settings/api**
4. Click **Create** → choose **Developer**
5. Fill in the form:
   - Application Name: `Numper Hub`
   - Application URL: `http://localhost:7778`
   - Application Summary: `Personal local media browser`
   - Select **Personal** for intended use
6. Submit — your key will appear on the page
7. Copy the **API Read Access Token** (the long one starting with `eyJ...`)

---

### Step 7 — Add Your API Key

1. Open the `Numper-Hub` folder on your PC
2. Create a new text file called `.env` (just `.env`, no other name)
3. Open it with Notepad and type exactly this — replacing the placeholder with your actual token:
   ```
   TMDB_API_KEY=your_token_here
   ```
4. Save the file

> **Note:** If Windows won't let you name it `.env`, open Notepad, type the line above, then go to File → Save As → change "Save as type" to "All Files" → type `.env` as the filename → Save.

---

### Step 8 — Launch

Double-click **`launch_all.bat`** inside the `Numper-Hub` folder.

A terminal window will open and your browser will automatically go to:

```
http://127.0.0.1:7778
```

You'll see the hub with all four sections ready to use.

> To stop the app, close the terminal window or press `Ctrl+C` inside it.

---

## Every Time You Want to Use It

Just double-click **`launch_all.bat`**. That's it.

---

## Troubleshooting

**`python` is not recognized**
→ You forgot to check "Add Python to PATH" during install. Uninstall Python and reinstall, making sure to check that box.

**`pip install` fails**
→ Try running Command Prompt as Administrator (right-click → Run as administrator) and run the command again.

**Browser opens but shows nothing / blank page**
→ Your `.env` file is missing or the API key is wrong. Double-check Step 7.

**Stream doesn't play / 502 error**
→ The stream source may be temporarily down. Try a different anime or movie, or wait a few minutes and try again.

**`playwright install` takes a long time**
→ That's normal — it's downloading a browser. Let it finish.

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
