"""Try Parts B and C without the web page:

    python -m indexer.cli my-recordings/01-solo.m4a --title "Glacier basics"
"""
import argparse
from pathlib import Path

from .pipeline import process_audio


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe and analyze one audio file.")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    ep = process_audio(args.audio, args.title or args.audio.stem)
    print(f"Episode {ep['id']}: {ep['title']} ({ep['duration_seconds']} s)")
    print(f"Confidence: {ep['confidence']}  Sentiment: {ep['sentiment']}")
    for seg in ep["segments"]:
        print(f"\n[{mmss(seg['start'])} - {mmss(seg['end'])}]  confidence {seg['confidence']}")
        print(seg["text"])
        print("  people:", ", ".join(seg["people"]) or "-")
        print("  topics:", ", ".join(seg["topics"]) or "-")


if __name__ == "__main__":
    main()
