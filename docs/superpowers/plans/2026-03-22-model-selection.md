# Model Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a numbered console menu to `transcribe.bat` and radio buttons to the recorder GUI so the user can switch between three WhisperX model sizes, with the selection persisting in `settings.json`.

**Architecture:** A new `settings.py` module owns all read/write of `settings.json`. `constants.py` defines the three model options. `transcribe.py` reads the model at startup. `recorder.py` reads it on launch and writes on radio-button change. `transcribe.bat` reads it via a tiny `get_model.py` helper (avoids `cmd.exe` quoting issues entirely) and writes it via a Python one-liner.

**Tech Stack:** Python 3, tkinter, JSON, Windows batch scripting

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `constants.py` | Modify | Add `MODELS`, `MODEL_KEYS`, `DEFAULT_MODEL` |
| `settings.py` | Create | `load_settings()` / `save_settings()` — sole owner of `settings.json` |
| `get_model.py` | Create | Tiny CLI helper for `transcribe.bat` to read the saved model without `cmd.exe` quoting issues |
| `transcribe.py` | Modify | Load model from settings at startup; update header |
| `recorder.py` | Modify | Remove `MODEL` constant; add radio buttons; read/write model via settings |
| `transcribe.bat` | Modify | Add model-selection menu; pass `%SELECTED_MODEL%` to `--model` |
| `.gitignore` | Modify | Add `settings.json` |

---

### Task 1: Add model constants to `constants.py`

**Files:**
- Modify: `constants.py`

- [ ] **Step 1: Append the three new constants**

Open `constants.py`. After the closing `}` of `PROGRESS_MAP` (line 30), append:

```python

# Model options available for selection
MODELS = [
    ("large-v3-turbo", "Fast   — large-v3-turbo  (recommended)"),
    ("large-v3",       "Best   — large-v3         (max accuracy)"),
    ("medium",         "Light  — medium            (low-end hardware)"),
]
MODEL_KEYS    = [m[0] for m in MODELS]
DEFAULT_MODEL = "large-v3-turbo"
```

- [ ] **Step 2: Verify**

```
.venv\Scripts\python.exe -c "from constants import MODELS, MODEL_KEYS, DEFAULT_MODEL; print(MODEL_KEYS)"
```
Expected: `['large-v3-turbo', 'large-v3', 'medium']`

- [ ] **Step 3: Commit**

```bash
git add constants.py
git commit -m "feat: add MODELS, MODEL_KEYS, DEFAULT_MODEL to constants"
```

---

### Task 2: Create `settings.py`

**Files:**
- Create: `settings.py`

`settings.json` is always resolved relative to `settings.py`'s own directory (`Path(__file__).parent`), never `cwd`. This ensures drag-and-drop and bat invocations behave identically regardless of working directory.

`settings.json` is **never committed to git** — `load_settings()` returns the default when the file is absent, so no seed file is needed.

- [ ] **Step 1: Create the file**

Create `settings.py` in the project root:

```python
import json
from pathlib import Path

from constants import DEFAULT_MODEL

_SETTINGS_PATH = Path(__file__).parent / "settings.json"


def load_settings() -> dict:
    """Read settings.json. Returns defaults if file is missing or malformed."""
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"model": DEFAULT_MODEL}


def save_settings(data: dict) -> None:
    """Write the full settings dict to settings.json."""
    _SETTINGS_PATH.write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
```

- [ ] **Step 2: Verify load with no file present**

Delete `settings.json` if it exists, then run:
```
.venv\Scripts\python.exe -c "from settings import load_settings; print(load_settings())"
```
Expected: `{'model': 'large-v3-turbo'}`
Confirm `settings.json` was NOT created (load does not auto-create).

- [ ] **Step 3: Verify save and reload**

```
.venv\Scripts\python.exe -c "from settings import load_settings, save_settings; save_settings({'model': 'medium'}); print(load_settings())"
```
Expected: `{'model': 'medium'}`
Confirm `settings.json` now contains `{"model": "medium"}`.

- [ ] **Step 4: Verify malformed JSON returns defaults**

```
echo not-json > settings.json
.venv\Scripts\python.exe -c "from settings import load_settings; print(load_settings())"
```
Expected: `{'model': 'large-v3-turbo'}` — no crash.

- [ ] **Step 5: Reset for remaining tasks**

```
del settings.json
```
(`settings.json` must NOT exist as a tracked file — it is gitignored.)

- [ ] **Step 6: Commit**

```bash
git add settings.py
git commit -m "feat: add settings.py with load_settings/save_settings"
```

---

### Task 3: Create `get_model.py`

