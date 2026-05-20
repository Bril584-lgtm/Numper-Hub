"""Launches both Numper Ani and Numper Hub, then opens the Hub."""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HUB_PORT  = 7778
ANI_PORT  = 8000
ANI_DIR   = Path(__file__).parent.parent / "Numper-Ani"
HUB_DIR   = Path(__file__).parent

def start(cmd, cwd):
    return subprocess.Popen(cmd, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    procs = []

    if ANI_DIR.exists():
        procs.append(start(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(ANI_PORT)],
            cwd=ANI_DIR,
        ))
        print(f"Starting Numper Ani on port {ANI_PORT}...")

    procs.append(start(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(HUB_PORT)],
        cwd=HUB_DIR,
    ))
    print(f"Starting Numper Hub on port {HUB_PORT}...")

    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{HUB_PORT}")
    print("Opened browser. Close this window to stop both servers.")

    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
