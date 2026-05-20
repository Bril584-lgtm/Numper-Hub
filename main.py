"""Numper Hub — entry point."""
import subprocess, sys, time, webbrowser
from pathlib import Path

PORT = 7778

def main():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=Path(__file__).parent,
    )
    time.sleep(1.8)
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()

if __name__ == "__main__":
    main()
