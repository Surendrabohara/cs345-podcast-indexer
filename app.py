"""Entry point. Azure App Service (Flask) looks for app.py and a variable called `app`.

Application Insights must start FIRST, before Flask or any Azure SDK is imported (handout G2).
"""
import os

from dotenv import load_dotenv

load_dotenv()  # load .env before everything else

from indexer.telemetry import init_telemetry  # noqa: E402

init_telemetry()

from indexer.main import app  # noqa: E402,F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
