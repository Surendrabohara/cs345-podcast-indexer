"""The whole ingest path: audio file -> WAV -> timed text -> segments -> people, topics, sentiment.

Audio is never kept. The converted WAV lives in a temporary folder that is deleted afterwards.
"""
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .analyze import analyze_segments, overall_sentiment
from .audio import NoSpeechError, convert_to_wav, wav_duration_seconds
from .segments import build_segments
from .store import save_episode
from .telemetry import (
    emit_pipeline_event, emit_pipeline_metrics, log_pipeline_call, timed_stage, tracer,
)
from .tts import DEFAULT_VOICE, build_summary, synthesize
from .transcribe import to_transcript, transcribe_file


def transcribe_only(src_path: Path, language: str = "en-US") -> dict:
    """For POST /transcribe: the B2 JSON for one file."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = convert_to_wav(Path(src_path), Path(tmp) / "audio.wav")
        duration = wav_duration_seconds(wav)
        phrases = transcribe_file(wav, language=language)
    return to_transcript(phrases, language, duration)


def process_audio(src_path: Path, title: str, language: str = "en-US", voice: str = DEFAULT_VOICE) -> dict:
    """For POST /process: transcribe, analyze, speak a summary, store.

    Three traced stages: speech_to_text, language_analysis, text_to_speech (handout G5).
    """
    audio_format = Path(src_path).suffix.lstrip(".").lower() or "unknown"

    with tracer.start_as_current_span("pipeline.process") as root_span:
        root_span.set_attribute("audio.format", audio_format)
        stage = "speech_to_text"
        try:
            # Stage 1: speech to text
            with tracer.start_as_current_span("stage.speech_to_text") as stt_span:
                def stt_stage():
                    with tempfile.TemporaryDirectory() as tmp:
                        wav = convert_to_wav(Path(src_path), Path(tmp) / "audio.wav")
                        duration = wav_duration_seconds(wav)
                        phrases = transcribe_file(wav, language=language)
                    return phrases, to_transcript(phrases, language, duration)

                (phrases, transcript), stt_ms = timed_stage(stt_stage)
                if not phrases or not transcript["transcript"].strip():
                    raise NoSpeechError("No speech was detected in this recording. Try again and speak clearly.")
                stt_span.set_attribute("stt.confidence", transcript["confidence"])
                stt_span.set_attribute("stt.word_count", len(transcript["transcript"].split()))
                stt_span.set_attribute("duration_ms", stt_ms)

            # Stage 2: language analysis
            stage = "language_analysis"
            with tracer.start_as_current_span("stage.language_analysis") as lang_span:
                def language_stage():
                    segments = build_segments(phrases)
                    analyze_segments(segments, language=language.split("-")[0])
                    return segments

                segments, lang_ms = timed_stage(language_stage)
                entities = [e for s in segments for e in s["entities"]]
                topics = sorted({t for s in segments for t in s["topics"]})
                sentiment = overall_sentiment(segments)
                lang_span.set_attribute("entity_count", len(entities))
                lang_span.set_attribute("sentiment", sentiment["label"])
                lang_span.set_attribute("duration_ms", lang_ms)

            episode = {
                "id": uuid.uuid4().hex[:8],
                "title": title,
                "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "language": language,
                "duration_seconds": transcript["duration_seconds"],
                "confidence": transcript["confidence"],
                "transcript": transcript["transcript"],
                "sentiment": sentiment,
                "entity_count": len(entities),
                "keyphrase_count": len(topics),
                "segments": segments,
            }
            save_episode(episode)

            # Stage 3: text to speech (a spoken summary of the result)
            stage = "text_to_speech"
            with tracer.start_as_current_span("stage.text_to_speech") as tts_span:
                def tts_stage():
                    summary = build_summary(title, topics, sentiment["label"], entities)
                    return summary, synthesize(summary, voice)

                (summary, tts_result), tts_ms = timed_stage(tts_stage)
                tts_span.set_attribute("char_count", tts_result["char_count"])
                tts_span.set_attribute("duration_ms", tts_ms)

            language_result = {"entities": entities, "key_phrases": topics, "sentiment": sentiment}
            timings = {"stt_ms": stt_ms, "language_ms": lang_ms, "tts_ms": tts_ms}
            emit_pipeline_metrics(transcript, language_result, tts_result, timings, audio_format)
            emit_pipeline_event(transcript, language_result, audio_format)
            log_pipeline_call(transcript, language_result, timings)
        except Exception as err:
            emit_pipeline_event({}, {}, audio_format, success=False, error_stage=stage, error_msg=str(err))
            raise

    return {**episode, "summary_text": summary, **tts_result}
