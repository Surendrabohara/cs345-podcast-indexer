"""Part G: Application Insights (OpenTelemetry) setup, metrics, events and a local session log.

init_telemetry() must run FIRST in app.py, before Flask or any Azure SDK is imported.
If APPLICATIONINSIGHTS_CONNECTION_STRING is missing (for example in tests) it prints a
warning and skips Azure Monitor. The metric and span calls below then do nothing.
"""
import os
import statistics
import time

from opentelemetry import metrics, trace

_initialized = False


def init_telemetry() -> bool:
    """Start Application Insights. Returns True if it was started."""
    global _initialized
    if _initialized:
        return True
    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        print("APPLICATIONINSIGHTS_CONNECTION_STRING not set: telemetry is off.")
        return False
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=connection_string)
    _initialized = True
    print("Application Insights initialized.")
    return True


tracer = trace.get_tracer("podcast-indexer")
meter = metrics.get_meter("podcast-indexer")

# Handout G3 metrics
stt_confidence_gauge = meter.create_gauge("stt_confidence")
stt_duration_gauge = meter.create_gauge("stt_duration_seconds")
stt_word_count_gauge = meter.create_gauge("stt_word_count")
entity_count_gauge = meter.create_gauge("language_entity_count")
keyphrase_count_gauge = meter.create_gauge("language_keyphrase_count")
sentiment_gauge = meter.create_gauge("language_sentiment")
tts_char_count_gauge = meter.create_gauge("tts_char_count")
stage_stt_hist = meter.create_histogram("stage_stt_ms")
stage_language_hist = meter.create_histogram("stage_language_ms")
stage_tts_hist = meter.create_histogram("stage_tts_ms")

# Domain metric from the product brief
search_latency_hist = meter.create_histogram("search_latency_ms", unit="ms")

SENTIMENT_NUMBER = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}

session_log: list[dict] = []


def timed_stage(fn, *args, **kwargs):
    """Run fn and return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, (time.perf_counter() - start) * 1000


def emit_pipeline_metrics(stt, language, tts, timings, audio_format):
    attrs = {"audio_format": audio_format, "language": stt["language"]}
    stt_confidence_gauge.set(stt["confidence"], attrs)
    stt_duration_gauge.set(stt["duration_seconds"], attrs)
    stt_word_count_gauge.set(len(stt["transcript"].split()), attrs)
    entity_count_gauge.set(len(language["entities"]), attrs)
    keyphrase_count_gauge.set(len(language["key_phrases"]), attrs)
    sentiment_gauge.set(SENTIMENT_NUMBER.get(language["sentiment"]["label"], 0.0), attrs)
    tts_char_count_gauge.set(tts["char_count"], attrs)
    stage_stt_hist.record(timings["stt_ms"], attrs)
    stage_language_hist.record(timings["language_ms"], attrs)
    stage_tts_hist.record(timings["tts_ms"], attrs)


def emit_pipeline_event(stt, language, audio_format, success=True, error_stage=None, error_msg=None):
    """Recorded as attributes on the current span (see handout G4)."""
    span = trace.get_current_span()
    if success:
        span.set_attribute("event.name", "pipeline_completed")
        span.set_attribute("stt.confidence", stt["confidence"])
        span.set_attribute("stt.language", stt["language"])
        span.set_attribute("entities.count", len(language["entities"]))
        span.set_attribute("sentiment", language["sentiment"]["label"])
        span.set_attribute("audio.format", audio_format)
    else:
        span.set_attribute("event.name", "pipeline_error")
        span.set_attribute("error.stage", error_stage or "unknown")
        span.set_attribute("error.message", error_msg or "")
        span.record_exception(Exception(error_msg or "pipeline error"))


def record_search_latency(latency_ms: float, query_type: str) -> None:
    search_latency_hist.record(latency_ms, {"query_type": query_type})


def log_pipeline_call(stt, language, timings):
    session_log.append({
        "confidence": stt["confidence"],
        "language": stt["language"],
        "entity_count": len(language["entities"]),
        "sentiment": language["sentiment"]["label"],
        "stt_ms": round(timings["stt_ms"], 1),
        "language_ms": round(timings["language_ms"], 1),
        "tts_ms": round(timings["tts_ms"], 1),
    })


def telemetry_summary() -> dict:
    if not session_log:
        return {"message": "No calls yet"}
    confidences = [e["confidence"] for e in session_log]
    stt_times = sorted(e["stt_ms"] for e in session_log)
    p95_index = max(int(len(stt_times) * 0.95) - 1, 0)
    return {
        "total_calls": len(session_log),
        "avg_confidence": round(statistics.mean(confidences), 3),
        "min_confidence": round(min(confidences), 3),
        "p95_stt_ms": round(stt_times[p95_index], 1),
        "sentiment_breakdown": {
            s: sum(1 for e in session_log if e["sentiment"] == s)
            for s in ("positive", "neutral", "negative")
        },
        "calls": session_log[-10:],
    }
