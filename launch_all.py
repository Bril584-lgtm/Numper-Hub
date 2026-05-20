"""Launches Numper Hub and Numper Ani in a single terminal."""
import sys
import os
import time
import threading
import subprocess
import webbrowser
from pathlib import Path

HUB_PORT = 7778
ANI_PORT = 8000
ANI_DIR  = Path(__file__).parent.parent / "Numper-Ani"
HUB_DIR  = Path(__file__).parent


def stream(proc, prefix):
    for line in iter(proc.stdout.readline, b""):
        print(f"[{prefix}] {line.decode(errors='ignore').rstrip()}", flush=True)


def start(cwd, port, label):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    threading.Thread(target=stream, args=(proc, label), daemon=True).start()
    return proc


if __name__ == "__main__":
    print("=" * 48)
    print(f"  Numper Hub  →  http://127.0.0.1:{HUB_PORT}")
    print(f"  Numper Ani  →  http://127.0.0.1:{ANI_PORT}")
    print("  Ctrl+C to stop both")
    print("=" * 48)

    procs = []
    procs.append(start(HUB_DIR, HUB_PORT, "Hub"))

    if ANI_DIR.exists():
        procs.append(start(ANI_DIR, ANI_PORT, "Ani"))
    else:
        print(f"[Ani] Not found at {ANI_DIR} — skipping")

    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{HUB_PORT}")

    try:
        while all(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p in procs:
            p.terminate()
