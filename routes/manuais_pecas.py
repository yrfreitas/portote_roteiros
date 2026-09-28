"""Busca de manual de serviço por modelo, na aba Cotação de Peças —
pedido de 2026-09-08. Ver services/manuais_pecas.py pro porquê do cache."""
from flask import Blueprint, jsonify, request

from database import db_conn
from services.manuais_pecas import buscar, obter_paginas

manuais_pecas_bp = Blueprint("manuais_pecas", __name__)


@manuais_pecas_bp.route("/manuais-pecas/buscar", methods=["GET"])
def rota_buscar():
    termo = (request.args.get("modelo") or "").strip()
    categoria = (request.args.get("categoria") or "").strip() or None
    if not termo:
        return jsonify({"erro": "Informe o modelo do aparelho"}), 400

    resultados = buscar(termo, categoria)
    return jsonify({
        "resultados": [
            {"id": r["drive_id"], "categoria": r["categoria"], "arquivo": r["arquivo"]}
            for r in resultados
        ]
    })


@manuais_pecas_bp.route("/manuais-pecas/<drive_id>/paginas", methods=["GET"])
def rota_paginas(drive_id):
    # ?forcar=1 (item #8, 2026-09-28): ignora o cache e baixa o PDF de novo
    # do Drive -- pro caso da Panasonic ter atualizado o manual e o cache
    # não ter como perceber sozinho (mesmo drive_id, conteúdo novo).
    forcar = (request.args.get("forcar") or "").strip() in ("1", "true")
    with db_conn(commit=True) as conn:
        paginas = obter_paginas(conn, drive_id, forcar=forcar)

    if paginas is None:
        return jsonify({"erro": "Não consegui obter esse manual — tenta de novo em instantes"}), 502

    return jsonify({"paginas": paginas})
