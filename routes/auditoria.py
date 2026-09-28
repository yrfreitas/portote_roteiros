"""Log de auditoria (item #16 da lista de melhorias, 2026-09-28) -- "quem
editou/apagou o quê". Visibilidade travada pro admin-mestre (o login só-
senha, o dono do sistema), de propósito -- não é uma permissão que passa
pelo editor de Acessos como as outras (ver permissoes.py), é decisão de
quem manda, fora do alcance de qualquer login nomeado (JP, Kauê etc.),
mesmo que tenham papel='admin'.

Achado importante ao implementar: `session["admin"] = True` (ver
routes/auth.py) é setado TANTO pelo login só-senha QUANTO por todo login
nomeado -- é "está autenticado no painel", não "é o admin-mestre". O que
distingue de verdade é `session.get("usuario_id")`: só existe pra quem
logou com usuário/senha (tem linha em `usuarios`); o admin-mestre nunca
tem.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import db_conn, execute, fetch_all, sql

auditoria_bp = Blueprint("auditoria", __name__)


def eh_admin_mestre() -> bool:
    return bool(session.get("admin")) and not session.get("usuario_id")


def registrar(conn, acao: str, entidade: str = None, entidade_id=None, detalhe: str = None) -> None:
    """Chamado de DENTRO de uma rota de escrita já autenticada, na MESMA
    conexão/transação da ação (se a ação for revertida por erro depois, o
    log some junto -- não faz sentido registrar algo que não aconteceu).
    `quem` sempre é quem está de fato logado, admin-mestre ou nomeado --
    aqui é só REGISTRO, a restrição de quem CONSULTA depois é outra coisa."""
    execute(conn, sql(
        "INSERT INTO auditoria (quem, acao, entidade, entidade_id, detalhe, criado_em) "
        "VALUES (?, ?, ?, ?, ?, ?)"),
        (session.get("usuario_nome") or "Administrador", acao, entidade,
         str(entidade_id) if entidade_id is not None else None, detalhe,
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))


@auditoria_bp.route("/auditoria", methods=["GET"])
def listar():
    if not eh_admin_mestre():
        return jsonify({"erro": "Sem permissão"}), 403
    limite = min(int(request.args.get("limite", 200) or 200), 1000)
    with db_conn() as conn:
        linhas = fetch_all(conn, sql(
            "SELECT * FROM auditoria ORDER BY id DESC LIMIT ?"), (limite,))
    return jsonify({"linhas": linhas})
