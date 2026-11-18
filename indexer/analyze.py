"""Part C: Azure AI Language. Key phrases, named entities and sentiment."""
import re

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

from .config import require, settings

# Documents allowed per request (synchronous API).
NER_BATCH = 5
KEY_PHRASE_BATCH = 10
SENTIMENT_BATCH = 10
MAX_TOPICS_PER_SEGMENT = 5
CHUNK_CHARS = 4000  # keeps each document small for /analyze


def _client() -> TextAnalyticsClient:
    require("language_key", "language_endpoint")
    return TextAnalyticsClient(
        endpoint=settings.language_endpoint,
        credential=AzureKeyCredential(settings.language_key),
    )


def _unique(items):
    seen, out = set(), []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def analyze_segments(segments: list[dict], language: str = "en") -> list[dict]:
    """Add entities, people, topics and sentiment to each segment. Returns the same list."""
    client = _client()
    texts = [s["text"] for s in segments]
    n = len(texts)
    entities = [[] for _ in range(n)]
    topics = [[] for _ in range(n)]
    sentiments = [{"label": "neutral", "confidence": None, "scores": None} for _ in range(n)]

    for i in range(0, n, NER_BATCH):
        for j, res in enumerate(client.recognize_entities(texts[i:i + NER_BATCH], language=language)):
            if not res.is_error:
                entities[i + j] = [
                    {"text": e.text, "category": e.category, "confidence": round(e.confidence_score, 3)}
                    for e in res.entities
                ]

    for i in range(0, n, KEY_PHRASE_BATCH):
        for j, res in enumerate(client.extract_key_phrases(texts[i:i + KEY_PHRASE_BATCH], language=language)):
            if not res.is_error:
                topics[i + j] = _unique(p.lower() for p in res.key_phrases)[:MAX_TOPICS_PER_SEGMENT]

    for i in range(0, n, SENTIMENT_BATCH):
        for j, res in enumerate(client.analyze_sentiment(texts[i:i + SENTIMENT_BATCH], language=language)):
            if not res.is_error:
                s = res.confidence_scores
                scores = {"positive": s.positive, "neutral": s.neutral, "negative": s.negative}
                label = res.sentiment if res.sentiment in scores else max(scores, key=scores.get)
                sentiments[i + j] = {"label": label, "confidence": round(scores[label], 3), "scores": scores}

    for seg, ents, tops, sent in zip(segments, entities, topics, sentiments):
        seg["entities"] = ents
        seg["people"] = _unique(e["text"] for e in ents if e["category"] == "Person")
        seg["topics"] = tops
        seg["sentiment"] = sent
    return segments


def overall_sentiment(segments: list[dict]) -> dict:
    """One label for the whole recording: average the segment scores, take the highest."""
    scored = [s["sentiment"]["scores"] for s in segments if s.get("sentiment", {}).get("scores")]
    if not scored:
        return {"label": "neutral", "confidence": None}
    avg = {k: sum(s[k] for s in scored) / len(scored) for k in ("positive", "neutral", "negative")}
    label = max(avg, key=avg.get)
    return {"label": label, "confidence": round(avg[label], 3)}


def split_text(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Split long text at sentence ends so each piece stays under `limit` characters."""
    chunks, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if current and len(current) + len(sentence) + 1 > limit:
            chunks.append(current)
            current = ""
        current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def analyze_text(text: str, language: str = "en") -> dict:
    """For POST /analyze: key phrases, entities and sentiment for one piece of text."""
    pieces = [{"text": t} for t in split_text(text)]
    analyze_segments(pieces, language=language)
    return {
        "key_phrases": _unique(p for piece in pieces for p in piece["topics"]),
        "entities": [e for piece in pieces for e in piece["entities"]],
        "sentiment": overall_sentiment(pieces),
    }
