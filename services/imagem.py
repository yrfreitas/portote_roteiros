"""Miniatura de foto pro servidor gerar sozinho, em cima da foto grande que
já está salva.

Achado real em 2026-09-28: o site "pesado e travando no celular" era isso —
GET /estoque e GET /cotacoes devolviam a foto de CADA item em base64
completo (a mesma que aparece ampliada), só pra desenhar um quadradinho de
~60px na lista. Com dezenas de itens com foto, um `SELECT *` desses vira um
JSON de vários MB baixado (e reprocessado pelo JS) toda vez que a aba abre
— em wifi de escritório passa despercebido, no 4G do técnico é a diferença
entre abrir na hora e travar.

Miniatura é gerada UMA VEZ (na leitura, se ainda não existir) e fica salva
em `foto_thumb` — não recalcula a cada request. `foto` grande continua
existindo pra quando alguém clica pra ampliar (rota própria, sob demanda).
"""
import base64
import io
import logging
import re

from PIL import Image

log = logging.getLogger("portotec.imagem")

_RE_DATA_URI = re.compile(r"^data:image/[\w+.-]+;base64,(.+)$", re.DOTALL)


def gerar_thumb(foto_data_uri: str, lado_max: int = 160, qualidade: int = 60) -> str | None:
    """Recebe a foto no mesmo formato salvo no banco (data URI base64) e
    devolve uma versão pequena, também como data URI JPEG. None se a foto
    vier corrompida/formato inesperado — nesse caso quem chama simplesmente
    não grava `foto_thumb` e a lista mostra sem miniatura (nunca quebra a
    tela por causa disso, mesma filosofia de `_foto_valida` em cotacoes.py)."""
    m = _RE_DATA_URI.match(foto_data_uri or "")
    if not m:
        return None
    try:
        bruto = base64.b64decode(m.group(1))
        img = Image.open(io.BytesIO(bruto))
        img = img.convert("RGB")  # fundo transparente -> branco, evita o bug de PNG virando preto (ver v150)
        img.thumbnail((lado_max, lado_max), Image.LANCZOS)
        saida = io.BytesIO()
        img.save(saida, format="JPEG", quality=qualidade, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(saida.getvalue()).decode()
    except Exception:
        log.warning("Falha gerando miniatura de foto", exc_info=True)
        return None
