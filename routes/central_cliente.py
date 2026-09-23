"""Central do Cliente — o cliente acompanha a própria Ordem de Serviço por um
link público (ordens_servico.token_cliente), sem login.

Fase 1 (2026-09-16): status/timeline, "técnico a caminho" (reaproveita
routes/rastreio.py, não duplica tracking), aprovar/reprovar orçamento sem
pagamento ainda, e aviso push opcional. Fora de escopo desta fase — decisão
de negócio pendente: agendamento por CEP (falta agenda de capacidade por
região) e Pix/cartão (falta escolher gateway).

Mesmo modelo de privacidade do link de rastreio: quem tem o token é o
cliente, não alguém com direito ao resto — devolve só o que a tela precisa.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from database import db_conn, execute, fetch_all, fetch_one
from routes.ordens_servico import STATUS_OS, STATUS_OS_FINALIZADORES
from routes.rastreio import montar_payload_rastreio, rastreio_ativo_para_os
from services.garantia import calcular_garantia

central_cliente_bp = Blueprint("central_cliente", __name__)

# Copy pensada pra quem NÃO trabalha na Porto Tec — os valores em STATUS_OS
# (routes/ordens_servico.py) são vocabulário interno. "cancelada" fica de
# fora de propósito: é tratada como aviso à parte, não como um degrau da
# timeline (uma OS cancelada não "progride" até lá).
_ROTULOS_CLIENTE = {
    "aguardando_agendamento": "Aguardando agendamento",
    "aguardando_agendamento_garantia": "Aguardando agendamento (retorno em garantia)",
    "agendada": "Visita agendada",
    "aguardando_peca": "Aguardando peça",
    "aguardando_orcamento": "Orçamento em elaboração",
    "aguardando_aprovacao": "Aguardando sua aprovação",
    "reprovada": "Orçamento não aprovado",
    "aprovada": "Orçamento aprovado",
    "aprovado_agendar": "Garantia aprovada — aguardando agendamento",
    "enviar_ordem_pdf": "Serviço concluído",
    "finalizada": "Serviço concluído",
    "finalizada_garantia": "Serviço concluído (garantia)",
}
_TIMELINE = [s for s in STATUS_OS if s != "cancelada"]


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _os_por_token(conn, token):
    return fetch_one(conn, """
        SELECT os.id, os.status, os.modelo_os, os.tipo_os, os.criado_em,
               os.garantia_meses, os.garantia_inicio,
               os.orcamento_aprovado_em, os.orcamento_reprovado_em,
               c.nome AS cliente_nome
          FROM ordens_servico os
          JOIN clientes c ON c.id = os.cliente_id
         WHERE os.token_cliente = ?
    """, (token,))


def _montar_timeline(status: str):
    if status == "cancelada":
        return []
    try:
        posicao_atual = _TIMELINE.index(status)
    except ValueError:
        posicao_atual = -1   # status fora da lista normal — timeline vazia, não quebra
    return [
        {"chave": s, "rotulo": _ROTULOS_CLIENTE.get(s, s),
         "estado": "done" if i < posicao_atual else ("current" if i == posicao_atual else "pending")}
        for i, s in enumerate(_TIMELINE)
    ]


@central_cliente_bp.route("/<token>/status", methods=["GET"])
def status(token):
    """Único endpoint de polling da página — devolve tudo que ela mostra."""
    with db_conn() as conn:
        ordem = _os_por_token(conn, token)
        if not ordem:
            return jsonify({"erro": "Link inválido"}), 404

        orcamento = None
        if (ordem.get("modelo_os") == "orcamento"
                and ordem.get("status") == "aguardando_aprovacao"
                and not ordem.get("orcamento_aprovado_em")
                and not ordem.get("orcamento_reprovado_em")):
            itens = fetch_all(conn, """
                SELECT nome, valor FROM ordem_servico_itens
                 WHERE ordem_servico_id = ? ORDER BY id
            """, (ordem["id"],))
            orcamento = {
                "itens": [{"nome": i["nome"], "valor": float(i["valor"] or 0)} for i in itens],
                "valor_total": sum(float(i["valor"] or 0) for i in itens),
            }

        r = rastreio_ativo_para_os(conn, ordem["id"])
        tecnico_a_caminho = montar_payload_rastreio(r) if r else None

    garantia = calcular_garantia(ordem) if ordem.get("status") in STATUS_OS_FINALIZADORES else None

    return jsonify({
        "cliente_nome": (ordem.get("cliente_nome") or "").split(" ")[0],
        "status": ordem.get("status"),
        "status_rotulo": _ROTULOS_CLIENTE.get(ordem.get("status"), ordem.get("status")),
        "cancelada": ordem.get("status") == "cancelada",
        "timeline": _montar_timeline(ordem.get("status")),
        "orcamento": orcamento,
        "orcamento_reprovado": bool(ordem.get("orcamento_reprovado_em")),
        "tecnico_a_caminho": tecnico_a_caminho,
        "garantia": garantia,
    })


@central_cliente_bp.route("/<token>/orcamento/aprovar", methods=["POST"])
def aprovar(token):
    with db_conn(commit=True) as conn:
        ordem = _os_por_token(conn, token)
        if not ordem:
            return jsonify({"erro": "Link inválido"}), 404
        if ordem.get("modelo_os") != "orcamento":
            return jsonify({"erro": "Esta OS não é um orçamento"}), 400
        if ordem.get("orcamento_aprovado_em"):
            return jsonify({"erro": "Este orçamento já está aprovado"}), 400
        if ordem.get("orcamento_reprovado_em"):
            return jsonify({"erro": "Este orçamento já foi reprovado"}), 400
        agora = _agora()
        execute(conn, "UPDATE ordens_servico SET orcamento_aprovado_em = ? WHERE id = ?",
                (agora, ordem["id"]))
    return jsonify({"mensagem": "Orçamento aprovado", "orcamento_aprovado_em": agora})


@central_cliente_bp.route("/<token>/orcamento/reprovar", methods=["POST"])
def reprovar(token):
    with db_conn(commit=True) as conn:
        ordem = _os_por_token(conn, token)
        if not ordem:
            return jsonify({"erro": "Link inválido"}), 404
        if ordem.get("modelo_os") != "orcamento":
            return jsonify({"erro": "Esta OS não é um orçamento"}), 400
        if ordem.get("orcamento_aprovado_em"):
            return jsonify({"erro": "Este orçamento já está aprovado"}), 400
        if ordem.get("orcamento_reprovado_em"):
            return jsonify({"erro": "Este orçamento já foi reprovado"}), 400
        agora = _agora()
        execute(conn, "UPDATE ordens_servico SET orcamento_reprovado_em = ? WHERE id = ?",
                (agora, ordem["id"]))
    return jsonify({"mensagem": "Orçamento reprovado", "orcamento_reprovado_em": agora})


@central_cliente_bp.route("/<token>/push/subscribe", methods=["POST"])
def push_subscribe(token):
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth_key = (keys.get("auth") or "").strip()

    if not endpoint or not p256dh or not auth_key:
        return jsonify({"erro": "Subscription incompleta"}), 400

    with db_conn(commit=True) as conn:
        ordem = _os_por_token(conn, token)
        if not ordem:
            return jsonify({"erro": "Link inválido"}), 404

        existente = fetch_one(
            conn, "SELECT id FROM push_subscriptions_cliente WHERE endpoint = ?", (endpoint,)
        )
        if existente:
            execute(conn, """
                UPDATE push_subscriptions_cliente SET os_id = ?, p256dh = ?, auth = ?
                WHERE id = ?
            """, (ordem["id"], p256dh, auth_key, existente["id"]))
        else:
            execute(conn, """
                INSERT INTO push_subscriptions_cliente (os_id, endpoint, p256dh, auth)
                VALUES (?, ?, ?, ?)
            """, (ordem["id"], endpoint, p256dh, auth_key))

    return jsonify({"mensagem": "Notificações ativadas"}), 201


@central_cliente_bp.route("/<token>/push/subscribe", methods=["DELETE"])
def push_unsubscribe(token):
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()

    with db_conn(commit=True) as conn:
        ordem = _os_por_token(conn, token)
        if not ordem:
            return jsonify({"erro": "Link inválido"}), 404

        execute(conn, """
            DELETE FROM push_subscriptions_cliente WHERE endpoint = ? AND os_id = ?
        """, (endpoint, ordem["id"]))

    return jsonify({"mensagem": "Notificações desativadas"})
