"""Login com PESSOAS e PAPÉIS, no lugar de uma senha única.

Até 2026-08-17 havia uma senha só de admin: o sistema sabia que "alguém
logado" agiu, nunca quem. Com dois técnicos em campo isso parou de servir, e
o Kalebe pediu explicitamente que o técnico não veja o diagnóstico nem o
resto do que é de desenvolvedor.

DOIS PAPÉIS, e a diferença é de VISÃO, não só de tela:
  admin    — tudo, inclusive diagnóstico, erros do sistema e cadastro de gente
  tecnico  — as rotas e o trabalho do dia; nada de manutenção do sistema

A PORTA DOS FUNDOS QUE FICA (de propósito): a senha antiga do
ADMIN_PASSWORD_HASH continua valendo, entrando como administrador. Sem isso,
qualquer erro nesta migração trancaria o Kalebe para fora do próprio sistema
— e o jeito de destrancar seria mexer no banco de produção às pressas.
"""
import os
from datetime import datetime, timezone

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from database import db_conn, execute, fetch_all, fetch_one, insert_returning_id
from extensions import limiter

auth_bp = Blueprint("auth", __name__)

PAPEIS = ("admin", "tecnico")


def _hash_admin() -> str:
    return os.environ.get("ADMIN_PASSWORD_HASH", "")


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def usuario_atual() -> dict:
    """Quem está logado, do jeito que o resto do sistema pergunta."""
    return {
        "id": session.get("usuario_id"),
        "nome": session.get("usuario_nome") or "Administrador",
        "papel": session.get("papel") or ("admin" if session.get("admin") else None),
        "tecnico_id": session.get("tecnico_id"),
    }


def e_admin() -> bool:
    return usuario_atual().get("papel") == "admin"


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "GET":
        if session.get("admin"):
            return redirect(url_for("index"))
        return render_template("login.html", erro=None)

    login_digitado = (request.form.get("usuario") or "").strip().lower()
    senha = request.form.get("senha", "")

    if not senha:
        return render_template("login.html", erro="Informe a senha."), 401

    usuario = None
    if login_digitado:
        with db_conn() as conn:
            usuario = fetch_one(
                conn, "SELECT * FROM usuarios WHERE LOWER(login) = ?",
                (login_digitado,))

    if usuario:
        if not usuario.get("ativo"):
            return render_template("login.html",
                                   erro="Este acesso está desativado."), 401
        if not check_password_hash(usuario["senha_hash"], senha):
            return render_template("login.html", erro="Usuário ou senha incorretos."), 401

        session.clear()
        session["admin"] = True            # mantém o before_request existente
        session["usuario_id"] = usuario["id"]
        session["usuario_nome"] = usuario["nome"]
        session["papel"] = usuario["papel"]
        session["tecnico_id"] = usuario.get("tecnico_id")
        session.permanent = True

        with db_conn(commit=True) as conn:
            execute(conn, "UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?",
                    (_agora(), usuario["id"]))

    else:
        # Caminho antigo: só a senha, entra como administrador. É a porta que
        # impede a migração trancar o dono do sistema para fora.
        hash_configurado = _hash_admin()
        if not hash_configurado:
            return render_template(
                "login.html",
                erro="ADMIN_PASSWORD_HASH não está configurada no servidor."), 500
        if not check_password_hash(hash_configurado, senha):
            return render_template("login.html", erro="Usuário ou senha incorretos."), 401

        session.clear()
        session["admin"] = True
        session["papel"] = "admin"
        session["usuario_nome"] = "Administrador"
        session.permanent = True

    destino = request.args.get("next") or ""
    if not destino.startswith("/") or destino.startswith("//"):
        destino = url_for("index")
    return redirect(destino)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/eu", methods=["GET"])
def eu():
    """Quem sou eu — o painel usa para esconder o que não é do papel."""
    return jsonify(usuario_atual())