**Files:**
- Create: `get_model.py`

`transcribe.bat` needs to read the saved model into a `%SELECTED_MODEL%` variable using `for /f`. Embedding a Python `-c` one-liner with dictionary key strings inside `for /f`'s single-quoted command causes unreliable `cmd.exe` quote parsing. A dedicated one-line script avoids this entirely.

- [ ] **Step 1: Create the file**

Create `get_model.py` in the project root:

```python
"""CLI helper for transcribe.bat — prints the saved model name and exits."""
from settings import load_settings
print(load_settings().get("model", "large-v3-turbo"))
```

- [ ] **Step 2: Verify**

```
.venv\Scripts\python.exe get_model.py
```
Expected: `large-v3-turbo` (or whatever is currently in `settings.json` / the default if absent).

- [ ] **Step 3: Commit**

```bash
git add get_model.py
git commit -m "feat: add get_model.py CLI helper for bat scripts"
```

---

### Task 4: Update `transcribe.py`

**Files:**
- Modify: `transcribe.py`

Three changes: add import, replace hardcoded `MODEL` constant with a dynamic load, update the header string. Apply edits using the anchor text shown — do not rely on line numbers since they shift as edits are made.

- [ ] **Step 1: Add the import**

Find this line (currently line 7):
```python
from constants import SUPPRESS, PROGRESS_MAP
```
Replace it with:
```python
from constants import SUPPRESS, PROGRESS_MAP
from settings import load_settings
```

- [ ] **Step 2: Replace the MODEL constant**

Find this line (currently line 13, becomes line 14 after Step 1):
```python
MODEL       = "large-v3-turbo"
```
Replace it with:
```python
MODEL       = load_settings()["model"]
```

- [ ] **Step 3: Update the header string**

Find this line inside `if __name__ == "__main__":`:
```python
    print("   WhisperX Transcriber  |  large-v3-turbo + diarize")
```
Replace it with:
```python
    print(f"   WhisperX Transcriber  |  {MODEL} + diarize")
```

- [ ] **Step 4: Verify**

With no `settings.json` present:
```
.venv\Scripts\python.exe -c "import transcribe; print(transcribe.MODEL)"
```
Expected: `large-v3-turbo`

Then create a settings file with `medium`:
```
.venv\Scripts\python.exe -c "from settings import save_settings; save_settings({'model': 'medium'})"
.venv\Scripts\python.exe -c "import transcribe; print(transcribe.MODEL)"
```
Expected: `medium`

Reset:
```
del settings.json
```

- [ ] **Step 5: Commit**

```bash
git add transcribe.py
git commit -m "feat: load model dynamically from settings in transcribe.py"
```

---

### Task 5: Update `recorder.py`

**Files:**
- Modify: `recorder.py`

Four changes: add imports, remove `MODEL` constant, add radio buttons to the GUI, use `self._model_var.get()` in `_run_transcription`.

**Widget grid layout change:**

| Row | Before | After |
|-----|--------|-------|
| 0 | Name label + entry | Name label + entry |
| 1 | "(optional)" label | "(optional)" label |
| 2 | Record button | Radio buttons (LabelFrame) |
| 3 | Timer | Record button |
| 4 | Status | Timer |
| 5 | — | Status |

Apply all edits using the anchor text shown — do not rely on line numbers since they shift as each edit is made.

- [ ] **Step 1: Add imports**

Find:
```python
from constants import SUPPRESS, PROGRESS_MAP
```
Replace with:
```python
from constants import SUPPRESS, PROGRESS_MAP, MODELS
from settings import load_settings, save_settings
```

- [ ] **Step 2: Remove the hardcoded MODEL constant**

Find and delete this line entirely:
```python
MODEL          = "large-v3-turbo"
```

- [ ] **Step 3: Add model state to `__init__`**

Find this line in `RecorderApp.__init__`:
```python
        self._recorded_duration = "00:00:00"
```
After it, add:
```python
        self._model_var = tk.StringVar(value=load_settings()["model"])
```

- [ ] **Step 4: Add radio buttons widget block**

Find this line in the `# ── Widgets ───` block:
```python
        tk.Label(root, text="(optional)", fg="gray").grid(row=1, column=1, sticky="w", padx=16)
```
After it, add:
```python

        # ── Model selection ───────────────────────────────────────────────────
        model_frame = tk.LabelFrame(root, text="Model", padx=8, pady=4)
        model_frame.grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")

        self._model_radios = []
        for key, label in MODELS:
            rb = tk.Radiobutton(
                model_frame,
                text=label,
                variable=self._model_var,
                value=key,
                command=self._on_model_change,
            )
            rb.pack(anchor="w")
            self._model_radios.append(rb)
```

