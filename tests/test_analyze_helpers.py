from indexer.analyze import overall_sentiment, split_text


def test_split_text_keeps_pieces_under_limit():
    text = " ".join(f"This is sentence number {i}." for i in range(400))
    pieces = split_text(text, limit=500)
    assert len(pieces) > 1
    assert all(len(p) <= 500 for p in pieces)
    assert " ".join(pieces).split() == text.split()


def test_split_text_short_text_is_one_piece():
    assert split_text("Hello there. Bye now.") == ["Hello there. Bye now."]


def test_overall_sentiment_averages_segment_scores():
    segs = [
        {"sentiment": {"scores": {"positive": 0.8, "neutral": 0.1, "negative": 0.1}}},
        {"sentiment": {"scores": {"positive": 0.2, "neutral": 0.7, "negative": 0.1}}},
    ]
    out = overall_sentiment(segs)
    assert out["label"] == "positive" and out["confidence"] == 0.5


def test_overall_sentiment_without_scores_is_neutral():
    assert overall_sentiment([{"sentiment": {"scores": None}}])["label"] == "neutral"
