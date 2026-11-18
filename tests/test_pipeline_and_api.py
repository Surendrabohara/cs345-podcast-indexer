"""Checks the code around Azure. Speech and Language are replaced by fakes, so no keys are needed."""
import io
import wave
from pathlib import Path

import pytest

from indexer import main, pipeline, store
from indexer.transcribe import to_transcript


def fake_convert(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000 * 3)  # 3 seconds of silence
    return dst


def fake_transcribe(wav_path, language="en-US"):
    return [
        {"start": 0.0, "end": 2.0, "text": "Maya Ortiz studies glacier melt.", "confidence": 0.9,
         "words": [{"word": "Maya", "offset": 0.0, "duration": 0.3, "confidence": 0.95}]},
        {"start": 2.2, "end": 3.0, "text": "It affects river water.", "confidence": 0.8, "words": []},
    ]


def fake_analyze(segments, language="en"):
    for s in segments:
        s["entities"] = [{"text": "Maya Ortiz", "category": "Person", "confidence": 0.99}] if "Maya" in s["text"] else []
        s["people"] = ["Maya Ortiz"] if "Maya" in s["text"] else []
        s["topics"] = ["glacier melt"]
        s["sentiment"] = {"label": "neutral", "confidence": 0.7,
                          "scores": {"positive": 0.1, "neutral": 0.7, "negative": 0.2}}
    return segments


@pytest.fixture()
def fakes(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "convert_to_wav", fake_convert)
    monkeypatch.setattr(pipeline, "transcribe_file", fake_transcribe)
    monkeypatch.setattr(pipeline, "analyze_segments", fake_analyze)
    monkeypatch.setattr(pipeline, "save_episode", lambda ep: store.save_episode(ep, tmp_path / "eps"))
    monkeypatch.setattr(main, "list_episodes", lambda: store.list_episodes(tmp_path / "eps"))
    monkeypatch.setattr(main, "load_episode", lambda i: store.load_episode(i, tmp_path / "eps"))
    monkeypatch.setattr(main, "analyze_text", lambda text: {
        "key_phrases": ["glacier melt"], "entities": [], "sentiment": {"label": "neutral", "confidence": 0.7}})
    return tmp_path


def upload(client, filename="clip.m4a", title="Glacier basics", path="/process"):
    return client.post(
        path,
        data={"audio": (io.BytesIO(b"not real audio"), filename), "title": title},
        content_type="multipart/form-data",
    )


def test_to_transcript_has_the_fields_the_handout_asks_for():
    phrases = fake_transcribe(None)
    out = to_transcript(phrases, "en-US", 3.0)
    assert set(["transcript", "language", "duration_seconds", "confidence", "words"]) <= set(out)
    assert out["transcript"].startswith("Maya Ortiz")
    assert 0.8 < out["confidence"] < 0.9  # weighted toward the longer, more confident phrase


def test_pipeline_builds_and_saves_an_episode(fakes):
    ep = pipeline.process_audio(Path("whatever.m4a"), "Glacier basics")
    assert ep["title"] == "Glacier basics"
    assert ep["duration_seconds"] == 3.0
    assert ep["sentiment"]["label"] == "neutral"
    assert ep["entity_count"] == 1
    assert ep["segments"][0]["people"] == ["Maya Ortiz"]
    assert store.load_episode(ep["id"], fakes / "eps")["title"] == "Glacier basics"


def test_process_episodes_and_search(fakes):
    client = main.app.test_client()
    assert client.get("/health").get_json() == {"status": "ok"}

    res = upload(client)
    assert res.status_code == 201
    body = res.get_json()
    for key in ("transcript", "language", "duration_seconds", "confidence", "sentiment", "segments"):
        assert key in body

    assert len(client.get("/episodes").get_json()) == 1
    assert client.get(f"/episodes/{body['id']}").status_code == 200
    assert client.get("/episodes/missing").status_code == 404

    found = client.get("/search?q=glacier").get_json()
    assert len(found["results"]) == 1 and "latency_ms" in found
    assert len(client.get("/search?person=Maya Ortiz").get_json()["results"]) == 1


def test_transcribe_returns_handout_json(fakes):
    res = upload(main.app.test_client(), path="/transcribe")
    assert res.status_code == 200
    assert "words" in res.get_json() and "confidence" in res.get_json()


def test_analyze_needs_text(fakes):
    client = main.app.test_client()
    assert client.post("/analyze", json={}).status_code == 400
    ok = client.post("/analyze", json={"text": "Glacier melt matters."})
    assert ok.status_code == 200 and "key_phrases" in ok.get_json()


def test_missing_file_is_400(fakes):
    assert main.app.test_client().post("/process", data={"title": "x"}).status_code == 400


def test_unsupported_file_type_is_415(fakes):
    res = upload(main.app.test_client(), filename="notes.txt")
    assert res.status_code == 415


def test_unreadable_audio_is_415(fakes, monkeypatch):
    from indexer.audio import UnsupportedAudioError

    def broken(src, dst):
        raise UnsupportedAudioError("The file could not be read as audio.")

    monkeypatch.setattr(pipeline, "convert_to_wav", broken)
    assert upload(main.app.test_client()).status_code == 415


def test_file_over_25mb_is_413(fakes, monkeypatch):
    monkeypatch.setitem(main.app.config, "MAX_CONTENT_LENGTH", 100)
    big = main.app.test_client().post(
        "/process",
        data={"audio": (io.BytesIO(b"x" * 1000), "big.wav")},
        content_type="multipart/form-data",
    )
    assert big.status_code == 413
