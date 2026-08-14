# gunicorn_config.py

import os

# ============================================
# Gunicorn Configuration for IPAM
# ============================================

# Number of worker processes
# Formula: (2 x CPU cores) + 1
workers = int(os.environ.get('GUNICORN_WORKERS', 4))

# Worker class
# 'sync' is safe for CPU-bound, 'gevent' for I/O-bound
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')

# Number of threads per worker (only for gthread worker class)
threads = int(os.environ.get('GUNICORN_THREADS', 2))

# Timeout for worker processes (in seconds)
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))

# Keep-alive connection time (in seconds)
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', 5))

# Maximum number of requests a worker will process before restarting
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))

# Add jitter to avoid all workers restarting at the same time
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))

# Graceful timeout (in seconds)
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', 30))

# Bind address
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5100')

# Access log
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', 'logs/gunicorn_access.log')

# Error log
errorlog = os.environ.get('GUNICORN_ERROR_LOG', 'logs/gunicorn_error.log')

# Log level
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Preload application (saves memory but requires app to be fork-safe)
preload_app = os.environ.get('GUNICORN_PRELOAD_APP', 'true').lower() == 'true'

# Daemon mode (set to 'true' to run in background)
daemon = os.environ.get('GUNICORN_DAEMON', 'false').lower() == 'true'

# Process name
proc_name = 'ipam'

# PID file (only used in daemon mode)
pidfile = 'logs/gunicorn.pid' if daemon else None

# Server mechanics
forwarded_allow_ips = '*'  # Trust X-Forwarded-For headers from proxy