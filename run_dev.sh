#!/usr/bin/env bash

# Kill process by port if port is exist
sudo fuser -k 5100/tcp

# Aktifkan virtual environment
source venv/bin/activate

# Jalankan Gunicorn dengan log ke screen (development mode)
gunicorn \
    --bind 0.0.0.0:5100 \
    --workers 1 \
    --threads 1 \
    --worker-class sync \
    --timeout 120 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --reload \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    wsgi:app
