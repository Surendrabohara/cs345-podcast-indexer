"""The whole ingest path: audio file -> WAV -> timed text -> segments -> people, topics, sentiment.

Audio is never kept. The converted WAV lives in a temporary folder that is deleted afterwards.
"""
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .analyze import analyze_segments, overall_sentiment
from .audio import convert_to_wav, wav_duration_seconds
from .segments import build_segments
from .store import save_episode
from .transcribe import to_transcript, transcribe_file


def transcribe_only(src_path: Path, language: str = "en-US") -> dict:
    """For POST /transcribe: the B2 JSON for one file."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = convert_to_wav(Path(src_path), Path(tmp) / "audio.wav")
        duration = wav_duration_seconds(wav)
        phrases = transcribe_file(wav, language=language)
    return to_transcript(phrases, language, duration)


def process_audio(src_path: Path, title: str, language: str = "en-US") -> dict:
    """For POST /process: transcribe, split into segments, analyze, store."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = convert_to_wav(Path(src_path), Path(tmp) / "audio.wav")
        duration = wav_duration_seconds(wav)
        phrases = transcribe_file(wav, language=language)

    transcript = to_transcript(phrases, language, duration)
    segments = build_segments(phrases)
    analyze_segments(segments, language=language.split("-")[0])

    all_entities = [e for s in segments for e in s["entities"]]
    all_topics = sorted({t for s in segments for t in s["topics"]})
    episode = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "language": language,
        "duration_seconds": transcript["duration_seconds"],
        "confidence": transcript["confidence"],
        "transcript": transcript["transcript"],
        "sentiment": overall_sentiment(segments),
        "entity_count": len(all_entities),
        "keyphrase_count": len(all_topics),
        "segments": segments,
    }
    save_episode(episode)
    return episode
