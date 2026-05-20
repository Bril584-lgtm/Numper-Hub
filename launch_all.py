"""Launches Numper Hub (all sections included)."""
import sys
import os
import time
import webbrowser
import subprocess
from pathlib import Path

HUB_PORT = 7778
HUB_DIR  = Path(__file__).parent

if __name__ == "__main__":
    print("=" * 48)
    print(f"  Numper Hub  →  http://127.0.0.1:{HUB_PORT}")
    print("  Anime · Movies · Spanish · Hentai")
    print("  Press Ctrl+C to stop")
    print("=" * 48)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app",
         "--host", "127.0.0.1", "--port", str(HUB_PORT)],
        cwd=HUB_DIR, env=env,
    )

    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{HUB_PORT}")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        proc.terminate()
