"""Instâncias compartilhadas entre app.py e os blueprints de rotas —
existe pra evitar import circular (rotas usando @limiter.limit(...)
precisam do objeto sem importar de volta o app.py que as registra)."""
import logging
import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

log = logging.getLogger("portotec.limiter")

# Sem backend externo o flask-limiter guarda os contadores na memória do
# processo. Isso é correto com UM worker (ver Procfile: --workers 1 --threads 8,
# onde as threads compartilham o mesmo processo e portanto o mesmo contador),
# mas passa a ser furado no instante em que houver mais de um worker ou réplica:
# cada processo contaria por si e o limite real viraria N vezes o configurado.
# Deixar isso plugável por env significa que ligar um Redis no Railway no futuro
# é só criar a variável — nenhuma mudança de código.
_storage = os.environ.get("RATELIMIT_STORAGE_URI", "").strip()

if not _storage:
    log.warning(
        "RATELIMIT_STORAGE_URI não definida — rate limiting usando memória do "
        "processo. Só é confiável com um único worker. Se aumentar workers ou "
        "réplicas no Railway, configure um Redis nessa variável."
    )

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri=_storage or "memory://",
    # Devolve X-RateLimit-* nas respostas: sem isso não há como verificar de fora
    # se o limite está mesmo ativo — foi exatamente o que dificultou o
    # diagnóstico em 2026-08-12.
    headers_enabled=True,
)


# Versão do código do app que o servidor está servindo. Existe para resolver um
# problema que custou caro em 2026-08-14: o técnico deixa o PWA aberto o dia
# inteiro e o JS só é buscado da rede quando a PÁGINA recarrega. O service
# worker já é rede-primeiro para .js, mas isso não adianta se nunca há um novo
# carregamento — o Pedro tocou "A caminho" quatro vezes rodando código de três
# versões atrás, sem que nada indicasse isso.
#
# O app compara este valor com o que ele próprio carregou e se recarrega quando
# diverge. Subir junto com o CACHE_VERSAO do sw.js e o VERSAO_TELA do
# tecnico.js — os três têm que contar a mesma história.
VERSAO_APP = "v28"
