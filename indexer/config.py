"""Settings read from environment variables (or a local .env file).

Variable names follow the course handout (Part A).
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
EPISODE_DIR = DATA_DIR / "episodes"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # handout: max 25 MB
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".webm", ".flac"}


@dataclass(frozen=True)
class Settings:
    speech_key: str = os.getenv("AZURE_SPEECH_KEY", "")
    speech_region: str = os.getenv("AZURE_SPEECH_REGION", "")
    language_key: str = os.getenv("AZURE_LANGUAGE_KEY", "")
    language_endpoint: str = os.getenv("AZURE_LANGUAGE_ENDPOINT", "")
    appinsights_connection_string: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")


settings = Settings()


def require(*names: str) -> None:
    """Stop early with a clear message if a setting is missing."""
    missing = [n for n in names if not getattr(settings, n)]
    if missing:
        env_names = ", ".join(_env_name(n) for n in missing)
        raise RuntimeError(
            f"Missing setting(s): {env_names}. Copy .env.example to .env and fill them in."
        )


def _env_name(field: str) -> str:
    return {
        "speech_key": "AZURE_SPEECH_KEY",
        "speech_region": "AZURE_SPEECH_REGION",
        "language_key": "AZURE_LANGUAGE_KEY",
        "language_endpoint": "AZURE_LANGUAGE_ENDPOINT",
        "appinsights_connection_string": "APPLICATIONINSIGHTS_CONNECTION_STRING",
    }[field]
