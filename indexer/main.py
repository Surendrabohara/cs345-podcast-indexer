"""Web app for the Podcast & Interview Indexer (runs on localhost, deploys to App Service)."""
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .analyze import analyze_text
from .audio import UnsupportedAudioError
from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES
from .pipeline import process_audio, transcribe_only
from .search import search_segments
from .store import list_episodes, load_episode

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.errorhandler(413)
def too_large(_err):
    return jsonify(error="File is too large. The limit is 25 MB."), 413


@app.errorhandler(UnsupportedAudioError)
def unsupported(err):
    return jsonify(error=str(err)), 415


@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


def _with_uploaded_audio(handler):
    """Save the upload to a temp file, run `handler(path, filename)`, always delete the file."""
    file = request.files.get("audio")
    if file is None or not file.filename:
        return jsonify(error="Send an audio file in the 'audio' field."), 400
    name = Path(file.filename).name
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        return jsonify(error=f"Unsupported file type. Use one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}."), 415
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / name
        file.save(src)
        try:
            return handler(src, name)
        except UnsupportedAudioError:
            raise
        except RuntimeError as err:
            return jsonify(error=str(err)), 500


@app.post("/transcribe")
def transcribe():
    language = request.form.get("language", "en-US")
    return _with_uploaded_audio(lambda src, name: jsonify(transcribe_only(src, language)))


@app.post("/analyze")
def analyze():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify(error="Send JSON with a non-empty 'text' field."), 400
    try:
        return jsonify(analyze_text(text))
    except RuntimeError as err:
        return jsonify(error=str(err)), 500


@app.post("/process")
def process():
    title = (request.form.get("title") or "").strip()
    language = request.form.get("language", "en-US")

    def run(src, name):
        episode = process_audio(src, title or Path(name).stem, language)
        return jsonify(episode), 201

    return _with_uploaded_audio(run)


@app.get("/episodes")
def episodes():
    return jsonify([_summary(e) for e in list_episodes()])


@app.get("/episodes/<episode_id>")
def episode_detail(episode_id):
    ep = load_episode(episode_id)
    if ep is None:
        return jsonify(error="Episode not found."), 404
    return jsonify(ep)


@app.get("/search")
def search():
    return jsonify(
        search_segments(
            list_episodes(),
            q=request.args.get("q", ""),
            person=request.args.get("person"),
            topic=request.args.get("topic"),
            episode=request.args.get("episode"),
        )
    )


def _summary(ep: dict) -> dict:
    return {
        "id": ep["id"],
        "title": ep["title"],
        "created": ep["created"],
        "duration_seconds": ep["duration_seconds"],
        "confidence": ep.get("confidence"),
        "segments": len(ep["segments"]),
    }
