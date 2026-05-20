"""Numper Hub — entry point."""
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 7778
ENV_FILE = Path(__file__).parent / ".env"


def _load_env():
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _prompt_tmdb_key():
    if os.environ.get("TMDB_API_KEY"):
        return
    print("\nNumper Hub needs a TMDB API key to load Movies and Spanish content.")
    print("Get a free one at: https://www.themoviedb.org/settings/api")
    print()
    key = input("Paste your API key (or press Enter to skip): ").strip()
    if not key:
        print("Skipping — Movies and Spanish sections won't work without a key.\n")
        return
    os.environ["TMDB_API_KEY"] = key
    existing = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    if "TMDB_API_KEY=" in existing:
        lines = [
            f"TMDB_API_KEY={key}" if l.startswith("TMDB_API_KEY=") else l
            for l in existing.splitlines()
        ]
        ENV_FILE.write_text("\n".join(lines) + "\n")
    else:
        with open(ENV_FILE, "a") as f:
            f.write(f"TMDB_API_KEY={key}\n")
    print("Key saved to .env\n")


def main():
    _load_env()
    _prompt_tmdb_key()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=Path(__file__).parent,
        env=os.environ.copy(),
    )
    time.sleep(1.8)
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
