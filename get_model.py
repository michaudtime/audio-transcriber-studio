"""CLI helper for transcribe.bat — prints the saved model name and exits."""
from settings import load_settings
print(load_settings().get("model", "large-v3-turbo"))
