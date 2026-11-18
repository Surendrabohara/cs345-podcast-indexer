from indexer.segments import build_segments


def phrase(start, end, text="word", confidence=None):
    return {"start": start, "end": end, "text": text, "confidence": confidence}


def test_empty_input_gives_no_segments():
    assert build_segments([]) == []


def test_short_audio_is_one_segment():
    segs = build_segments([phrase(0, 5, "hello", 0.9), phrase(6, 10, "there", 0.8)])
    assert len(segs) == 1
    assert segs[0]["start"] == 0 and segs[0]["end"] == 10
    assert segs[0]["text"] == "hello there"
    assert segs[0]["confidence"] == 0.85


def test_missing_confidence_is_none():
    assert build_segments([phrase(0, 5)])[0]["confidence"] is None


def test_splits_after_target_length():
    phrases = [phrase(i * 10, i * 10 + 9) for i in range(9)]  # 0..89 seconds
    segs = build_segments(phrases, target=30, maximum=60)
    assert len(segs) >= 2
    for seg in segs:
        assert seg["end"] - seg["start"] <= 60


def test_never_exceeds_maximum_when_phrases_are_short():
    phrases = [phrase(i * 5, i * 5 + 4) for i in range(60)]  # 5 minutes
    segs = build_segments(phrases, target=30, maximum=60)
    assert all(s["end"] - s["start"] <= 60 for s in segs)


def test_segments_keep_all_text_in_order():
    phrases = [phrase(i * 10, i * 10 + 9, f"p{i}") for i in range(7)]
    segs = build_segments(phrases)
    joined = " ".join(s["text"] for s in segs).split()
    assert joined == [f"p{i}" for i in range(7)]


def test_one_very_long_phrase_stays_whole():
    segs = build_segments([phrase(0, 90, "long")])
    assert len(segs) == 1
