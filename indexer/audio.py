"""Audio input step: turn any file into WAV, 16 kHz, 16-bit, mono (what Speech expects)."""
import shutil
import subprocess
import wave
from pathlib import Path


class UnsupportedAudioError(RuntimeError):
    """The file is not audio we can read. The API turns this into HTTP 415."""


def convert_to_wav(src: Path, dst: Path) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found. On a Mac, install it with: brew install ffmpeg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-ac", "1",            # mono
        "-ar", "16000",        # 16 kHz
        "-sample_fmt", "s16",  # 16-bit
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise UnsupportedAudioError("The file could not be read as audio.")
    return dst


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())