- [ ] **Step 5: Shift Record button, timer, and status to new row numbers**

Find:
```python
        self._btn.grid(row=2, column=0, columnspan=2, pady=12)
```
Replace with:
```python
        self._btn.grid(row=3, column=0, columnspan=2, pady=12)
```

Find:
```python
                 font=("Courier New", 22)).grid(row=3, column=0, columnspan=2)
```
Replace with:
```python
                 font=("Courier New", 22)).grid(row=4, column=0, columnspan=2)
```

Find:
```python
                 fg="gray", wraplength=280).grid(row=4, column=0, columnspan=2, pady=(4, 12))
```
Replace with:
```python
                 fg="gray", wraplength=280).grid(row=5, column=0, columnspan=2, pady=(4, 12))
```

- [ ] **Step 6: Add `_on_model_change` method**

Add this method to `RecorderApp` after `_set_status`:
```python
    def _on_model_change(self):
        """Persist model selection to settings.json immediately."""
        s = load_settings()
        s["model"] = self._model_var.get()
        save_settings(s)
```

- [ ] **Step 7: Disable radio buttons during transcription**

Find in `_stop_recording`:
```python
        self._btn.config(text="⏺  Record", bg="#4CAF50", state="disabled")
```
After it, add:
```python
        for rb in self._model_radios:
            rb.config(state="disabled")
```

- [ ] **Step 8: Re-enable radio buttons on transcription done**

Find in `_on_transcription_done`:
```python
        self._btn.config(state="normal")
```
After it, add:
```python
        for rb in self._model_radios:
            rb.config(state="normal")
```

- [ ] **Step 9: Use `self._model_var.get()` in `_run_transcription`**

Find in `_run_transcription` inside the `cmd` list:
```python
            "--model", MODEL,
```
Replace with:
```python
            "--model", self._model_var.get(),
```

- [ ] **Step 10: Verify manually**

Launch the recorder:
```
.venv\Scripts\python.exe recorder.py
```
Verify:
- Three radio buttons appear in a "Model" frame between the name field and Record button
- The radio button matching the current `settings.json` model (or `large-v3-turbo` if absent) is pre-selected
- Clicking a different radio button immediately updates `settings.json`:
  ```
  .venv\Scripts\python.exe -c "from settings import load_settings; print(load_settings())"
  ```
- Close and reopen — previously selected model is still selected

- [ ] **Step 11: Commit**

```bash
git add recorder.py
git commit -m "feat: add model radio buttons to recorder GUI with settings persistence"
```

---

### Task 6: Add model-selection menu to `transcribe.bat`

**Files:**
- Modify: `transcribe.bat`

The menu reads the current model by calling `get_model.py` (no quoting issues), displays all three options with `[current]` on the active one, accepts user input, saves the selection via a Python one-liner (single quotes inside the Python string avoid all quoting problems), and passes `%SELECTED_MODEL%` to `--model` in both `whisperx` invocations.

- [ ] **Step 1: Replace `transcribe.bat` entirely**

