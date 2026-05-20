"""Numper Hub — configuration."""
import os

# Get a free TMDB API key at: https://www.themoviedb.org/settings/api
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
