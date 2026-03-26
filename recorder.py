import os
import sys
import threading
import time
import subprocess
import numpy as np
import sounddevice as sd
import soundfile as sf
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime

from constants import SUPPRESS, PROGRESS_MAP, MODELS
from settings import load_settings, save_settings

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR     = Path(__file__).parent
PYTHON_EXE     = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
RECORDINGS_DIR = SCRIPT_DIR / "recordings"
SAMPLE_RATE    = 16000
DEVICE_INDEX   = None   # None = system default mic; set to int for specific device
HF_TOKEN       = os.environ.get("HF_TOKEN", "")
FFMPEG_BIN     = os.environ.get("FFMPEG_BIN", "")


def validate_config():
    """Validate config on startup. Returns error message string or None."""
    if not HF_TOKEN or not HF_TOKEN.startswith("hf_") or HF_TOKEN == "hf_your_token_here":
        return (
            "HF_TOKEN is not set or is still the placeholder value.\n\n"
            "Copy config.bat.example to config.bat and set your Hugging Face token.\n"
            "Get a token at: huggingface.co/settings/tokens"
        )
    return None


class RecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WhisperX Recorder")
        self.root.resizable(False, False)

        # ── State ─────────────────────────────────────────────────────────────
        self._state = "idle"          # idle | recording | saving | transcribing
        self._audio_chunks = []
        self._stream = None
        self._proc = None
        self._stderr_thread = None
        self._stop_event = threading.Event()
        self._record_start = None
        self._recorded_duration = "00:00:00"
        self._model_var = tk.StringVar(value=load_settings()["model"])

        # ── Widgets ───────────────────────────────────────────────────────────
        pad = {"padx": 16, "pady": 6}

        tk.Label(root, text="Name:").grid(row=0, column=0, sticky="e", **pad)
        self._name_var = tk.StringVar()
        self._name_entry = tk.Entry(root, textvariable=self._name_var, width=28)
        self._name_entry.grid(row=0, column=1, **pad)
        tk.Label(root, text="(optional)", fg="gray").grid(row=1, column=1, sticky="w", padx=16)

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

        self._btn = tk.Button(root, text="⏺  Record", width=20,
                              command=self._on_button, bg="#4CAF50", fg="white",
                              font=("Segoe UI", 10, "bold"))
        self._btn.grid(row=3, column=0, columnspan=2, pady=12)

        self._timer_var = tk.StringVar(value="00:00:00")
        tk.Label(root, textvariable=self._timer_var,
                 font=("Courier New", 22)).grid(row=4, column=0, columnspan=2)

        self._status_var = tk.StringVar(value="Idle")
        tk.Label(root, textvariable=self._status_var,
                 fg="gray", wraplength=280).grid(row=5, column=0, columnspan=2, pady=(4, 12))

        # ── Window close ──────────────────────────────────────────────────────
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_button(self):
        if self._state == "idle":
            self._start_recording()
        elif self._state == "recording":
            self._stop_recording()

    def _set_status(self, msg):
        """Thread-safe status update."""
        self.root.after(0, lambda: self._status_var.set(msg))

    def _on_model_change(self):
        """Persist model selection to settings.json immediately."""
        s = load_settings()
        s["model"] = self._model_var.get()
        save_settings(s)

    def _on_close(self):
        if self._state == "recording":
            self._stream.stop()
            self._stream.close()
            self._audio_chunks = []
        elif self._state == "transcribing":
            self._stop_event.set()
            if self._proc:
                self._proc.kill()
            if self._stderr_thread:
                joined = self._stderr_thread.join(timeout=3)
        self.root.destroy()

    def _start_recording(self):
        self._audio_chunks = []
        self._stop_event.clear()
        self._state = "recording"
        self._record_start = time.time()

        # Reset timer at the start of each new recording
        self._timer_var.set("00:00:00")

        self._btn.config(text="⏹  Stop", bg="#f44336")
        self._status_var.set("Recording...")

        def callback(indata, frames, time_info, status):
            self._audio_chunks.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=DEVICE_INDEX,
                callback=callback,
            )
            self._stream.start()
        except Exception as e:
            self._state = "idle"
            self._btn.config(text="⏺  Record", bg="#4CAF50")
            self._status_var.set(f"Error: No microphone found ({e})")
            return

        self._tick_timer()

    def _tick_timer(self):
        if self._state == "recording":
            elapsed = int(time.time() - self._record_start)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self._timer_var.set(f"{h:02d}:{m:02d}:{s:02d}")
            self.root.after(1000, self._tick_timer)

    def _stop_recording(self):
        self._stream.stop()
        self._stream.close()
        self._stream = None
        # Save the final recorded duration before state changes
        self._recorded_duration = self._timer_var.get()
        self._state = "saving"
        self._btn.config(text="⏺  Record", bg="#4CAF50", state="disabled")
        for rb in self._model_radios:
            rb.config(state="disabled")
        self._status_var.set("Saving...")
        self._save_and_transcribe()

    def _build_filename(self):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name = self._name_var.get().strip()
        stem = f"{name}_{ts}" if name else ts
        return stem, RECORDINGS_DIR / f"{stem}.wav"

    def _save_and_transcribe(self):
        if not self._audio_chunks:
            self._state = "idle"
            self._btn.config(state="normal")
            self._status_var.set("Error: No audio recorded")
            return

        audio = np.concatenate(self._audio_chunks, axis=0)

        if audio.size == 0:
            self._state = "idle"
            self._btn.config(state="normal")
            self._status_var.set("Error: No audio recorded (empty buffer)")
            return

        stem, wav_path = self._build_filename()

        try:
            sf.write(str(wav_path), audio, SAMPLE_RATE)
        except OSError as e:
            self._state = "idle"
            self._btn.config(state="normal")
            self._status_var.set(f"Error: Could not save recording ({e})")
            return

        self._state = "transcribing"
        self._status_var.set("Transcribing...")
        self._run_transcription(stem, wav_path)

    def _run_transcription(self, stem, wav_path):
        # Guard against race where window was closed during save
        if self._stop_event.is_set():
            return
        self._stop_event.clear()

        env = os.environ.copy()
        if FFMPEG_BIN:
            env["PATH"] = FFMPEG_BIN + os.pathsep + env["PATH"]
        env["HF_TOKEN"]                        = HF_TOKEN
        env["PYTHONWARNINGS"]                  = "ignore"
        env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

        cmd = [
            str(PYTHON_EXE), "-m", "whisperx", str(wav_path),
            "--model", self._model_var.get(),
            "--device", "cuda",
            "--compute_type", "float16",
            "--diarize",
            "--output_dir", str(RECORDINGS_DIR),
            "--output_format", "txt",
        ]

        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=str(SCRIPT_DIR),
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                env=env,
            )
        except Exception as e:
            self.root.after(0, lambda: self._on_transcription_done(
                stem, wav_path, success=False, error_msg=f"Error: Could not start WhisperX ({e})"
            ))
            return

        def read_stderr():
            try:
                for raw in self._proc.stderr:
                    if self._stop_event.is_set():
                        break
                    line = raw.decode("utf-8", errors="replace").rstrip()
                    if any(p in line for p in SUPPRESS):
                        continue
                    for key, label in PROGRESS_MAP.items():
                        if key in line:
                            if label:
                                self._set_status(label)
                            else:
                                short = line.split(" - ")[-1]
                                self._set_status(f"  Detected: {short}")
                            break
                    else:
                        if line.strip():
                            self._set_status(f"  {line}")

                self._proc.wait()
                rc = self._proc.returncode
                txt_path = RECORDINGS_DIR / f"{stem}.txt"

                if self._stop_event.is_set():
                    return  # window was closed, don't update UI

                if rc == 0 and txt_path.exists():
                    self.root.after(0, lambda: self._on_transcription_done(stem, wav_path, success=True))
                elif rc == 0:
                    self.root.after(0, lambda: self._on_transcription_done(
                        stem, wav_path, success=False,
                        error_msg="Error: Transcription produced no output"
                    ))
                else:
                    self.root.after(0, lambda: self._on_transcription_done(
                        stem, wav_path, success=False,
                        error_msg=f"Error: WhisperX exited with code {rc}"
                    ))
            except Exception as exc:
                if not self._stop_event.is_set():
                    self.root.after(0, lambda: self._on_transcription_done(
                        stem, wav_path, success=False,
                        error_msg=f"Error: Internal transcription error ({exc})"
                    ))

        self._stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        self._stderr_thread.start()

    def _on_transcription_done(self, stem, wav_path, success, error_msg=None):
        self._state = "idle"
        self._proc = None
        self._stderr_thread = None
        self._btn.config(state="normal")
        for rb in self._model_radios:
            rb.config(state="normal")
        # Keep the recorded duration visible rather than resetting to 00:00:00
        self._timer_var.set(self._recorded_duration)
        self._name_var.set("")
        if success:
            self._status_var.set(f"Done! → {stem}.txt")
        else:
            self._status_var.set(error_msg or "Error: Transcription failed")


if __name__ == "__main__":
    err = validate_config()
    if err:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Configuration Error", err)
        root.destroy()
        sys.exit(1)

    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    root = tk.Tk()
    app = RecorderApp(root)
    root.mainloop()