# ─── Cadastro de pessoas (só admin) ─────────────────────────────────────
@auth_bp.route("/api/usuarios", methods=["GET"])
def listar_usuarios():
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode ver os acessos"}), 403

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT u.id, u.nome, u.login, u.papel, u.tecnico_id, u.ativo,
                   u.criado_em, u.ultimo_acesso, t.nome AS tecnico_nome
              FROM usuarios u
              LEFT JOIN tecnicos t ON t.id = u.tecnico_id
             ORDER BY u.papel, u.nome
        """)
    return jsonify({"usuarios": linhas})


@auth_bp.route("/api/usuarios", methods=["POST"])
def criar_usuario():
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode criar acessos"}), 403

    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    login_novo = (data.get("login") or "").strip().lower()
    senha = data.get("senha") or ""
    papel = (data.get("papel") or "tecnico").strip()

    if not nome or not login_novo:
        return jsonify({"erro": "Nome e usuário são obrigatórios"}), 400
    if papel not in PAPEIS:
        return jsonify({"erro": "Papel inválido"}), 400
    # 6 é pouco, mas é a diferença entre alguém criar o acesso e alguém adiar
    # para depois — o que na prática significa continuar com a senha única.
    if len(senha) < 6:
        return jsonify({"erro": "A senha precisa de pelo menos 6 caracteres"}), 400

    tecnico_id = data.get("tecnico_id")
    try:
        tecnico_id = int(tecnico_id) if tecnico_id else None
    except (TypeError, ValueError):
        tecnico_id = None

    with db_conn(commit=True) as conn:
        if fetch_one(conn, "SELECT id FROM usuarios WHERE LOWER(login) = ?",
                     (login_novo,)):
            return jsonify({"erro": f'Já existe o usuário "{login_novo}"'}), 409

        novo_id = insert_returning_id(conn, """
            INSERT INTO usuarios (nome, login, senha_hash, papel, tecnico_id, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nome, login_novo, generate_password_hash(senha), papel,
              tecnico_id, _agora()))

    return jsonify({"id": novo_id, "nome": nome, "login": login_novo,
                    "papel": papel}), 201


@auth_bp.route("/api/usuarios/<int:usuario_id>", methods=["PUT"])
def editar_usuario(usuario_id):
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode editar acessos"}), 403

    data = request.get_json(silent=True) or {}

    with db_conn(commit=True) as conn:
        usuario = fetch_one(conn, "SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404

        senha = data.get("senha")
        if senha:
            if len(senha) < 6:
                return jsonify({"erro": "A senha precisa de pelo menos 6 caracteres"}), 400
            execute(conn, "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                    (generate_password_hash(senha), usuario_id))

        if "ativo" in data:
            # Trava: desativar o próprio acesso deixaria o sistema sem dono.
            if usuario_id == session.get("usuario_id") and not data.get("ativo"):
                return jsonify({"erro": "Você não pode desativar o próprio acesso"}), 400
            execute(conn, f"UPDATE usuarios SET ativo = {'TRUE' if data.get('ativo') else 'FALSE'} WHERE id = ?"
                    if False else "UPDATE usuarios SET ativo = ? WHERE id = ?",
                    (bool(data.get("ativo")), usuario_id))

        if data.get("papel") in PAPEIS:
            if usuario_id == session.get("usuario_id") and data["papel"] != "admin":
                return jsonify({"erro": "Você não pode tirar o próprio acesso de administrador"}), 400
            execute(conn, "UPDATE usuarios SET papel = ? WHERE id = ?",
                    (data["papel"], usuario_id))

    return jsonify({"mensagem": "Acesso atualizado"})


@auth_bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
def remover_usuario(usuario_id):
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode remover acessos"}), 403
    if usuario_id == session.get("usuario_id"):
        return jsonify({"erro": "Você não pode remover o próprio acesso"}), 400

    with db_conn(commit=True) as conn:
        apagados = execute(conn, "DELETE FROM usuarios WHERE id = ?", (usuario_id,))

    if not apagados:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    return jsonify({"mensagem": "Acesso removido"})
