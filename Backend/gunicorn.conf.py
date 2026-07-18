# gunicorn.conf.py
import os

# Configuración de Gunicorn
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")
workers = 2
threads = 4
worker_class = "sync"

# ⚠️ IMPORTANTE: Aumentar el timeout a 5 minutos
timeout = 300  # 300 segundos = 5 minutos
graceful_timeout = 300
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Para manejar mejor las solicitudes largas
max_requests = 1000
max_requests_jitter = 100
