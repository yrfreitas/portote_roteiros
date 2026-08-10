from flask import Blueprint, jsonify, request

from database import db_conn, execute, fetch_one
from extensions import limiter
from routes.fichas import recalcular_rota
from services.geo import geocode_cep

servicos_bp = Blueprint("servicos", __name__)

AVISO_IMPRECISO = ("Endereço aproximado (centroide do CEP). "
                   "Confira o número da casa para maior precisão.")

STATUS_SERVICO_VALIDOS = {"pendente", "concluido"}


def aplicar_status_servico(conn, servico_id: int, novo_status: str) -> None:
    """UPDATE puro, sem validação — quem chama já garantiu que o status é
    válido e que o serviço existe e pertence a quem está pedindo a mudança.
    Compartilhado entre a rota admin (servicos_bp) e a rota escopada por
    token do técnico (tecnico_api_bp)."""
    if novo_status == "concluido":
        execute(conn, """
            UPDATE servicos SET status = ?, concluido_em = CURRENT_TIMESTAMP WHERE id = ?
        """, (novo_status, servico_id))
    else:
        execute(conn, """
            UPDATE servicos SET status = ?, concluido_em = NULL WHERE id = ?
        """, (novo_status, servico_id))


@servicos_bp.route("/fichas/<int:ficha_id>/servicos", methods=["POST"])
@limiter.limit("60 per minute")
def adicionar_servico(ficha_id):
    data = request.get_json(silent=True) or {}

    cep = "".join(c for c in (data.get("cep") or "") if c.isdigit())
    numero = (data.get("numero") or "").strip()

    if len(cep) != 8:
        return jsonify({"erro": "Informe um CEP válido com 8 dígitos"}), 400

    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
    if not ficha:
        return jsonify({"erro": "Ficha não encontrada"}), 404

    geo = geocode_cep(cep, numero=numero)
    if not geo:
        return jsonify({
            "erro": f"CEP {cep[:5]}-{cep[5:]} não encontrado. "
                    f"Confira o número e tente novamente."
        }), 400

    with db_conn(commit=True) as conn:
        execute(conn, """
            INSERT INTO servicos
                (ficha_id, cep, endereco_completo, lat, lng,
                 cliente, descricao, numero, tipo_aparelho, modelo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ficha_id, cep, geo.endereco, geo.lat, geo.lng,
              (data.get("cliente") or "").strip(),
              (data.get("descricao") or "").strip(),
              numero,
              (data.get("tipo_aparelho") or "").strip(),
              (data.get("modelo") or "").strip()))

        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        resultado = recalcular_rota(conn, ficha_id, ficha)

    resposta = {
        "mensagem": "Serviço adicionado e rota otimizada",
        "endereco": geo.endereco,
        "numero":   numero,
        **resultado,
    }

    if not geo.preciso:
        resposta["aviso"] = AVISO_IMPRECISO
    elif resultado.get("sem_partida"):
        resposta["aviso"] = ("Ponto adicionado, mas esta ficha não tem CEP de "
                             "partida — a rota não pode ser otimizada ainda.")

    return jsonify(resposta), 201


@servicos_bp.route("/servicos/<int:servico_id>", methods=["PUT"])
def editar_servico(servico_id):
    data = request.get_json(silent=True) or {}

    with db_conn() as conn:
        servico = fetch_one(conn, "SELECT * FROM servicos WHERE id = ?", (servico_id,))
    if not servico:
        return jsonify({"erro": "Serviço não encontrado"}), 404

    cep_novo = "".join(c for c in (data.get("cep") or servico["cep"]) if c.isdigit())
    numero_novo = (data.get("numero") if data.get("numero") is not None
                   else servico.get("numero") or "").strip()

    mudou_local = (cep_novo != servico["cep"]
                   or numero_novo != (servico.get("numero") or ""))

    lat, lng = servico.get("lat"), servico.get("lng")
    endereco = servico.get("endereco_completo")
    geo = None

    if mudou_local:
        if len(cep_novo) != 8:
            return jsonify({"erro": "Informe um CEP válido com 8 dígitos"}), 400
        geo = geocode_cep(cep_novo, numero=numero_novo)
        if not geo:
            return jsonify({"erro": f"CEP {cep_novo} não encontrado"}), 400
        lat, lng, endereco = geo.lat, geo.lng, geo.endereco

    with db_conn(commit=True) as conn:
        execute(conn, """
            UPDATE servicos
               SET cep = ?, numero = ?, endereco_completo = ?,
                   lat = ?, lng = ?, cliente = ?, descricao = ?,
                   tipo_aparelho = ?, modelo = ?
             WHERE id = ?
        """, (cep_novo, numero_novo, endereco, lat, lng,
              (data.get("cliente") if data.get("cliente") is not None
               else servico.get("cliente") or ""),
              (data.get("descricao") if data.get("descricao") is not None
               else servico.get("descricao") or ""),
              (data.get("tipo_aparelho") if data.get("tipo_aparelho") is not None
               else servico.get("tipo_aparelho") or ""),
              (data.get("modelo") if data.get("modelo") is not None
               else servico.get("modelo") or ""),
              servico_id))

        ficha_id = servico["ficha_id"]
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        resultado = recalcular_rota(conn, ficha_id, ficha) if mudou_local else {}

    resposta = {"mensagem": "Serviço atualizado", "endereco": endereco, **resultado}
    if geo and not geo.preciso:
        resposta["aviso"] = AVISO_IMPRECISO
    return jsonify(resposta)


@servicos_bp.route("/servicos/<int:servico_id>/status", methods=["PUT"])
def alterar_status_servico(servico_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_SERVICO_VALIDOS:
        return jsonify({
            "erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_SERVICO_VALIDOS))}"
        }), 400

    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, "SELECT id FROM servicos WHERE id = ?", (servico_id,))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404
        aplicar_status_servico(conn, servico_id, novo_status)

    return jsonify({"mensagem": f"Serviço marcado como {novo_status}", "status": novo_status})


@servicos_bp.route("/servicos/<int:servico_id>", methods=["DELETE"])
def remover_servico(servico_id):
    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, "SELECT * FROM servicos WHERE id = ?", (servico_id,))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404

        ficha_id = servico["ficha_id"]
        execute(conn, "DELETE FROM servicos WHERE id = ?", (servico_id,))

        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        resultado = recalcular_rota(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Serviço removido e rota recalculada", **resultado})