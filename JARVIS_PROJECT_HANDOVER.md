# JARVIS Project Handover

## Current Project State
Stable, working. Nothing existing was rewritten in a behavior-changing way —
this session's work was entirely: finishing the deprecated Gemini SDK
migration across 8 files (same behavior, only the call shape changed),
adding one test per migrated file, and one `requirements.txt` cleanup line.
`main.py` / `ui.py` core app logic, `DESIGN.md`, and the Windows packaging
pipeline built in the prior session are all untouched.

## Project Context
- **Goal**: JARVIS is a personal desktop AI assistant (PyQt6 UI + Gemini
  Live), Windows 10/11 only. Must become a real installable app, not a
  "run from source" tool.
- **Architecture**: `main.py` (entry point) + `ui.py` (PyQt6 UI). Gemini
  Live wiring in `core/jarvis_client.py` / `core/live_model.py`. Agent loop
  in `agent/` (`planner.py`, `executor.py`, `error_handler.py`,
  `task_queue.py`). Screen/context awareness in `awareness/engine.py`.
  Tool implementations live in `actions/*.py`.
- **Design source of truth**: `DESIGN.md` — arc-reactor cyan/near-black
  theme, Space Grotesk + JetBrains Mono, staged-reveal motion, three-panel
  console. Not touched yet.
- There's also a separate hosted web product (`api/` FastAPI + `web/`
  Next.js, multi-user) — out of scope for the Windows desktop goal.
- Windows packaging pipeline (`scripts/build_windows.py`,
  `scripts/windows_installer.iss`, etc.) was built in a prior session and
  is still unverified on a real Windows machine — see Next Steps #1.

## Completed Work (this session)

**Finished the deprecated Gemini SDK migration** that a prior session
started with `agent/error_handler.py`. All runtime files that previously
called the deprecated `google.generativeai` SDK (`genai.configure()` +
`genai.GenerativeModel(...).generate_content(...)`) now use the current
`google.genai` SDK (`genai.Client(api_key=...)` +
`client.models.generate_content(model=..., contents=..., config=...)`),
matching the pattern already established in `agent/error_handler.py` and
`actions/screen_processor.py`.

Migrated, one file per pass, same model names and decision logic — only
the call shape changed:

1. **`agent/planner.py`** — `create_plan()` and `replan()`. System
   instructions now passed via `types.GenerateContentConfig`.
2. **`agent/executor.py`** — `_run_generated_code()`, `_detect_language()`,
   `_translate_to_goal_language()`, `_summarize()`.
3. **`actions/code_helper.py`** — finished what was a *partial* migration
   (only `_screen_debug_action` was on the new SDK before). Replaced
   `_get_gemini()` with `_get_genai_client()`; migrated `_write`,
   `_fix_code`, `_edit_action`, `_explain_action`, `_optimize_action`.
4. **`actions/computer_settings.py`** — `_detect_action()`.
5. **`actions/desktop.py`** — `_ask_gemini_for_desktop_action()`.
6. **`actions/dev_agent.py`** — `_plan_project()`, `_write_file()`,
   `_fix_project()`. Renamed the shared helper `_get_model(model_name)` →
   `_get_client()` since a `genai.Client` isn't model-specific; each call
   site now passes its own model name (`MODEL_PLANNER` / `MODEL_WRITER`)
   directly into `generate_content()`.
7. **`actions/flight_finder.py`** — date-expression parsing and
   `_parse_flights_with_gemini()`.
8. **`actions/youtube_video.py`** — `_summarize_with_gemini()`.

**Verification that the migration is actually complete**: both a
repo-wide grep and `core/qa_audit.py`'s own `deprecated_sdk_files` check
(the one added last session, scanning `main.py` + `actions/*.py` +
`agent/*.py` for the string `"google.generativeai"`) now return zero
matches. Next `jarvis --self-test` run should show that P2 finding gone.

