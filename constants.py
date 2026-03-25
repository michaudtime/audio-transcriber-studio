# Shared constants used by both transcribe.py and recorder.py

# Noise filter — stderr lines containing any of these strings are suppressed
SUPPRESS = (
    "torchcodec", "libtorchcodec", "UserWarning", "warnings.warn",
    "Traceback (most recent call last)", 'File "', "ctypes", "_dlopen",
    "self._handle", "FileNotFoundError", "OSError: Could not load",
    "The above exception", "raise OSError", "torch.ops.load_library",
    "[start of libtorchcodec", "[end of libtorchcodec",
    "Lightning automatically upgraded", "python -m lightning",
    "HF_HUB_DISABLE", "To support symlinks", "huggingface_hub",
    "ReproducibilityWarning", "TensorFloat-32", "torch.backends",
    "pyannote/issues", "Xet Storage", "pip install hf_xet",
    "use audio preloaded", "fix torchcodec installation",
    "FFmpeg is not properly", "FFmpeg version", "versions 4, 5, 6",
    "full-shared", "PyTorch version", "TorchCodec",
    "pyannote\\audio\\core\\io", "  warnings.warn",
    "it might lead to reproducibility", "re-enabled by calling",
    ">>> import torch", ">>> torch.backends",
    "See https://github.com/pyannote",
)

# Friendly labels for key progress lines
PROGRESS_MAP = {
    "Performing voice activity detection": "  [1/4] Voice activity detection...",
    "Performing transcription":            "  [2/4] Transcribing audio...",
    "Performing alignment":                "  [3/4] Aligning words...",
    "Performing diarization":              "  [4/4] Identifying speakers...",
    "Detected language":                   None,  # printed as-is (trimmed)
}
