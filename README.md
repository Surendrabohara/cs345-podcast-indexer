# Podcast & Interview Indexer

CS 345 / CSC 645 Azure AI Speech semester project. Product 7.
Track 1: Azure AI Search. Track 2: Terraform.

Upload an audio file. The app transcribes it (Azure AI Speech), finds people, topics and sentiment (Azure AI Language), cuts it into 30–60 second segments, and lets you search them with a timestamp.

## What works now (checkpoint: Parts A–C)

| Endpoint | What it does |
|---|---|
| `POST /transcribe` | audio in, JSON out: `transcript`, `language`, `duration_seconds`, `confidence`, `words` |
| `POST /analyze` | `{"text": "..."}` in, key phrases / entities / sentiment out |
| `POST /process` | main endpoint: transcribe + analyze + segment + store. Returns 201 |
| `GET /episodes`, `GET /episodes/<id>` | list and read stored episodes |
| `GET /search?q=&person=&topic=` | search segments, returns `latency_ms` |
| `GET /health` | `{"status":"ok"}` |

Errors: unsupported or unreadable audio → **415**. File over 25 MB → **413**. Missing file → **400**.
The uploaded audio is converted in a temp folder and deleted. Only the transcript and segments are kept (in `data/episodes/`).

## Setup

Azure resource names used in this project: resource group `cs345-speech-rg`, Speech `cs345-speech`, Language `cs345-language`, Log Analytics `cs345-logs`, Application Insights `cs345-insights`.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your own values
```

You also need **ffmpeg** installed locally (`brew install ffmpeg` or `sudo apt install ffmpeg`).

`.env` is in `.gitignore`. Never commit it. Never paste real keys into an AI tool.

## Run

```bash
python app.py                      # http://localhost:5000
```

Try the main endpoint:

```bash
curl -F "audio=@my-recording.m4a" -F "title=Glacier basics" http://localhost:5000/process
```

Or from the command line, no server needed:

```bash
python -m indexer.cli my-recording.m4a --title "Glacier basics"
```

## Tests

```bash
pytest -q
```

The tests use fakes for Azure, so they run without keys.

## Deploying (later)

`startup.sh` installs ffmpeg and starts gunicorn (`app:app`) on App Service. Set the same values as in `.env` as App Service application settings.

## Test recordings

Scripts and expected answers are in `test-data/`. All five recordings are self-recorded. Audio files are not committed.

## Not built yet

Part D (text to speech), Part E (microphone page), Part G (Application Insights and the `search_latency_ms` metric), Track 1 (Azure AI Search index), Track 2 (Terraform).