```bat
@echo off
REM WhisperX Transcription with Diarization
REM Drag and drop an audio/video file onto this bat to transcribe it
REM Optional: drag with a 2nd argument for number of speakers

call :main %*
echo.
echo ============================================
echo Press any key to close this window...
echo ============================================
pause > nul
exit /b

:main
setlocal

set SCRIPT_DIR=%~dp0

if exist "%SCRIPT_DIR%config.bat" (
    call "%SCRIPT_DIR%config.bat"
) else (
    echo ERROR: config.bat not found. Copy config.bat.example to config.bat and fill in your values.
    endlocal
    exit /b 1
)

if defined FFMPEG_BIN set PATH=%FFMPEG_BIN%;%PATH%

echo ============================================
echo  WhisperX Transcriber
echo ============================================
echo.

if "%~1"=="" (
    echo ERROR: No file provided.
    echo.
    echo Usage: Drag and drop an audio/video file onto this bat file.
    echo        Or run: transcribe.bat "C:\path\to\audio.mp3"
    echo        Or run: transcribe.bat "C:\path\to\audio.mp3" 2   (for 2 speakers)
    endlocal
    exit /b 1
)

REM ── Read current model ────────────────────────────────────────────────────────
for /f %%M in ('"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%get_model.py"') do set SELECTED_MODEL=%%M

REM ── Model selection menu ──────────────────────────────────────────────────────
echo   Select model:
if "%SELECTED_MODEL%"=="large-v3-turbo" (
    echo     1^) Fast   -- large-v3-turbo  ^(recommended^)  [current]
) else (
    echo     1^) Fast   -- large-v3-turbo  ^(recommended^)
)
if "%SELECTED_MODEL%"=="large-v3" (
    echo     2^) Best   -- large-v3         ^(max accuracy^)  [current]
) else (
    echo     2^) Best   -- large-v3         ^(max accuracy^)
)
if "%SELECTED_MODEL%"=="medium" (
    echo     3^) Light  -- medium            ^(low-end hardware^)  [current]
) else (
    echo     3^) Light  -- medium            ^(low-end hardware^)
)
echo.

set CHOICE_ATTEMPT=0
:prompt_model
set MODEL_CHOICE=
set /p MODEL_CHOICE=  Enter 1-3 (or press Enter to keep current):

if "%MODEL_CHOICE%"==""      goto :model_selected
if "%MODEL_CHOICE%"=="1" ( set SELECTED_MODEL=large-v3-turbo & goto :save_model )
if "%MODEL_CHOICE%"=="2" ( set SELECTED_MODEL=large-v3       & goto :save_model )
if "%MODEL_CHOICE%"=="3" ( set SELECTED_MODEL=medium         & goto :save_model )

set /a CHOICE_ATTEMPT+=1
if %CHOICE_ATTEMPT% EQU 1 goto :prompt_model
echo   Invalid input. Using current model: %SELECTED_MODEL%
goto :model_selected

:save_model
"%SCRIPT_DIR%.venv\Scripts\python.exe" -c "from settings import load_settings, save_settings; s=load_settings(); s['model']='%SELECTED_MODEL%'; save_settings(s)"

:model_selected
echo.
echo Input file : %~1
echo Output dir : %~dp1
echo Model      : %SELECTED_MODEL%
echo.

set INPUT_FILE=%~1
set NUM_SPEAKERS=%~2

if "%NUM_SPEAKERS%"=="" (
    echo Auto-detecting number of speakers...
    echo.
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m whisperx "%INPUT_FILE%" ^
        --model %SELECTED_MODEL% ^
        --device cuda ^
        --compute_type float16 ^
        --diarize ^
        --output_dir "%~dp1" ^
        --output_format txt
) else (
    echo Using fixed speaker count: %NUM_SPEAKERS%
    echo.
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m whisperx "%INPUT_FILE%" ^
        --model %SELECTED_MODEL% ^
        --device cuda ^
        --compute_type float16 ^
        --diarize ^
        --min_speakers %NUM_SPEAKERS% ^
        --max_speakers %NUM_SPEAKERS% ^
        --output_dir "%~dp1" ^
        --output_format txt
)

set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% NEQ 0 (
    echo ERROR: WhisperX failed with exit code %EXIT_CODE%
) else (
    echo SUCCESS! Output files saved to: %~dp1
)

endlocal
exit /b %EXIT_CODE%
```

- [ ] **Step 2: Verify the menu — Run 1 (test selection saves)**

Run from the project root with no file argument (will error after menu, which is expected):
```
transcribe.bat
```
- Menu displays correctly with `[current]` on the right model
- Enter `2` → menu accepts it, then exits with "ERROR: No file provided"
- Verify `settings.json` now contains `large-v3`:
  ```
  .venv\Scripts\python.exe -c "from settings import load_settings; print(load_settings())"
  ```

- [ ] **Step 3: Verify the menu — Run 2 (test [current] updates)**

Run `transcribe.bat` again with no file:
- `[current]` should now appear next to option 2 (large-v3)
- Press Enter → exits with "ERROR: No file provided" (keeps large-v3, no save)

- [ ] **Step 4: Verify invalid input fallback**

Run `transcribe.bat` again, enter `x` twice:
- Expected output: `Invalid input. Using current model: large-v3`

- [ ] **Step 5: Reset model to default**

```
.venv\Scripts\python.exe -c "from settings import save_settings; save_settings({'model': 'large-v3-turbo'})"
```

- [ ] **Step 6: Commit**

```bash
git add transcribe.bat
git commit -m "feat: add model selection menu to transcribe.bat"
```

---

### Task 7: Update `.gitignore` and final push

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `settings.json` to the user config section**

Find in `.gitignore`:
```
# User config (contains secrets)
config.bat
```
Replace with:
```
# User config (contains secrets and local preferences)
config.bat
settings.json
```

- [ ] **Step 2: Verify `settings.json` is ignored**

```bash
git status
```
`settings.json` must NOT appear in the output (neither tracked nor untracked).

- [ ] **Step 3: Commit and push**

```bash
git add .gitignore
git commit -m "chore: gitignore settings.json (user-local preference file)"
git push
```
