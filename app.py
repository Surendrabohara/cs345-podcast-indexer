"""Entry point. Azure App Service (Flask) looks for app.py and a variable called `app`.

Part G note: call init_telemetry() from telemetry.py FIRST in this file, before the
imports below, so Application Insights can instrument Flask and the Azure SDKs.
"""
import os

from indexer.main import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
