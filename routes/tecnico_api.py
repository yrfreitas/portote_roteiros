from flask import Blueprint, jsonify, request

from database import db_conn, execute, fetch_all, fetch_one, ler_revisao
from routes.fichas import (STATUS_VALIDOS, ordenar_por_semana,
                           recalcular_distancia_ordem_fixa)
from routes.servicos import STATUS_SERVICO_VALIDOS, aplicar_status_servico

tecnico_api_bp = Blueprint("tecnico_api", __name__)


def _tecnico_por_token(conn, token):
    if not token:
        return None
    return fetch_one(conn, "SELECT * FROM tecnicos WHERE token = ?", (token,))


def _ficha_do_tecnico(conn, ficha_id, tecnico_id):
    return fetch_one(
        conn, "SELECT * FROM fichas WHERE id = ? AND tecnico_id = ?",
        (ficha_id, tecnico_id),
    )


# Espelho do /api/versao para o técnico em campo. Existe separado porque
# /api/versao passa pela sessão de admin e o técnico não tem sessão — o link
# dele é a credencial. Valida o token do mesmo jeito que as demais rotas daqui:
# link inválido não recebe nem o número da revisão.
@tecnico_api_bp.route("/<token>/versao", methods=["GET"])
def versao_tecnico(token):
    with db_conn() as conn:
        if not _tecnico_por_token(conn, token):
            return jsonify({"erro": "Link inválido"}), 404
        return jsonify(ler_revisao(conn))


@tecnico_api_bp.route("/<token>/fichas", methods=["GET"])
def fichas_do_tecnico(token):
    with db_conn() as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        fichas = fetch_all(conn, """
            SELECT f.*, COUNT(s.id) AS total_servicos
            FROM fichas f
            LEFT JOIN servicos s ON s.ficha_id = f.id
            WHERE f.tecnico_id = ?
            GROUP BY f.id
        """, (tecnico["id"],))

        # Mesma ordem da semana do painel. O técnico abre o app para saber o
        # que vem hoje; lista embaralhada por "quem foi editado por último"
        # obriga a procurar o próprio dia numa tela pequena.
        fichas = ordenar_por_semana(fichas)

    return jsonify({"tecnico": {"id": tecnico["id"], "nome": tecnico["nome"], "cor": tecnico["cor"]},
                     "fichas": fichas})


@tecnico_api_bp.route("/<token>/fichas/<int:ficha_id>", methods=["GET"])
def detalhe_ficha_tecnico(token, ficha_id):
    with db_conn() as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        ficha = _ficha_do_tecnico(conn, ficha_id, tecnico["id"])
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(
            conn, "SELECT * FROM servicos WHERE ficha_id = ? ORDER BY ordem, id",
            (ficha_id,),
        )

    return jsonify({"ficha": ficha, "servicos": servicos})


@tecnico_api_bp.route("/<token>/fichas/<int:ficha_id>/status", methods=["PUT"])
def status_ficha_tecnico(token, ficha_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_VALIDOS:
        return jsonify({"erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_VALIDOS))}"}), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        ficha = _ficha_do_tecnico(conn, ficha_id, tecnico["id"])
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        if novo_status == "concluida":
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (novo_status, ficha_id))
        else:
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = NULL,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (novo_status, ficha_id))

    return jsonify({"mensagem": f"Ficha marcada como {novo_status}", "status": novo_status})


@tecnico_api_bp.route("/<token>/servicos/<int:servico_id>/status", methods=["PUT"])
def status_servico_tecnico(token, servico_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_SERVICO_VALIDOS:
        return jsonify({
            "erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_SERVICO_VALIDOS))}"
        }), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        servico = fetch_one(conn, """
            SELECT s.* FROM servicos s
            JOIN fichas f ON f.id = s.ficha_id
            WHERE s.id = ? AND f.tecnico_id = ?
        """, (servico_id, tecnico["id"]))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404

        aplicar_status_servico(conn, servico_id, novo_status)

    return jsonify({"mensagem": f"Serviço marcado como {novo_status}", "status": novo_status})


@tecnico_api_bp.route("/<token>/fichas/<int:ficha_id>/reordenar", methods=["PUT"])
def reordenar_tecnico(token, ficha_id):
    data = request.get_json(silent=True) or {}
    ordem_ids = data.get("ordem_ids")

    if not isinstance(ordem_ids, list) or not ordem_ids:
        return jsonify({"erro": "ordem_ids deve ser uma lista de IDs de serviço"}), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        ficha = _ficha_do_tecnico(conn, ficha_id, tecnico["id"])
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(conn, "SELECT id FROM servicos WHERE ficha_id = ?", (ficha_id,))
        ids_da_ficha = {s["id"] for s in servicos}

        try:
            ordem_ids = [int(i) for i in ordem_ids]
        except (TypeError, ValueError):
            return jsonify({"erro": "ordem_ids deve conter apenas números"}), 400

        if set(ordem_ids) != ids_da_ficha:
            return jsonify({
                "erro": "A lista enviada não corresponde exatamente aos pontos desta ficha."
            }), 409

        for posicao, servico_id in enumerate(ordem_ids, start=1):
            execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?", (posicao, servico_id))

        resultado = recalcular_distancia_ordem_fixa(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Ordem atualizada manualmente", **resultado})


@tecnico_api_bp.route("/<token>/push/subscribe", methods=["POST"])
def push_subscribe(token):
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth_key = (keys.get("auth") or "").strip()

    if not endpoint or not p256dh or not auth_key:
        return jsonify({"erro": "Subscription incompleta"}), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        existente = fetch_one(
            conn, "SELECT id FROM push_subscriptions WHERE endpoint = ?", (endpoint,)
        )
        if existente:
            execute(conn, """
                UPDATE push_subscriptions SET tecnico_id = ?, p256dh = ?, auth = ?
                WHERE id = ?
            """, (tecnico["id"], p256dh, auth_key, existente["id"]))
        else:
            execute(conn, """
                INSERT INTO push_subscriptions (tecnico_id, endpoint, p256dh, auth)
                VALUES (?, ?, ?, ?)
            """, (tecnico["id"], endpoint, p256dh, auth_key))

    return jsonify({"mensagem": "Notificações ativadas"}), 201


@tecnico_api_bp.route("/<token>/push/subscribe", methods=["DELETE"])
def push_unsubscribe(token):
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        execute(conn, """
            DELETE FROM push_subscriptions WHERE endpoint = ? AND tecnico_id = ?
        """, (endpoint, tecnico["id"]))

    return jsonify({"mensagem": "Notificações desativadas"})
