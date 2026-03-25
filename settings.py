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
