"""Build a standalone Windows executable for JARVIS (no VS Code / Python required to run it).

Produces a onedir PyInstaller build at dist/JARVIS/JARVIS.exe that bundles
the app, its fonts, and the config/prompt templates it reads on first run.
Real secrets (.env, config/api_keys.json, memory/long_term.json) are never
bundled — the packaged app creates them next to the exe on first launch,
same as the source checkout does today.

Usage (Windows only):
    .venv\\Scripts\\python.exe scripts\\build_windows.py [--console]

    --console   keep the terminal window open (useful for debugging /
                still lets `JARVIS.exe --self-test` print output).
                Default is windowed (no console), for a normal desktop app.

Known limitation: browser-automation tools (Playwright) download their own
browser binaries separately (`playwright install`) and are not bundled by
PyInstaller. Users of a packaged build who want browser tools still need to
run that once. This is unrelated to the JARVIS UI/voice/file/screen tools,
which work fully offline-packaged.

To turn the resulting dist/JARVIS/ folder into a real installer (Start Menu
entry, uninstaller, Program Files placement), run scripts/windows_installer.iss
through Inno Setup after this script finishes. See that file's header for
instructions.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "JARVIS"

# (source path relative to ROOT, destination folder inside the bundle)
DATA_FILES = [
    ("core/prompt.txt", "core"),
    ("assets", "assets"),
    ("config/api_keys.example.json", "config"),
    ("config/layout_settings.example.json", "config"),
    ("config/ui_settings.example.json", "config"),
    (".env.example", "."),
]


def run(*args: str) -> None:
    print("+", " ".join(args))
    subprocess.check_call(args, cwd=ROOT)


def check_windows() -> None:
    if os.name != "nt":
        print("[build_windows] This script produces a Windows .exe and must be run on Windows.")
        raise SystemExit(1)


def check_pyinstaller() -> None:
    if shutil.which("pyinstaller") is None:
        print("[build_windows] PyInstaller not found. Install build dependencies first:")
        print("  .venv\\Scripts\\python.exe -m pip install -r requirements-build.txt")
        raise SystemExit(1)


def clean() -> None:
    for path in (DIST / APP_NAME, BUILD / APP_NAME):
        if path.exists():
            print(f"[build_windows] Removing previous build: {path}")
            shutil.rmtree(path)


# Packages known to trip up PyInstaller's static import scan because they
# load plugins/resources dynamically (Qt plugins, native codecs, etc.).
# Using --collect-all is broader than strictly necessary but far more
# reliable than chasing individual "hidden import" errors after each build.
COLLECT_ALL = ["PyQt6", "cv2", "mss"]


def build(windowed: bool) -> int:
    args = [
        "pyinstaller",
        "--noconfirm",
        "--name",
        APP_NAME,
        "--paths",
        str(ROOT),
    ]
    args.append("--windowed" if windowed else "--console")
    for package in COLLECT_ALL:
        args += ["--collect-all", package]
    for source, dest in DATA_FILES:
        src_path = ROOT / source
        if not src_path.exists():
            print(f"[build_windows] Skipping missing data file: {source}")
            continue
        args += ["--add-data", f"{src_path}{os.pathsep}{dest}"]
    args.append(str(ROOT / "main.py"))

    run(*args)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--console",
        action="store_true",
        help="Keep the console window (default is a windowed app with no console).",
    )
    args = parser.parse_args()

    check_windows()
    check_pyinstaller()
    clean()
    build(windowed=not args.console)

    exe_path = DIST / APP_NAME / f"{APP_NAME}.exe"
    print("\n[build_windows] Build complete.")
    print(f"[build_windows] Executable: {exe_path}")
    print("[build_windows] Copy .env.example to .env next to the .exe and add GEMINI_API_KEY,")
    print("[build_windows] or run the .exe once to have it created automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
