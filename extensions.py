"""Instâncias compartilhadas entre app.py e os blueprints de rotas —
existe pra evitar import circular (rotas usando @limiter.limit(...)
precisam do objeto sem importar de volta o app.py que as registra)."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
