"""Local search over the stored segments.

This is a simple stand-in so the app works on localhost for the checkpoint.
Track 1 replaces it with Azure AI Search. The function signature stays the same.
"""
import re
import time


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def search_segments(
    episodes: list[dict],
    q: str = "",
    person: str | None = None,
    topic: str | None = None,
    episode: str | None = None,
) -> dict:
    started = time.perf_counter()
    terms = _words(q)
    hits = []

    for ep in episodes:
        if episode and ep["id"] != episode:
            continue
        for seg in ep["segments"]:
            people = [p.lower() for p in seg.get("people", [])]
            topics = [t.lower() for t in seg.get("topics", [])]
            if person and person.lower() not in people:
                continue
            if topic and topic.lower() not in topics:
                continue

            score = 0
            if terms:
                text_words = _words(seg["text"])
                people_words = [w for p in people for w in _words(p)]
                topic_words = [w for t in topics for w in _words(t)]
                for term in terms:
                    score += text_words.count(term)
                    score += 2 * people_words.count(term)
                    score += 2 * topic_words.count(term)
                if score == 0:
                    continue
            hits.append({
                "episode_id": ep["id"],
                "episode_title": ep["title"],
                "start_sec": seg["start"],
                "end_sec": seg["end"],
                "text": seg["text"],
                "people": seg.get("people", []),
                "topics": seg.get("topics", []),
                "score": score,
            })

    hits.sort(key=lambda h: (-h["score"], h["episode_title"], h["start_sec"]))
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    return {"results": hits, "latency_ms": latency_ms}
