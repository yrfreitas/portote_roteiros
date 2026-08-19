from datetime import datetime

from flask import Blueprint, jsonify, request

from database import db_conn, execute, fetch_all, fetch_one, ler_revisao, sql
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
    """Ping de 20 em 20 segundos. Serve a três coisas ao mesmo tempo.

    Além de dizer se os dados e o código mudaram, ele REGISTRA o que o celular
    respondeu sobre si mesmo (`?app=` e `?gps=`). Isso existe porque diagnosticar
    o app do técnico às cegas custou três rodadas de deploy em 2026-08-14: o
    aparelho rodava código de três versões atrás e nada no servidor revelava
    isso. Aproveitar um ping que já acontece custa zero requisição nova.
    """
    from extensions import VERSAO_APP

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        # Truncado: é campo alimentado pelo cliente e não pode virar porta de
        # entrada para texto arbitrário grande no banco.
        app_versao = (request.args.get("app") or "")[:20] or None
        gps_estado = (request.args.get("gps") or "")[:20] or None
        gps_erro = (request.args.get("gps_erro") or "")[:120] or None

        if app_versao or gps_estado or gps_erro:
            # Mesma função que o rastreador externo usa — uma só regra de
            # gravação para as duas origens.
            from routes.rastreio import _marcar_visto
            _marcar_visto(conn, tecnico["id"], gps_estado=gps_estado,
                          app_versao=app_versao, gps_erro=gps_erro)

        # `revisao` diz que os DADOS mudaram; `app` diz que o CÓDIGO mudou.
        # São perguntas diferentes e o app reage a cada uma de um jeito:
        # recarregar a rota na primeira, recarregar a página na segunda.
        return jsonify({**ler_revisao(conn), "app": VERSAO_APP})


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

        # LEFT JOIN para o atendimento sem desfecho continuar aparecendo:
        # concluir sem escolher desfecho é permitido (o técnico pode fechar o
        # app antes), e sumir da lista por isso seria pior que a falta do dado.
        servicos = fetch_all(conn, sql("""
            SELECT s.*, d.desfecho, d.motivo AS desfecho_motivo,
                   d.peca AS desfecho_peca
              FROM servicos s
              LEFT JOIN servico_desfecho d ON d.servico_id = s.id
             WHERE s.ficha_id = ?
             ORDER BY s.ordem, s.id
        """), (ficha_id,))

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
        desfecho_gravado = _gravar_desfecho(conn, servico_id, novo_status,
                                            data.get("desfecho"),
                                            tecnico.get("nome") or "")

    return jsonify({"mensagem": f"Serviço marcado como {novo_status}",
                    "status": novo_status, "desfecho": desfecho_gravado})


# Desfechos possíveis de um atendimento. Lista FECHADA de propósito: o valor
# alimenta contagem e filtro, e texto livre não soma nem filtra.
DESFECHOS_VALIDOS = {"resolvido", "precisa_peca", "volto_depois", "nao_atendido"}


def _gravar_desfecho(conn, servico_id, novo_status, desfecho, quem):
    """Guarda o que aconteceu no atendimento, junto com a conclusão.

    Vem na MESMA requisição do status, e não num endpoint próprio, porque o
    aplicativo do técnico tem fila offline: duas requisições significariam
    que uma pode subir e a outra não, deixando atendimento concluído sem
    desfecho — ou desfecho órfão de um atendimento que voltou a pendente.

    Reabrir o atendimento apaga o desfecho: ele descreve uma conclusão que
    deixou de existir.
    """
    if novo_status != "concluido":
        execute(conn, sql("DELETE FROM servico_desfecho WHERE servico_id = ?"),
                (servico_id,))
        return None

    if not isinstance(desfecho, dict):
        return None

    tipo = (desfecho.get("tipo") or "").strip().lower()
    if tipo not in DESFECHOS_VALIDOS:
        return None

    motivo = (desfecho.get("motivo") or "").strip()[:120]
    peca = (desfecho.get("peca") or "").strip()[:200]
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute(conn, sql("DELETE FROM servico_desfecho WHERE servico_id = ?"),
            (servico_id,))
    execute(conn, sql(
        "INSERT INTO servico_desfecho (servico_id, desfecho, motivo, peca, "
        "registrado_em, registrado_por) VALUES (?, ?, ?, ?, ?, ?)"),
        (servico_id, tipo, motivo, peca, agora, quem))

    return {"tipo": tipo, "motivo": motivo, "peca": peca}


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
