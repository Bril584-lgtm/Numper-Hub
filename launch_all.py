"""Launches Numper Hub and Numper Ani in a single terminal."""
import sys
import os
import time
import threading
import webbrowser
from pathlib import Path

HUB_PORT = 7778
ANI_PORT = 8000
ANI_DIR  = Path(__file__).parent.parent / "Numper-Ani"
HUB_DIR  = Path(__file__).parent


def run_hub():
    import uvicorn
    os.chdir(HUB_DIR)
    sys.path.insert(0, str(HUB_DIR))
    uvicorn.run("server:app", host="127.0.0.1", port=HUB_PORT, log_level="info")


def run_ani():
    if not ANI_DIR.exists():
        print("[Numper Ani] Not found — skipping")
        return
    import uvicorn
    os.chdir(ANI_DIR)
    sys.path.insert(0, str(ANI_DIR))
    uvicorn.run("server:app", host="127.0.0.1", port=ANI_PORT, log_level="info")


if __name__ == "__main__":
    print("=" * 48)
    print("  Numper Hub   →  http://127.0.0.1:7778")
    print("  Numper Ani   →  http://127.0.0.1:8000")
    print("  Press Ctrl+C to stop both servers")
    print("=" * 48)

    t_ani = threading.Thread(target=run_ani, daemon=True)
    t_hub = threading.Thread(target=run_hub, daemon=True)

    t_ani.start()
    t_hub.start()

    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{HUB_PORT}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
