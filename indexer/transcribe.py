"""Part B: continuous speech recognition. Returns timed phrases with confidence."""
import json
import threading
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk

from .config import require, settings

TICKS_PER_SECOND = 10_000_000  # Speech reports time in 100-nanosecond ticks


def transcribe_file(wav_path: Path, language: str = "en-US", timeout_s: int = 900) -> list[dict]:
    """Recognize a whole file with continuous recognition.

    Each phrase is {"start", "end", "text", "confidence", "words"}; times are in seconds.
    """
    require("speech_key", "speech_region")
    speech_config = speechsdk.SpeechConfig(
        subscription=settings.speech_key, region=settings.speech_region
    )
    speech_config.speech_recognition_language = language
    speech_config.output_format = speechsdk.OutputFormat.Detailed  # adds confidence
    speech_config.request_word_level_timestamps()
    audio_config = speechsdk.audio.AudioConfig(filename=str(wav_path))
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    phrases: list[dict] = []
    errors: list[str] = []
    done = threading.Event()  # the SDK is event driven: we must wait for it (handout, Pitfall 3)

    def on_recognized(evt):
        # "Recognized" = the final text for one phrase ("Recognizing" is only a draft).
        result = evt.result
        if result.reason == speechsdk.ResultReason.RecognizedSpeech and result.text:
            start = result.offset / TICKS_PER_SECOND
            end = start + result.duration / TICKS_PER_SECOND
            confidence, words = _read_details(result)
            phrases.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "text": result.text,
                "confidence": confidence,
                "words": words,
            })

    def on_canceled(evt):
        # End of file also arrives as a cancel. Only a real error matters.
        if evt.reason == speechsdk.CancellationReason.Error:
            errors.append(f"{evt.error_code}: {evt.error_details}")
        done.set()

    recognizer.recognized.connect(on_recognized)
    recognizer.session_stopped.connect(lambda evt: done.set())
    recognizer.canceled.connect(on_canceled)

    recognizer.start_continuous_recognition()
    finished = done.wait(timeout=timeout_s)
    recognizer.stop_continuous_recognition()

    if errors:
        raise RuntimeError(f"Speech recognition failed: {errors[0]}")
    if not finished:
        raise RuntimeError("Speech recognition timed out.")
    return phrases


def _read_details(result):
    """Pull confidence and word timings out of the detailed JSON. Missing parts become None."""
    try:
        best = json.loads(result.json)["NBest"][0]
    except (ValueError, KeyError, IndexError, TypeError):
        return None, []
    words = []
    for w in best.get("Words", []):
        words.append({
            "word": w.get("Word"),
            "offset": round(w.get("Offset", 0) / TICKS_PER_SECOND, 2),
            "duration": round(w.get("Duration", 0) / TICKS_PER_SECOND, 2),
            "confidence": w.get("Confidence"),
        })
    return best.get("Confidence"), words


def to_transcript(phrases: list[dict], language: str, duration_seconds: float) -> dict:
    """The JSON shape the handout asks for in B2."""
    total = sum(p["end"] - p["start"] for p in phrases)
    scored = [(p["end"] - p["start"], p["confidence"]) for p in phrases if p.get("confidence") is not None]
    weight = sum(w for w, _ in scored)
    confidence = round(sum(w * c for w, c in scored) / weight, 3) if weight else None
    return {
        "transcript": " ".join(p["text"] for p in phrases),
        "language": language,
        "duration_seconds": round(duration_seconds, 1),
        "confidence": confidence,
        "words": [w for p in phrases for w in p.get("words", [])],
        "speech_seconds": round(total, 1),
    }
