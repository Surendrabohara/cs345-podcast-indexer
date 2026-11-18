#!/bin/bash
# App Service startup command. ffmpeg is not on the Linux image, so install it on every cold start.
apt-get update && apt-get install -y ffmpeg
gunicorn --bind=0.0.0.0 --timeout 600 app:app
