"""Numper Hub — configuration."""
import os
from pathlib import Path

# Load .env from project root if present
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Get a free TMDB API key at: https://www.themoviedb.org/settings/api
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
SUBDL_API_KEY = os.getenv("SUBDL_API_KEY", "")