**`requirements.txt`**: removed the now-unused `google-generativeai` line.
`google-genai` remains (that's the current SDK, still needed).

## Files Changed (this session)
- `agent/planner.py` (SDK migration, behavior unchanged)
- `agent/executor.py` (SDK migration, behavior unchanged)
- `actions/code_helper.py` (finished SDK migration, behavior unchanged)
- `actions/computer_settings.py` (SDK migration, behavior unchanged)
- `actions/desktop.py` (SDK migration, behavior unchanged)
- `actions/dev_agent.py` (SDK migration, behavior unchanged)
- `actions/flight_finder.py` (SDK migration, behavior unchanged)
- `actions/youtube_video.py` (SDK migration, behavior unchanged)
- `tests/test_core_resilience.py` (added 4 tests: planner, executor,
  code_helper, computer_settings — one per representative migrated file)
- `requirements.txt` (removed unused `google-generativeai` line)

No changes to `main.py`, `ui.py`, `agent/error_handler.py`,
`actions/screen_processor.py`, `core/`, `awareness/`, or the Windows
packaging scripts from the prior session.

## Important Architecture Decisions
- SDK migrations continued to be done one file at a time with a dedicated
  test each (per prior session's stated approach) — this session did all
  8 remaining files rather than stopping after one, since the pattern was
  already well-established and mechanical.
- Where a file had a shared "get me a configured model" helper
  (`_get_gemini()` in `code_helper.py`, `_get_model()` in `dev_agent.py`),
  it was renamed/reshaped to "get me a client" (`_get_genai_client()` /
  `_get_client()`) rather than keeping a model-specific wrapper, since
  `genai.Client` isn't tied to one model — this matches how
  `error_handler.py` and `screen_processor.py` already do it.
- Tests follow the exact fake-`sys.modules` injection pattern from the
  prior session's `test_error_handler_uses_google_genai_client_not_deprecated_sdk`:
  a `ModuleType("google.genai")` with a fake `Client` is patched into
  `sys.modules` via `patch.dict`, so the real (uninstalled) `google-genai`
  package is never required to test the call shape.
- Did not add a dedicated test for every one of the 8 files — added 4
  representative ones (planner, executor, code_helper, computer_settings)
  covering the different call shapes (with/without system_instruction,
  shared client helper vs. inline client). `desktop.py`, `dev_agent.py`,
  `flight_finder.py`, `youtube_video.py` were verified by compile +
  manual code review + the repo-wide SDK-audit check, but don't have a
  dedicated unit test yet — see Next Steps.

## Bugs / Issues
None introduced. No existing runtime behavior was changed — every call
site kept the same model name, same prompt content, same
error-handling/fallback structure; only `genai.configure()` +
`GenerativeModel(...).generate_content(...)` became
`genai.Client(...)` + `client.models.generate_content(model=..., contents=...)`.

## Testing Status
- All 8 migrated files pass `python3 -m py_compile`.
- `tests/test_core_resilience.py`: 22/22 passing (was 18 at the start of
  this session; added tests for planner, executor, code_helper,
  computer_settings SDK migrations). Run with:
  `python3 -m unittest tests.test_core_resilience -v`
- `tests/test_qa_system.py`: still 20/35 passing, 15 erroring — identical
  to the baseline documented by the prior session. All 15 errors are the
  same pre-existing `PortAudio library not found` sandbox gap on
  `import main`, unrelated to this session's changes. Confirmed this is
  the *same* 15, not a new regression.
- Repo-wide check confirms zero files under `main.py` / `actions/*.py` /
  `agent/*.py` still contain the string `"google.generativeai"`.
- **Not tested / not testable in this sandbox** (same as before): the
  Windows build/installer scripts (no Windows), and anything requiring
  the real `google-genai` package, `PyQt6`, or system audio libs — all
  still absent from this sandbox. Every migrated call site was verified
  with a faked `google.genai` module, not the real package.

## Next Steps (priority order)

1. **Verify packaging on a real Windows machine** — unchanged from last
   session, still the one thing that can't be checked further from here:
   - Run `scripts\setup_jarvis.bat`, then `scripts\build_windows.bat`.
   - Confirm `dist\JARVIS\JARVIS.exe` launches, creates `.env`, reaches the
     normal UI.
   - Compile `scripts\windows_installer.iss` with Inno Setup, confirm
     `JARVIS-Setup.exe` installs, shortcuts work, uninstall is clean.

2. **Deprecated-SDK cleanup is now DONE** — all 8 files from the prior
   handover's list are migrated. Optional polish if picked up again:
   - Add dedicated tests for `actions/desktop.py`, `actions/dev_agent.py`,
     `actions/flight_finder.py`, `actions/youtube_video.py` SDK calls
     (currently only compile-checked + manually reviewed, not unit-tested
     like the other 4 files were).
   - Consider running `jarvis --self-test` on a machine with `google-genai`
     installed to confirm `windows_packaging_findings()` /
     `deprecated_sdk_files` both come back clean end-to-end, not just via
     the standalone check run in this sandbox.

3. **Add an app icon** once branding assets exist; wire into
   `build_windows.py --icon` and `windows_installer.iss`'s
   `SetupIconFile`. Nothing done this session blocks this.

4. **Move on to actual product features** — packaging/infra and the SDK
   cleanup are both now in a reasonable state. Pick one of the original
   five areas (studying, coding, files/documents, screen understanding,
   computer interaction/automation) and go through `agent/planner.py` +
   relevant `actions/*.py` file(s) + `main.py`'s `TOOL_DECLARATIONS` to
   add or improve a tool, following `DESIGN.md` for anything UI-facing.
   Nothing done so far blocks this.

5. **Sandbox note for future sessions here**: no network access, and
   `google-genai`, `google-generativeai`, `PyQt6`, and PortAudio are all
   still missing. Anything touching live Gemini calls or the UI needs
   either network access restored or the `sys.modules` fake-package
   pattern used throughout `tests/test_core_resilience.py` (4 examples
   now, one per migrated file with a dedicated test).

No API keys, passwords, or secrets are included in this document or in any
file changed.
