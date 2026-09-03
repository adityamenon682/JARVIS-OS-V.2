# JARVIS Project Handover

## Current Project State
Working, stable. No existing files were rewritten — only new files added and
one README section appended. Desktop app (`main.py` + `ui.py`, PyQt6 +
Gemini Live) is untouched and behaves exactly as before.

## Context (architecture recap)
- Desktop app: `main.py` (entry point, has a `main()` and `cli_main()`),
  `ui.py` (PyQt6 UI). Gemini Live wiring in `core/jarvis_client.py` /
  `core/live_model.py`. Agent loop in `agent/`. Screen/context awareness in
  `awareness/engine.py`.
- Design system source of truth: `DESIGN.md` (arc-reactor cyan/black theme,
  Space Grotesk + JetBrains Mono, staged-reveal motion). Not touched this
  session.
- Separate hosted web product (`api/` FastAPI + `web/` Next.js) exists for
  multi-user cloud use — out of scope for the Windows desktop app goal.
- `main.py` already contained `running_as_app = getattr(sys, "frozen", False)`,
  meaning a PyInstaller-style packaged build was anticipated but never
  implemented. This made "Windows installable app" the safest, most aligned
  first task — it's additive and the app already expects it.

## Completed Work
1. **`scripts/build_windows.py`** — new PyInstaller build script. Produces
   `dist/JARVIS/JARVIS.exe` (onedir, windowed by default, `--console` flag
   available). Bundles `assets/` (fonts), `core/prompt.txt`, the `config/*
   .example.json` templates, and `.env.example`. Never bundles real secrets
   (`.env`, `config/api_keys.json`, `memory/long_term.json`) — those are
   created next to the exe on first run, same as the source checkout.
   Written in the same style as `scripts/setup_jarvis.py` (pathlib, a `run()`
   helper wrapping `subprocess.check_call`, small functions, `main() -> int`,
   `raise SystemExit(main())`).
2. **`scripts/build_windows.bat`** — double-clickable wrapper, matches the
   `@echo off` / `setlocal` / `cd /d "%~dp0.."` / `echo [prefix] ...` pattern
   used by `scripts/start_jarvis.bat` and `scripts/setup_jarvis.bat`.
3. **`requirements-build.txt`** — new file, holds `pyinstaller` only (kept
   out of `requirements.txt` so normal `jarvis` users never install it),
   using the same `platform_system` environment-marker pattern already used
   in `requirements.txt` for Windows-only deps.
4. **`README.md`** — added one short "Windows installable build" section
   before "## Documentation", matching existing heading/tone/code-block
   style. No other README content changed.

## Files Changed
- `scripts/build_windows.py` (new)
- `scripts/build_windows.bat` (new)
- `requirements-build.txt` (new)
- `README.md` (one section appended)

## Important Architecture Decisions
- Build tooling kept fully separate from runtime code — zero changes to
  `main.py`, `ui.py`, `core/`, `agent/`, or `awareness/`.
- PyInstaller is a *build-only* dependency (`requirements-build.txt`), not
  added to `requirements.txt`, so it never affects the normal
  `python scripts/setup_jarvis.py` / `jarvis` flow.
- Windowed build is the default (no console) for a normal double-click desktop
  app; `--console` is available for anyone who wants `JARVIS.exe --self-test`
  output visible.
- `.gitignore` already ignores `build/` and `dist/`, so no gitignore changes
  were needed.

## Bugs / Issues
None introduced. No existing behavior was changed.

## Testing Status
- `scripts/build_windows.py` was syntax-checked with `python3 -m py_compile`
  — compiles cleanly.
- **Not run end-to-end**, because this sandbox is Linux and has no network
  access to install PyInstaller or produce a real Windows `.exe`. The script
  itself refuses to run on non-Windows (`check_windows()`), by design.
- No changes were made to any code path that runs today, so existing app
  behavior is unaffected.

## Remaining Work (next steps, in suggested order)
1. **On an actual Windows machine**: run `scripts\setup_jarvis.bat` once,
   then `scripts\build_windows.bat`, and confirm `dist\JARVIS\JARVIS.exe`
   launches correctly, finds/creates `.env`, and reaches the normal JARVIS
   UI.
2. If PyQt6/Playwright/opencv resources are missing at runtime in the frozen
   build (common PyInstaller gotcha with those packages), add targeted
   `--hidden-import` / `--collect-all` flags to `build_windows.py` as needed
   — do not restructure the app to work around it.
3. Add an application icon (`.ico`) and wire it into `build_windows.py` via
   `--icon` once branding assets exist.
4. Decide on a real installer wrapper (Inno Setup / MSIX) around the
   PyInstaller output so it's a proper installable app rather than a folder
   to copy — this was explicitly requested but is a separate, larger task
   from the build script itself.
5. Continue down the original priority list from the architecture review:
   agent/tool additions, awareness features, or further UI work — none of
   this session's work blocks any of those.

No API keys, passwords, or secrets are included in this document or in any
file changed this session.
