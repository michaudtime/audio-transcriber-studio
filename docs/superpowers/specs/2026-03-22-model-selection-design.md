# Model Selection Design

**Date:** 2026-03-22
**Feature:** Easy model switching across all tools

---

## Overview

Add the ability to switch between three WhisperX model sizes — fast, accurate, and lightweight — with the selection persisting between sessions via a `settings.json` file. The selection surface differs per tool: a numbered console menu in `transcribe.bat` and radio buttons in the recorder GUI.

---

## Models

Three models available, defined in `constants.py`:

| Key | Label | Use case |
|-----|-------|----------|
| `large-v3-turbo` | Fast — large-v3-turbo (recommended) | Default, best balance of speed and quality |
| `large-v3` | Best — large-v3 (max accuracy) | When accuracy matters more than speed |
| `medium` | Light — medium (low-end hardware) | Weaker GPUs or faster turnaround |

---

## Persistence Layer

### `settings.json`
A JSON file in the project root storing user preferences:
```json
{"model": "large-v3-turbo"}
```

- Created automatically with defaults if it doesn't exist
- Gitignored — not committed to the repo (add near `config.bat` in `.gitignore`)
- Never written by batch scripts directly; always via Python

### `settings.py`
A small module with two functions used by all Python scripts.
The `settings.json` path is always resolved relative to `settings.py`'s own directory (`Path(__file__).parent`), never relative to `cwd`, so drag-and-drop and bat invocations behave identically.

```python
def load_settings() -> dict
def save_settings(data: dict) -> None
```

- `load_settings()` reads `settings.json`; returns `{"model": DEFAULT_MODEL}` if the file is missing or contains malformed JSON
- `save_settings()` writes the full settings dict to `settings.json` (standard write is sufficient; atomic write is not required for a single-key file where `load_settings` already self-heals on malformed input)

---

## `constants.py` Changes

Add the model list:
```python
MODELS = [
    ("large-v3-turbo", "Fast   — large-v3-turbo  (recommended)"),
    ("large-v3",       "Best   — large-v3         (max accuracy)"),
    ("medium",         "Light  — medium            (low-end hardware)"),
]
MODEL_KEYS = [m[0] for m in MODELS]
DEFAULT_MODEL = "large-v3-turbo"
```

---

## `transcribe.py` Changes

- Remove hardcoded `MODEL = "large-v3-turbo"` constant
- Add `from settings import load_settings` import
- Load model from `load_settings()["model"]` at startup
- Update the printed header (currently `"large-v3-turbo + diarize"`) to use the dynamic model value, e.g. `f"{MODEL} + diarize"`

---

## `transcribe.bat` Menu

`transcribe.bat` calls `whisperx` directly (not via `transcribe.py`), so it must both save the selection to `settings.json` and set a local `SELECTED_MODEL` env var that is substituted into the `--model` flag.

**Flow:**
1. On launch, read current model from `settings.json` into `SELECTED_MODEL` via Python one-liner
2. Display menu with current model marked `[current]`
3. On valid selection (1–3): save to `settings.json` via Python one-liner, update `SELECTED_MODEL`
4. On Enter (no input): keep existing `SELECTED_MODEL`, skip save
5. On invalid input: re-prompt once; on second invalid input print `"Invalid input. Using current model: <SELECTED_MODEL>"` and continue with existing value
6. Pass `--model %SELECTED_MODEL%` in both the auto-detect and fixed-speaker `whisperx` invocations (replacing the current hardcoded `large-v3-turbo`)

**Menu display:**
```
  Select model:
    1) Fast   — large-v3-turbo  (recommended)  [current]
    2) Best   — large-v3         (max accuracy)
    3) Light  — medium            (low-end hardware)

  Enter 1-3 (or press Enter to keep current):
```

**Python one-liner to read current model (used in bat):**
```bat
for /f %%M in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "from settings import load_settings; print(load_settings()[\"model\"])"') do set SELECTED_MODEL=%%M
```

**Python one-liner to save selected model (used after valid input):**
```bat
"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "from settings import load_settings, save_settings; s=load_settings(); s['model']='%SELECTED_MODEL%'; save_settings(s)"
```

---

## Recorder GUI Changes

### Layout
Radio buttons inserted between the name field and the Record button:

```
Name: [________________] (optional)

( ) Fast   — large-v3-turbo  (recommended)
( ) Best   — large-v3         (max accuracy)
( ) Light  — medium            (low-end hardware)

[ ⏺  Record          ]
  00:00:00
  Idle
```

### Behaviour
- Remove hardcoded `MODEL = "large-v3-turbo"` constant from `recorder.py`
- Add `from settings import load_settings, save_settings` import
- On startup: call `load_settings()["model"]`, set the matching radio button
- On change: load-modify-save round-trip: `s = load_settings(); s["model"] = selected_key; save_settings(s)`
- During saving/transcribing: radio buttons disabled (same as Record button)
- Re-enabled in `_on_transcription_done`

---

## `.gitignore` Addition

Add `settings.json` near the `config.bat` entry (user-local preference files section).

---

## Recommended Implementation Order

To avoid broken intermediate states, implement in this order:

1. `constants.py` — add `MODELS`, `MODEL_KEYS`, `DEFAULT_MODEL`
2. `settings.py` — new module, no dependencies on other changed files
3. `transcribe.py` — depends on `constants.py` and `settings.py`
4. `recorder.py` — depends on `constants.py` and `settings.py`
5. `transcribe.bat` — depends on `settings.py` being importable via the venv
6. `.gitignore` — add `settings.json`

---

## Files Changed

| File | Change |
|------|--------|
| `constants.py` | Add `MODELS`, `MODEL_KEYS`, `DEFAULT_MODEL` |
| `settings.py` | New module — `load_settings()` / `save_settings()` |
| `transcribe.py` | Remove `MODEL` constant; load from settings; update header string |
| `recorder.py` | Remove `MODEL` constant; add radio buttons; load/save via settings; disable during transcription |
| `transcribe.bat` | Add model menu; read/write settings.json via Python one-liners; pass `%SELECTED_MODEL%` to `--model` |
| `.gitignore` | Add `settings.json` |
