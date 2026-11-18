"""Group timed phrases into segments of about 30 to 60 seconds.

One segment is one search document later. Short segments let a search land on
the exact moment, and keep every piece of text small for the Language service.
"""


def build_segments(phrases: list[dict], target: float = 30.0, maximum: float = 60.0) -> list[dict]:
    segments: list[dict] = []
    current: dict | None = None

    for p in phrases:
        if current is None:
            current = _new(p)
            continue

        length_now = current["end"] - current["start"]
        length_if_added = p["end"] - current["start"]
        if length_now >= target or length_if_added > maximum:
            segments.append(_finish(current))
            current = _new(p)
        else:
            current["end"] = p["end"]
            current["parts"].append(p["text"])
            if p.get("confidence") is not None:
                current["confs"].append(p["confidence"])

    if current is not None:
        segments.append(_finish(current))
    return segments


def _new(p: dict) -> dict:
    confs = [p["confidence"]] if p.get("confidence") is not None else []
    return {"start": p["start"], "end": p["end"], "parts": [p["text"]], "confs": confs}


def _finish(current: dict) -> dict:
    confs = current["confs"]
    return {
        "start": current["start"],
        "end": current["end"],
        "text": " ".join(current["parts"]),
        "confidence": round(sum(confs) / len(confs), 3) if confs else None,
    }
