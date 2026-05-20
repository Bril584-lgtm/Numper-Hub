"""Numper Hub — entry point."""
import os
import platform
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 7778
ENV_FILE = Path(__file__).parent / ".env"
HERE = Path(__file__).parent.resolve()


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


def _desktop():
    if platform.system() == "Windows":
        result = subprocess.run(
            ["powershell", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True,
        )
        p = result.stdout.strip()
        return Path(p) if p else Path.home() / "Desktop"
    return Path.home() / "Desktop"


def _shortcut_path():
    system = platform.system()
    desktop = _desktop()
    if system == "Windows":
        return desktop / "Numper Hub.lnk"
    elif system == "Darwin":
        return desktop / "Numper Hub.command"
    else:
        return desktop / "numper-hub.desktop"


def _create_shortcut():
    system = platform.system()
    path = _shortcut_path()
    try:
        if system == "Windows":
            python = Path(sys.executable).resolve()
            ps = (
                f'$ws = New-Object -ComObject WScript.Shell;'
                f'$s = $ws.CreateShortcut("{path}");'
                f'$s.TargetPath = "{python}";'
                f'$s.Arguments = "numper-hub.py";'
                f'$s.WorkingDirectory = "{HERE}";'
                f'$s.Save()'
            )
            subprocess.run(["powershell", "-Command", ps], capture_output=True)
        elif system == "Darwin":
            path.write_text(f'#!/bin/bash\ncd "{HERE}" && python3 numper-hub.py\n')
            os.chmod(path, 0o755)
        else:
            path.write_text(
                f"[Desktop Entry]\nType=Application\nName=Numper Hub\n"
                f'Exec=bash -c "cd {HERE} && python3 numper-hub.py"\nTerminal=true\n'
            )
            os.chmod(path, 0o755)
        print(f"Shortcut created: {path}\n")
    except Exception as e:
        print(f"Couldn't create shortcut: {e}\n")


def _prompt_jimaku_token():
    if os.environ.get("JIMAKU_TOKEN"):
        return
    print("Anime subtitles use Jimaku.cc — get a free token at: https://jimaku.cc/settings")
    print("(Press Enter to skip — subtitles won't auto-load but you can still load files manually)")
    print()
    token = input("Paste your Jimaku token (or press Enter to skip): ").strip()
    if not token:
        print()
        return
    os.environ["JIMAKU_TOKEN"] = token
    existing = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    if "JIMAKU_TOKEN=" in existing:
        lines = [
            f"JIMAKU_TOKEN={token}" if l.startswith("JIMAKU_TOKEN=") else l
            for l in existing.splitlines()
        ]
        ENV_FILE.write_text("\n".join(lines) + "\n")
    else:
        with open(ENV_FILE, "a") as f:
            f.write(f"JIMAKU_TOKEN={token}\n")
    print("Token saved to .env\n")


def _maybe_offer_shortcut():
    if _shortcut_path().exists():
        return
    ans = input("Create a desktop shortcut? [y/n]: ").strip().lower()
    if ans == "y":
        _create_shortcut()


def main():
    _load_env()
    _prompt_tmdb_key()
    _prompt_jimaku_token()
    _maybe_offer_shortcut()
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
