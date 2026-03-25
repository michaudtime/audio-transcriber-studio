import subprocess
import sys
import os
import threading
from pathlib import Path

from constants import SUPPRESS, PROGRESS_MAP
from settings import load_settings

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
PYTHON_EXE  = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
HF_TOKEN    = os.environ.get("HF_TOKEN", "")
MODEL       = load_settings()["model"]
FFMPEG_BIN  = os.environ.get("FFMPEG_BIN", "")

AUDIO_EXTS = (
    "*.mp3", "*.mp4", "*.wav", "*.m4a", "*.mkv",
    "*.avi", "*.mov", "*.flac", "*.ogg", "*.wma", "*.aac", "*.webm"
)


if __name__ == "__main__":
    # Inject FFmpeg into PATH for this process
    if FFMPEG_BIN:
        os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ["PATH"]

    # ── Header ────────────────────────────────────────────────────────────────
    print("=" * 55)
    print(f"   WhisperX Transcriber  |  {MODEL} + diarize")
    print("=" * 55)
    print()

    # ── Get audio file ────────────────────────────────────────────────────────
    if len(sys.argv) > 1:
        # Called with a file argument (drag-and-drop or CLI)
        audio_file = Path(sys.argv[1])
    else:
        # No argument — open a file picker dialog
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)

            chosen = filedialog.askopenfilename(
                title="Select audio or video file to transcribe",
                filetypes=[
                    ("Audio / Video", " ".join(AUDIO_EXTS)),
                    ("All files", "*.*"),
                ],
            )
            root.destroy()

            if not chosen:
                print("No file selected. Exiting.")
                input("\nPress Enter to close...")
                sys.exit(0)

            audio_file = Path(chosen)

        except Exception as exc:
            print(f"Could not open file dialog: {exc}")
            print()
            print("Usage: transcribe.py <audio_file>")
            input("\nPress Enter to close...")
            sys.exit(1)

    # ── Validate ──────────────────────────────────────────────────────────────
    if not audio_file.exists():
        print(f"ERROR: File not found:\n  {audio_file}")
        input("\nPress Enter to close...")
        sys.exit(1)

    output_dir = audio_file.parent

    print(f"  Input  : {audio_file.name}")
    print(f"  Output : {output_dir}")
    print(f"  Model  : {MODEL}  |  Speakers: auto-detect")
    print()
    print("Starting transcription... (this may take a minute)")
    print("-" * 55)

    def stream_stderr(proc):
        """Read subprocess stderr, suppress noise, show clean progress."""
        for raw in proc.stderr:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if any(p in line for p in SUPPRESS):
                continue
            # Map verbose log lines to friendly labels
            matched = False
            for key, label in PROGRESS_MAP.items():
                if key in line:
                    if label:
                        print(label, flush=True)
                    else:
                        # e.g. "Detected language: english (0.99)"
                        short = line.split(" - ")[-1]
                        print(f"  Detected: {short}", flush=True)
                    matched = True
                    break
            if not matched and line.strip():
                print(f"  {line}", flush=True)

    # ── Run WhisperX ──────────────────────────────────────────────────────────
    cmd = [
        str(PYTHON_EXE), "-m", "whisperx",
        str(audio_file),
        "--model", MODEL,
        "--device", "cuda",
        "--compute_type", "float16",
        "--diarize",
        "--output_dir", str(output_dir),
        "--output_format", "txt",
    ]

    env = os.environ.copy()
    env["HF_TOKEN"]                        = HF_TOKEN
    env["PYTHONWARNINGS"]                  = "ignore"
    env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    proc = subprocess.Popen(
        cmd,
        cwd=str(SCRIPT_DIR),
        stderr=subprocess.PIPE,
        env=env,
    )

    t = threading.Thread(target=stream_stderr, args=(proc,), daemon=True)
    t.start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nInterrupted — stopping transcription...")
        proc.kill()
        proc.wait()
        t.join()
        print("Stopped.")
        sys.exit(1)

    t.join()

    result = proc

    # ── Result ────────────────────────────────────────────────────────────────
    print("-" * 55)
    print()
    if result.returncode == 0:
        print("SUCCESS!  Output files saved to:")
        print(f"  {output_dir}")
        print()
        out = output_dir / f"{audio_file.stem}.txt"
        if out.exists():
            print(f"    {out.name}")
    else:
        print(f"ERROR: WhisperX exited with code {result.returncode}")

    print()
    input("Press Enter to close...")
