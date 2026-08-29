"""Chat: o cliente conversa com a Porto Tec pelo próprio link de acompanhamento.

POR QUE ASSIM, E NÃO UM CHAT GENÉRICO:
o cliente não tem conta e não vai criar uma para perguntar "que horas ele
chega?". O link do acompanhamento já é a credencial dele — o mesmo modelo do
link do técnico. Então a SALA da conversa é o token do rastreio: quem tem o
link fala naquela conversa e em nenhuma outra.

Isso resolve de graça três coisas que um chat genérico exigiria construir:
identidade (é o dono do link), escopo (uma conversa por atendimento) e
validade (o link expira junto com o atendimento).

POLLING, NÃO WEBSOCKET — pela mesma razão registrada no auto-refresh: o
gunicorn roda com `--workers 1 --threads 8`, e cada conexão aberta prenderia
uma thread. Oito clientes com o chat aberto travariam a aplicação inteira.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import IS_PG, db_conn, execute, fetch_all, fetch_one

log = logging.getLogger("portotec.chat")

chat_bp = Blueprint("chat", __name__)

# Texto maior que isso é engano ou abuso — e a caixa do chat nem comporta.
TAMANHO_MAXIMO = 1000

_ATIVO = "ativo IS TRUE" if IS_PG else "ativo = 1"


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def publicar(conn, sala: str, texto: str, autor_tipo: str = "sistema",
             autor_nome: str = "Porto Tec") -> None:
    """Grava uma mensagem. Usado também pelo aviso automático de "a caminho",
    por isso recebe a conexão de fora — para entrar na mesma transação de quem
    chamou, e não sobrar mensagem de um rastreio que falhou ao ser criado."""
    execute(conn, """
        INSERT INTO mensagens (sala, autor_tipo, autor_nome, texto, criado_em)
        VALUES (?, ?, ?, ?, ?)
    """, (sala, autor_tipo, autor_nome, texto[:TAMANHO_MAXIMO], _agora()))


def _rastreio_da_sala(conn, sala: str):
    return fetch_one(conn, """
        SELECT ra.token, ra.criado_em, sv.cliente, t.nome AS tecnico
          FROM rastreios ra
          JOIN servicos sv ON sv.id = ra.servico_id
          JOIN tecnicos t  ON t.id = ra.tecnico_id
         WHERE ra.token = ?
    """, (sala,))


# ─── Lado do CLIENTE (público, a sala é o token do link) ────────────────
@chat_bp.route("/chat/<sala>", methods=["GET"])
def ler(sala):
    """Mensagens da conversa. Público: quem tem o link é o dono da conversa.

    `desde` permite buscar só o que chegou depois — o chat pergunta de 8 em 8
    segundos e não faz sentido rebaixar a conversa inteira toda vez.
    """
    try:
        desde = int(request.args.get("desde") or 0)
    except (TypeError, ValueError):
        desde = 0

    with db_conn() as conn:
        if not _rastreio_da_sala(conn, sala):
            return jsonify({"erro": "Conversa não encontrada"}), 404

        linhas = fetch_all(conn, """
            SELECT id, autor_tipo, autor_nome, texto, criado_em
              FROM mensagens WHERE sala = ? AND id > ?
             ORDER BY id
        """, (sala, desde))

    return jsonify({"mensagens": linhas,
                    "ultimo_id": linhas[-1]["id"] if linhas else desde})


@chat_bp.route("/chat/<sala>", methods=["POST"])
def escrever(sala):
    """O cliente manda mensagem. Também público, mesmo motivo."""
    texto = ((request.get_json(silent=True) or {}).get("texto") or "").strip()
    if not texto:
        return jsonify({"erro": "Escreva alguma coisa"}), 400

    with db_conn(commit=True) as conn:
        r = _rastreio_da_sala(conn, sala)
        if not r:
            return jsonify({"erro": "Conversa não encontrada"}), 404

        publicar(conn, sala, texto, autor_tipo="cliente",
                 autor_nome=r.get("cliente") or "Cliente")

    return jsonify({"ok": True}), 201


# ─── Lado da EMPRESA (painel, exige login) ──────────────────────────────
@chat_bp.route("/chat/conversas", methods=["GET"])
def conversas():
    """Conversas com mensagem, mais recente primeiro — a caixa de entrada."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401

    with db_conn() as conn:
        linhas = fetch_all(conn, f"""
            SELECT m.sala,
                   COUNT(*) AS total,
                   MAX(m.id) AS ultimo_id,
                   SUM(CASE WHEN m.autor_tipo = 'cliente' AND m.lida = {'FALSE' if IS_PG else '0'}
                            THEN 1 ELSE 0 END) AS nao_lidas,
                   sv.cliente, t.nome AS tecnico, ra.ativo
              FROM mensagens m
              JOIN rastreios ra ON ra.token = m.sala
              JOIN servicos sv  ON sv.id = ra.servico_id
              JOIN tecnicos t   ON t.id = ra.tecnico_id
             GROUP BY m.sala, sv.cliente, t.nome, ra.ativo
             ORDER BY MAX(m.id) DESC
        """)

    # Não lidas conta em CIMA de todas as conversas — corta antes disso e o
    # badge do painel mentiria pro que ficou de fora dos 50 primeiros.
    total_nao_lidas = sum(int(l.get("nao_lidas") or 0) for l in linhas)
    linhas = linhas[:50]

    # Última mensagem de cada conversa, para a lista mostrar prévia. Só depois
    # do corte: buscar isso pra TODA conversa e descartar o resto no final era
    # 1 SELECT a mais por conversa que nunca aparecia na tela.
    with db_conn() as conn:
        for l in linhas:
            ult = fetch_one(conn, """
                SELECT texto, autor_tipo, criado_em FROM mensagens
                 WHERE sala = ? ORDER BY id DESC
            """, (l["sala"],))
            l["ultima"] = ult or {}

    return jsonify({"conversas": linhas, "nao_lidas": total_nao_lidas})


