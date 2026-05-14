"""Gunicorn config — tuned for a 4 GB / 2 vCPU droplet.

Loaded by the systemd unit:
    gunicorn --config /home/jarvis/anjaneya/deploy/gunicorn.conf.py core.wsgi:application
"""

import os

# Bind to the Unix socket systemd creates via RuntimeDirectory=anjaneya.
bind = "unix:/run/anjaneya/gunicorn.sock"

# 2 * vCPU + 1 = 5 workers, gthread class with 2 threads each.
workers = int(os.environ.get("GUNICORN_WORKERS", 5))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_connections = 1000

# Recycle workers periodically to bound memory growth.
max_requests = 1000
max_requests_jitter = 100

timeout = 60
graceful_timeout = 30
keepalive = 5

accesslog = "/var/log/anjaneya/gunicorn-access.log"
errorlog = "/var/log/anjaneya/gunicorn-error.log"
loglevel = "info"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
)

proc_name = "anjaneya-gunicorn"
reload = False
daemon = False
# preload_app shares the parsed app across workers — lower memory, faster boot.
preload_app = True


def on_starting(server):
    server.log.info("Starting Anjaneya gunicorn server")
