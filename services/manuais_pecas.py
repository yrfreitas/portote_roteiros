"""Manual de serviço da Panasonic → últimas páginas (desenho explodido +
lista de códigos), por modelo — pedido de 2026-09-08.

O Kalebe mantém no Google Drive (público por link) os manuais de serviço
completos por categoria de aparelho. As últimas páginas de cada manual são
exatamente a parte útil pra cotar peça: desenho numerado + tabela de
código/descrição. Buscar o PDF inteiro toda vez que alguém digita um modelo
seria lento (alguns MB, mais o tempo de renderizar); por isso o índice
(data/manuais_pecas_index.json, gerado uma vez varrendo a pasta do Drive)
só guarda nome/categoria/id do arquivo, e o PDF só é baixado e renderizado
na PRIMEIRA busca de cada modelo — depois disso fica em cache no banco
(manual_pecas_cache) e nunca mais precisa baixar de novo.

Se um dia a pasta do Drive ganhar manual novo, o índice precisa ser
regerado (não há trigger automático — é a mesma varredura feita na criação
deste arquivo, não algo o site faz sozinho hoje)."""
import base64
import json
import logging
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone

from database import execute, fetch_one

log = logging.getLogger("portotec.manuais_pecas")

_INDICE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "manuais_pecas_index.json")
_PAGINAS_FINAIS = 6
_DPI_RENDER = 120

_indice_cache = None


def _carregar_indice():
    global _indice_cache
    if _indice_cache is None:
        with open(_INDICE_PATH, "r", encoding="utf-8") as fh:
            _indice_cache = json.load(fh)
    return _indice_cache


def _normalizar(texto):
    """Maiúsculo, sem acento, só letras/números — pra "NA-F160B5W", "na f160b5w"
    e "F160B5W" baterem no mesmo jeito contra o nome do arquivo."""
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", texto.upper())


def buscar(termo, categoria=None):
    """Casamento por substring nos dois sentidos: o termo digitado pode ser
    só uma parte do modelo (ex: "160B5"), e o nome do arquivo às vezes cobre
    vários modelos juntos (ex: "MS_NA-F150B1_F130B1T.pdf")."""
    termo_norm = _normalizar(termo)
    if not termo_norm:
        return []

    resultados = []
    for item in _carregar_indice():
        if categoria and item["categoria"] != categoria:
            continue
        arquivo_norm = _normalizar(item["arquivo"])
        if termo_norm in arquivo_norm:
            resultados.append(item)
    return resultados[:20]


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _renderizar_ultimas_paginas(caminho_pdf):
    """Cada página vira uma imagem (pro desenho, que é gráfico mesmo) MAIS a
    lista de palavras com a posição de cada uma, em % da página (pedido de
    2026-09-08: "poder selecionar e copiar o código"). O client desenha um
    <span> transparente em cima de cada palavra, na posição certa — a pessoa
    vê só a imagem, mas o texto por baixo é de verdade, selecionável."""
    import pymupdf

    doc = pymupdf.open(caminho_pdf)
    try:
        total = doc.page_count
        inicio = max(0, total - _PAGINAS_FINAIS)
        paginas = []
        for i in range(inicio, total):
            pagina = doc.load_page(i)
            pix = pagina.get_pixmap(dpi=_DPI_RENDER)
            png_b64 = base64.b64encode(pix.tobytes("png")).decode("ascii")

            largura_pt = pagina.rect.width or 1
            altura_pt = pagina.rect.height or 1
            palavras = []
            for (x0, y0, x1, y1, texto, *_resto) in pagina.get_text("words"):
                if not texto.strip():
                    continue
                palavras.append({
                    "t": texto,
                    "x": round(x0 / largura_pt * 100, 3),
                    "y": round(y0 / altura_pt * 100, 3),
                    "w": round((x1 - x0) / largura_pt * 100, 3),
                    "h": round((y1 - y0) / altura_pt * 100, 3),
                })

            paginas.append({
                "imagem": "data:image/png;base64," + png_b64,
                "palavras": palavras,
            })
        return paginas
    finally:
        doc.close()


def obter_paginas(conn, drive_id):
    """Retorna as páginas ({imagem, palavras}) do manual. Usa o cache se já
    existe; senão baixa do Drive, renderiza e grava."""
    linha = fetch_one(conn, "SELECT imagens FROM manual_pecas_cache WHERE drive_id = ?", (drive_id,))
    if linha and linha.get("imagens"):
        paginas_cache = json.loads(linha["imagens"])
        # Cache da v235 guardava só a imagem (string), sem palavra pra
        # selecionar — trata como se não tivesse cache e gera de novo no
        # formato novo, em vez de mostrar página sem texto pra sempre.
        if paginas_cache and isinstance(paginas_cache[0], dict):
            return paginas_cache

    item = next((i for i in _carregar_indice() if i["drive_id"] == drive_id), None)
    if not item:
        return None

    import gdown

    with tempfile.TemporaryDirectory() as tmp:
        caminho = os.path.join(tmp, "manual.pdf")
        try:
            gdown.download(id=drive_id, output=caminho, quiet=True)
        except Exception:
            log.exception("Falha ao baixar manual do Drive (drive_id=%s)", drive_id)
            return None

        if not os.path.exists(caminho):
            return None

        try:
            paginas = _renderizar_ultimas_paginas(caminho)
        except Exception:
            log.exception("Falha ao renderizar manual (drive_id=%s)", drive_id)
            return None

    # drive_id é PRIMARY KEY: pode já existir uma linha no formato antigo
    # (v235, sem palavra) pra regenerar — apaga antes de inserir a nova em
    # vez de UPDATE ... ON CONFLICT (dialeto diferente entre SQLite/Postgres,
    # mesmo motivo do resto do projeto, ver services/substituicoes.py).
    execute(conn, "DELETE FROM manual_pecas_cache WHERE drive_id = ?", (drive_id,))
    execute(conn, """
        INSERT INTO manual_pecas_cache (drive_id, categoria, arquivo, imagens, gerado_em)
        VALUES (?, ?, ?, ?, ?)
    """, (drive_id, item["categoria"], item["arquivo"], json.dumps(paginas), _agora()))

    return paginas
