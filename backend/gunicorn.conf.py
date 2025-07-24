# Gunicorn configuration file for Audiobook Organizer

# Server socket
bind = "0.0.0.0:4000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'audiobook-organizer'

# Daemon mode
daemon = False

# User/group to run as (optional, for security)
# user = "audiobook"
# group = "audiobook"

# Preload application for better performance
preload_app = True

# Enable hot reloading in development
reload = False
