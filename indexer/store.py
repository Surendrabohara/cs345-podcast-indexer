"""Local storage: one JSON file per episode in data/episodes/.

These files are the source of truth. The search index can always be rebuilt from them.
"""
import json
from pathlib import Path

from .config import EPISODE_DIR


def save_episode(episode: dict, folder: Path = EPISODE_DIR) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{episode['id']}.json").write_text(json.dumps(episode, indent=2), encoding="utf-8")


def load_episode(episode_id: str, folder: Path = EPISODE_DIR) -> dict | None:
    path = folder / f"{episode_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_episodes(folder: Path = EPISODE_DIR) -> list[dict]:
    if not folder.exists():
        return []
    episodes = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
    return sorted(episodes, key=lambda e: e.get("created", ""), reverse=True)