@chat_bp.route("/chat/<sala>/responder", methods=["POST"])
def responder(sala):
    """A empresa responde. Marca as do cliente como lidas na mesma passada —
    se você está respondendo, obviamente leu."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401

    texto = ((request.get_json(silent=True) or {}).get("texto") or "").strip()
    if not texto:
        return jsonify({"erro": "Escreva alguma coisa"}), 400

    autor = session.get("usuario_nome") or "Porto Tec"

    with db_conn(commit=True) as conn:
        if not _rastreio_da_sala(conn, sala):
            return jsonify({"erro": "Conversa não encontrada"}), 404
        publicar(conn, sala, texto, autor_tipo="empresa", autor_nome=autor)
        execute(conn, f"""
            UPDATE mensagens SET lida = {'TRUE' if IS_PG else '1'}
             WHERE sala = ? AND autor_tipo = 'cliente'
        """, (sala,))

    return jsonify({"ok": True}), 201


@chat_bp.route("/chat/<sala>/lida", methods=["PUT"])
def marcar_lida(sala):
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401

    with db_conn(commit=True) as conn:
        execute(conn, f"""
            UPDATE mensagens SET lida = {'TRUE' if IS_PG else '1'}
             WHERE sala = ? AND autor_tipo = 'cliente'
        """, (sala,))
    return jsonify({"ok": True})


# ─── Apagar conversa (só admin) ─────────────────────────────────────────
@chat_bp.route("/chat/<sala>", methods=["DELETE"])
def apagar_conversa(sala):
    """Remove a conversa inteira de um atendimento.

    Só admin: apagar conversa é destruir registro do que foi combinado com o
    cliente. O rastreio e o atendimento continuam — some a conversa, não o
    trabalho.
    """
    from routes.auth import e_admin
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode apagar conversas"}), 403

    with db_conn(commit=True) as conn:
        apagadas = execute(conn, "DELETE FROM mensagens WHERE sala = ?", (sala,))

    return jsonify({"mensagem": f"{apagadas} mensagem(ns) apagada(s)",
                    "apagadas": apagadas})


# ─── Chat da EQUIPE ─────────────────────────────────────────────────────
#
# Sala fixa 'equipe', só para o PAINEL (sessão de admin/recepcionista). Fica
# em rotas PRÓPRIAS, e não em /chat/<sala>, por segurança: o caminho
# /api/chat/ é público (o link do cliente é a credencial dele). Se a conversa
# interna morasse lá, qualquer pessoa de fora leria o que a equipe combina só
# digitando o endereço.
#
# O técnico em campo NÃO tem porta pra essa sala (removido em 2026-08-29):
# ele via nome e mensagem de OUTROS técnicos ali, o que a Porto Tec não quer
# — cada um deve ver só a própria rota no celular.
SALA_EQUIPE = "equipe"


def _mensagens_equipe(desde: int):
    with db_conn() as conn:
        return fetch_all(conn, """
            SELECT id, autor_tipo, autor_nome, texto, criado_em
              FROM mensagens WHERE sala = ? AND id > ?
             ORDER BY id
        """, (SALA_EQUIPE, desde))


def _desde():
    try:
        return int(request.args.get("desde") or 0)
    except (TypeError, ValueError):
        return 0


@chat_bp.route("/equipe/mensagens", methods=["GET"])
def equipe_ler():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    linhas = _mensagens_equipe(_desde())
    return jsonify({"mensagens": linhas,
                    "ultimo_id": linhas[-1]["id"] if linhas else _desde()})


@chat_bp.route("/equipe/mensagens", methods=["POST"])
def equipe_escrever():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401

    texto = ((request.get_json(silent=True) or {}).get("texto") or "").strip()
    if not texto:
        return jsonify({"erro": "Escreva alguma coisa"}), 400

    with db_conn(commit=True) as conn:
        publicar(conn, SALA_EQUIPE, texto,
                 autor_tipo=session.get("papel") or "admin",
                 autor_nome=session.get("usuario_nome") or "Administrador")
    return jsonify({"ok": True}), 201
