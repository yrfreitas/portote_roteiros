"""Rastreio ao vivo: o cliente acompanha o técnico a caminho.

O Waze tem "Compartilhar percurso", mas o link só nasce dentro do aplicativo
depois que o motorista começou a navegar — não há API para gerá-lo de fora.
Então o acompanhamento é nosso: o celular do técnico manda a posição, e uma
página pública mostra onde ele está.

DECISÕES DE PRIVACIDADE, que aqui não são detalhe:
- Guarda só a ÚLTIMA posição, nunca o trajeto. O cliente quer saber onde ele
  está agora; histórico de deslocamento de funcionário é dado sensível que
  ninguém pediu para ter.
- O rastreio é por ATENDIMENTO, não por técnico. Começa quando ele sai para
  aquele cliente e morre quando chega.
- Expira sozinho depois de VALIDADE_HORAS mesmo se ninguém encerrar. Técnico
  que esquece o app aberto não vira rastreado o dia inteiro.
- Concluir o ponto encerra o rastreio (ver aplicar_status_servico).
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request

from database import IS_PG, db_conn, execute, fetch_all, fetch_one

log = logging.getLogger("portotec.rastreio")

rastreio_bp = Blueprint("rastreio", __name__)

# Depois disso o link para de mostrar posição, encerrado ou não. Uma visita
# não passa de algumas horas; o que passar disso é app esquecido aberto.
VALIDADE_HORAS = 6

_ATIVO = "ativo IS TRUE" if IS_PG else "ativo = 1"


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _expirado(criado_em: str) -> bool:
    """Compara textualmente, no mesmo formato que gravamos. Ver a armadilha
    documentada em routes/fichas.py: a coluna é TEXT e o separador é ESPAÇO,
    então um isoformat() com T daria comparação errada."""
    if not criado_em:
        return True
    corte = (datetime.now(timezone.utc) - timedelta(hours=VALIDADE_HORAS))
    return str(criado_em)[:19] < corte.strftime("%Y-%m-%d %H:%M:%S")


def encerrar_por_servico(conn, servico_id: int) -> None:
    """Chamado quando o ponto é concluído: chegou, não faz mais sentido
    rastrear. Fica aqui para não espalhar regra de rastreio pelas rotas."""
    execute(conn, f"""
        UPDATE rastreios SET ativo = {'FALSE' if IS_PG else '0'}, encerrado_em = ?
         WHERE servico_id = ? AND {_ATIVO}
    """, (_agora(), servico_id))


def _tecnico_por_token(conn, token):
    if not token:
        return None
    return fetch_one(conn, "SELECT * FROM tecnicos WHERE token = ?", (token,))


@rastreio_bp.route("/t/<token>/servicos/<int:servico_id>/rastreio", methods=["POST"])
def iniciar(token, servico_id):
    """Abre (ou reaproveita) o rastreio deste atendimento."""
    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        # O ponto tem que ser de uma ficha do próprio técnico. Sem isso, quem
        # tivesse um link de técnico poderia abrir rastreio de qualquer ponto.
        servico = fetch_one(conn, """
            SELECT sv.id FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id
             WHERE sv.id = ? AND f.tecnico_id = ?
        """, (servico_id, tecnico["id"]))
        if not servico:
            return jsonify({"erro": "Ponto não encontrado nas suas rotas"}), 404

        existente = fetch_one(conn, f"""
            SELECT * FROM rastreios WHERE servico_id = ? AND {_ATIVO}
             ORDER BY id DESC
        """, (servico_id,))

        # Reaproveita o link se ainda vale: reabrir o mesmo atendimento não
        # pode invalidar o link que o cliente já recebeu.
        if existente and not _expirado(existente.get("criado_em")):
            return jsonify({"token": existente["token"], "reaproveitado": True})

        novo_token = secrets.token_urlsafe(16)
        execute(conn, """
            INSERT INTO rastreios (token, servico_id, tecnico_id, criado_em)
            VALUES (?, ?, ?, ?)
        """, (novo_token, servico_id, tecnico["id"], _agora()))

    return jsonify({"token": novo_token, "reaproveitado": False}), 201


@rastreio_bp.route("/t/<token>/rastreio/<rastreio_token>/posicao", methods=["PUT"])
def atualizar_posicao(token, rastreio_token):
    dados = request.get_json(silent=True) or {}
    try:
        lat = float(dados.get("lat"))
        lng = float(dados.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Coordenadas inválidas"}), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        # O rastreio tem que ser DELE. Caso contrário um técnico poderia
        # empurrar posição no rastreio de outro.
        alteradas = execute(conn, f"""
            UPDATE rastreios SET lat = ?, lng = ?, atualizado_em = ?
             WHERE token = ? AND tecnico_id = ? AND {_ATIVO}
        """, (lat, lng, _agora(), rastreio_token, tecnico["id"]))

    if not alteradas:
        return jsonify({"erro": "Rastreio não encontrado ou já encerrado"}), 404
    return jsonify({"ok": True})


@rastreio_bp.route("/t/<token>/rastreio/<rastreio_token>/encerrar", methods=["POST"])
def encerrar(token, rastreio_token):
    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        execute(conn, f"""
            UPDATE rastreios SET ativo = {'FALSE' if IS_PG else '0'}, encerrado_em = ?
             WHERE token = ? AND tecnico_id = ?
        """, (_agora(), rastreio_token, tecnico["id"]))

    return jsonify({"ok": True})


@rastreio_bp.route("/rastreio/<rastreio_token>", methods=["GET"])
def consultar(rastreio_token):
    """Leitura PÚBLICA — é o que a página do cliente consome.

    Devolve o mínimo: primeiro nome do técnico, posição atual e o destino.
    Nada de telefone, nome completo, outros pontos da rota ou dados da ficha.
    Quem tem o link é o cliente, não alguém com direito ao resto.
    """
    with db_conn() as conn:
        r = fetch_one(conn, """
            SELECT ra.*, sv.cliente, sv.endereco_completo,
                   sv.lat AS destino_lat, sv.lng AS destino_lng, sv.status AS servico_status,
                   t.nome AS tecnico_nome
              FROM rastreios ra
              JOIN servicos sv ON sv.id = ra.servico_id
              JOIN tecnicos t  ON t.id = ra.tecnico_id
             WHERE ra.token = ?
        """, (rastreio_token,))

    if not r:
        return jsonify({"erro": "Link de acompanhamento inválido"}), 404

    encerrado = (not r.get("ativo")) or _expirado(r.get("criado_em"))
    primeiro_nome = (r.get("tecnico_nome") or "").split(" ")[0]

    return jsonify({
        "ativo":     not encerrado,
        "tecnico":   primeiro_nome,
        "cliente":   r.get("cliente") or "",
        "destino":   {"lat": r.get("destino_lat"), "lng": r.get("destino_lng"),
                      "endereco": r.get("endereco_completo") or ""},
        # Só manda posição enquanto vale. Link vencido devolvendo a última
        # coordenada conhecida mostraria o técnico parado onde ele já não está.
        "posicao":   ({"lat": r["lat"], "lng": r["lng"], "em": r.get("atualizado_em")}
                      if (not encerrado and r.get("lat") is not None) else None),
        "chegou":    r.get("servico_status") == "concluido",
    })


@rastreio_bp.route("/rastreios/diagnostico", methods=["GET"])
def diagnostico():
    """Rastreios recentes, para saber o que de fato aconteceu no celular.

    Fica atrás da sessão de admin (não tem prefixo público). Existe porque
    "não funcionou" no aparelho de outra pessoa é impossível de investigar sem
    ver se o rastreio nasceu e se alguma posição chegou.
    """
    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT ra.id, ra.token, ra.lat, ra.lng, ra.ativo,
                   ra.criado_em, ra.atualizado_em, ra.encerrado_em,
                   t.nome AS tecnico, sv.cliente
              FROM rastreios ra
              JOIN tecnicos t  ON t.id = ra.tecnico_id
              JOIN servicos sv ON sv.id = ra.servico_id
             ORDER BY ra.id DESC
        """)

    return jsonify({
        "total": len(linhas),
        "com_posicao": sum(1 for l in linhas if l.get("lat") is not None),
        "rastreios": [{
            "id": l["id"],
            "tecnico": l["tecnico"],
            "cliente": l["cliente"],
            "criado_em": l["criado_em"],
            # A pergunta que decide o diagnóstico: nasceu mas nunca recebeu
            # posição? Então o problema é o GPS do aparelho, não a API.
            "recebeu_posicao": l.get("lat") is not None,
            "atualizado_em": l.get("atualizado_em"),
            "ativo": bool(l.get("ativo")),
        } for l in linhas[:20]],
    })


# A página em si (/acompanhar/<token>) fica no app.py, fora deste blueprint:
# aqui tudo vive sob /api, e a página é HTML que o cliente abre no navegador.
