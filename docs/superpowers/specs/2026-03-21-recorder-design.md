# Recorder Feature Design
**Date:** 2026-03-21
**Project:** WhisperX Transcription Tool (`C:\Users\chadm\whisperx\`)

---

## Overview

Add a GUI-based audio recorder to the existing WhisperX transcription setup. The user runs it on a dedicated transcription machine, records meeting audio through a microphone, and transcription starts automatically when recording stops.

---

## Files

| File | Purpose |
|------|---------|
| `recorder.py` | Main script: GUI, mic recording, auto-transcription |
| `recorder.bat` | Double-click launcher |

`transcribe.py` also receives a minor change: a `if __name__ == "__main__":` guard wrapping its execution block, so `SUPPRESS` and `PROGRESS_MAP` can be safely imported into `recorder.py`.

---

## Configuration

Config block at the top of `recorder.py`:

```python
SCRIPT_DIR     = Path(__file__).parent
PYTHON_EXE     = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
RECORDINGS_DIR = Path(r"C:\Users\chadm\whisperx\recordings")
SAMPLE_RATE    = 16000        # Hz — optimal for WhisperX
DEVICE_INDEX   = None         # None = system default mic; int for specific device
MODEL          = "large-v3-turbo"
HF_TOKEN       = "hf_..."     # copy from transcribe.py
FFMPEG_BIN     = r"C:\..."    # copy from transcribe.py
```

- **`RECORDINGS_DIR`** — created with `mkdir(parents=True, exist_ok=True)` on startup.
- **`DEVICE_INDEX`** — `None` = system default. Run `python -m sounddevice` to list indices.
- **`HF_TOKEN`** — validated on startup: must start with `"hf_"` AND must not equal the literal `"hf_..."`. If invalid, `messagebox.showerror` is shown and the app exits before the main window opens.

---

## Constants Imported from transcribe.py

After the `__main__` guard is added to `transcribe.py`, `recorder.py` imports:

```python
from transcribe import SUPPRESS, PROGRESS_MAP
```

Both files must be kept in sync if either constant changes in the future.

---

## GUI Layout

```
┌─────────────────────────────────┐
│        WhisperX Recorder        │
│                                 │
│  Name: [________________]       │
│         (optional)              │
│                                 │
│         [ ⏺ Record ]            │
│                                 │
│           00:00:00              │
│                                 │
│   Status: Idle                  │
└─────────────────────────────────┘
```

- **Name field** — optional; used in filename if filled, omitted if blank
- **Record button** — becomes red **Stop** while recording; disabled during transcription
- **Timer** — wall-clock elapsed recording time (`time.time()` delta), `HH:MM:SS`, updated every 1000 ms via `tkinter.after()`. Freezes when recording stops and stays frozen through Saving and Transcribing states. Resets to `00:00:00` only when Done or on the next Record press.
- **Status line** — current state / progress message

---

## State Flow

```
Idle
  → [user clicks Record]
Recording...
  → [user clicks Stop]
Saving...           (main thread; synchronous — typically <1 second)
  → [.wav written to disk]
Transcribing...     (Record button disabled)
  → [WhisperX exits 0 AND .txt exists]
Done! → <filename>.txt
  → [button re-enables, timer resets, name field cleared]

  → [any error at any stage]
Error: <message>    (button re-enables, returns to Idle)
```

**Window close behavior:**

| State | Behavior |
|-------|----------|
| Idle | Close immediately |
| Recording | Discard in-memory buffer (no file written); close |
| Saving | `soundfile.write()` is synchronous in the main thread; window close waits for it naturally (fast) |
| Transcribing | Set stop event → `proc.terminate()` → join stderr thread → close. `.wav` kept on disk. |

---

## Recording

- **Library:** `sounddevice.InputStream` with a callback
- **Accumulation:** callback appends `numpy` chunks to an in-memory list; `numpy.concatenate()` on stop
- **Format:** `dtype='int16'`, `channels=1`, `samplerate=SAMPLE_RATE`
- **Device:** `DEVICE_INDEX` (default `None`)
- **Memory:** ~115 MB/hour; no hard limit; documented for awareness

---

## File Saving

Runs synchronously in the main thread immediately after recording stops.

**Filename format:** `%Y-%m-%d_%H-%M-%S`

| Name field | Filename |
|------------|----------|
| Filled ("standup") | `standup_2026-03-21_14-30-00.wav` |
| Blank | `2026-03-21_14-30-00.wav` |

Same-name files silently overwritten (timestamp-to-second collision is extremely unlikely).

`soundfile.write()` wrapped in `try/except OSError`. On failure → `Error: Could not save recording` → Idle.

---

## Auto-Transcription

Runs in a **background thread** immediately after the `.wav` is saved.

**Thread safety:** a `threading.Event` (`_stop_event`) is used for coordination:
- The stderr reader loop checks `_stop_event` between lines and exits if set
- On window close during Transcribing: `_stop_event.set()` → `proc.terminate()` → `thread.join(timeout=5)` → window closes
- All tkinter widget updates from the thread use `root.after(0, callback)` — never direct calls

**Subprocess:**
```python
env = os.environ.copy()
env["PATH"]                            = FFMPEG_BIN + os.pathsep + env["PATH"]
env["PYTHONWARNINGS"]                  = "ignore"
env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

proc = subprocess.Popen(
    [str(PYTHON_EXE), "-m", "whisperx", str(wav_path),
     "--model", MODEL, "--device", "cuda", "--compute_type", "float16",
     "--diarize", "--hf_token", HF_TOKEN,
     "--output_dir", str(RECORDINGS_DIR), "--output_format", "txt"],
    stderr=subprocess.PIPE,
    stdout=subprocess.DEVNULL,
    env=env,
)
```

**Stderr handling:** reads `proc.stderr` line by line. For each line:
1. If `_stop_event` is set → exit loop
2. If any `SUPPRESS` substring matches → skip
3. If any `PROGRESS_MAP` key matches → dispatch friendly label to status
4. Otherwise → dispatch line verbatim to status (same behavior as `transcribe.py`)

**On completion:**
- Exit code 0 AND `RECORDINGS_DIR / f"{stem}.txt"` exists → `Done! → <stem>.txt`; timer resets; button re-enables
- Exit code 0 but `.txt` missing → `Error: Transcription produced no output`; Idle
- Non-zero exit code → `Error: WhisperX exited with code N`; Idle

---

## Error Handling Summary

| Scenario | Status / behavior | State after |
|----------|-------------------|-------------|
| HF_TOKEN invalid on startup | `messagebox.showerror`, app exits | — |
| Mic not found / sounddevice init fails | `Error: No microphone found` | Idle |
| Window closed during Recording | Buffer discarded, no file written | Closed |
| Window closed during Saving | Wait for synchronous write; close | Closed |
| Disk full on save (`OSError`) | `Error: Could not save recording` | Idle |
| WhisperX exits 0, `.txt` exists | `Done! → <stem>.txt` | Idle/ready |
| WhisperX exits 0, no `.txt` | `Error: Transcription produced no output` | Idle |
| WhisperX non-zero exit | `Error: WhisperX exited with code N` | Idle |
| Window closed during Transcribing | `_stop_event` + `proc.terminate()`; `.wav` kept | Closed |

---

## Change to transcribe.py

Wrap the execution block in a `__main__` guard so `SUPPRESS` and `PROGRESS_MAP` can be imported:

```python
if __name__ == "__main__":
    # ... all existing code below the constant definitions ...
```

`SUPPRESS` and `PROGRESS_MAP` remain at module level, above the guard.

---

## Dependencies

```
sounddevice   # mic capture
soundfile     # wav writing
```

```
.venv\Scripts\pip install sounddevice soundfile
```

---

## recorder.bat

```bat
@echo off
cd /d %~dp0
.venv\Scripts\python.exe recorder.py
pause
```

`recorder.py` handles all PATH and env injection internally, so the bat file only needs to set the working directory and launch the correct Python executable.
