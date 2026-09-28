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

PAPEIS = ("admin", "tecnico", "recepcionista")


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

    destino = request.args.get("next") or ""
    if not destino.startswith("/") or destino.startswith("//"):
        destino = url_for("index")

    if usuario:
        if not usuario.get("ativo"):
            return render_template("login.html",
                                   erro="Este acesso está desativado."), 401
        if not check_password_hash(usuario["senha_hash"], senha):
            return render_template("login.html", erro="Usuário ou senha incorretos."), 401

        # 2FA (item #17, opt-in -- totp_ativo nasce falso pra todo mundo,
        # ver database.py). Senha já validada; falta só o código antes de
        # abrir a sessão de verdade.
        if usuario.get("totp_ativo"):
            session.clear()
            session["_2fa_usuario_id"] = usuario["id"]
            session["_2fa_destino"] = destino
            return render_template("login.html", pedir_2fa=True, erro=None)

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

        with db_conn() as conn:
            cfg_2fa = fetch_one(conn, "SELECT totp_ativo FROM admin_mestre_2fa WHERE id = 1")
        if cfg_2fa and cfg_2fa.get("totp_ativo"):
            session.clear()
            session["_2fa_admin_mestre"] = True
            session["_2fa_destino"] = destino
            return render_template("login.html", pedir_2fa=True, erro=None)

        session.clear()
        session["admin"] = True
        session["papel"] = "admin"
        session["usuario_nome"] = "Administrador"
        session.permanent = True

    return redirect(destino)


@auth_bp.route("/login/2fa", methods=["POST"])
@limiter.limit("10 per minute")
def login_2fa():
    """Segundo passo do login quando a conta tem 2FA ativado (ver login()
    acima). Código errado NÃO revela se o problema foi o código ou a
    sessão pendente ter expirado -- mesma mensagem genérica pros dois."""
    from services.totp import verificar_codigo

    codigo = (request.form.get("codigo") or "").strip()
    destino = session.get("_2fa_destino") or url_for("index")

    usuario_id = session.get("_2fa_usuario_id")
    admin_mestre_pendente = session.get("_2fa_admin_mestre")

    if usuario_id:
        with db_conn() as conn:
            usuario = fetch_one(conn, "SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        if not usuario or not usuario.get("totp_ativo") \
                or not verificar_codigo(usuario.get("totp_secret"), codigo):
            return render_template("login.html", pedir_2fa=True, erro="Código inválido."), 401

        session.clear()
        session["admin"] = True
        session["usuario_id"] = usuario["id"]
        session["usuario_nome"] = usuario["nome"]
        session["papel"] = usuario["papel"]
        session["tecnico_id"] = usuario.get("tecnico_id")
        session.permanent = True
        with db_conn(commit=True) as conn:
            execute(conn, "UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?",
                    (_agora(), usuario["id"]))
        return redirect(destino)

    if admin_mestre_pendente:
        with db_conn() as conn:
            cfg = fetch_one(conn, "SELECT totp_secret, totp_ativo FROM admin_mestre_2fa WHERE id = 1")
        if not cfg or not cfg.get("totp_ativo") or not verificar_codigo(cfg.get("totp_secret"), codigo):
            return render_template("login.html", pedir_2fa=True, erro="Código inválido."), 401

        session.clear()
        session["admin"] = True
        session["papel"] = "admin"
        session["usuario_nome"] = "Administrador"
        session.permanent = True
        return redirect(destino)

    # Sessão pendente expirou ou nunca existiu (ex: recarregou a página de
    # código depois de muito tempo) -- volta pro login normal em vez de
    # mostrar um formulário de código que não leva a lugar nenhum.
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/eu", methods=["GET"])
def eu():
    """Quem sou eu — o painel usa para esconder o que a pessoa não pode.
    Inclui as permissões EFETIVAS (papel + ajustes) já resolvidas."""
    from permissoes import _caps_do_request
    dados = usuario_atual()
    dados["permissoes"] = _caps_do_request()
    # Log de auditoria (#16) é visível só pro admin-mestre -- ver
    # routes/auditoria.py::eh_admin_mestre pro porquê de não usar só
    # session['admin'] (isso também é True pra login nomeado com papel=admin).
    dados["admin_mestre"] = bool(session.get("admin")) and not session.get("usuario_id")

    # Token do próprio técnico, só pra quem é técnico — o painel usa pra
    # chamar as MESMAS rotas de almoço do celular de campo (/api/t/<token>/
    # almoco...) sem precisar duplicar endpoint nenhum. Pedido de 2026-08-31:
    # login de técnico cai no painel (não no link pessoal), e o botão de
    # almoço só existia lá.
    if dados.get("papel") == "tecnico" and dados.get("tecnico_id"):
        with db_conn() as conn:
            tecnico = fetch_one(conn, "SELECT token FROM tecnicos WHERE id = ?",
                                (dados["tecnico_id"],))
        dados["tecnico_token"] = tecnico["token"] if tecnico else None

    return jsonify(dados)


def _alvo_2fa():
    """(tabela, filtro) da CONTA LOGADA AGORA -- usuário nomeado ou
    admin-mestre. 2FA é por conta, cada um ativa a própria; não existe
    "ativar 2FA de outra pessoa" nesta feature."""
    usuario_id = session.get("usuario_id")
    if usuario_id:
        return "usuarios", usuario_id
    return "admin_mestre_2fa", 1


@auth_bp.route("/api/2fa/status", methods=["GET"])
def status_2fa():
    tabela, filtro = _alvo_2fa()
    with db_conn() as conn:
        linha = fetch_one(conn, f"SELECT totp_ativo FROM {tabela} WHERE id = ?", (filtro,))
    return jsonify({"ativo": bool(linha and linha.get("totp_ativo"))})


@auth_bp.route("/api/2fa/ativar", methods=["POST"])
def ativar_2fa():
    """Gera um segredo NOVO (ainda não ativa -- só ativa depois de
    /api/2fa/confirmar provar que a pessoa escaneou certo). Gerar de novo
    invalida qualquer QR mostrado antes e nunca confirmado -- sem isso, um
    QR esquecido aberto numa aba velha continuaria válido pra sempre."""
    from services.totp import gerar_secret, qr_data_uri, uri_provisionamento

    tabela, filtro = _alvo_2fa()
    secret = gerar_secret()
    conta = session.get("usuario_nome") or "Administrador"

    with db_conn(commit=True) as conn:
        if tabela == "admin_mestre_2fa":
            existe = fetch_one(conn, "SELECT id FROM admin_mestre_2fa WHERE id = 1")
            if existe:
                execute(conn, "UPDATE admin_mestre_2fa SET totp_secret = ?, totp_ativo = ? WHERE id = 1",
                       (secret, False))
            else:
                execute(conn, "INSERT INTO admin_mestre_2fa (id, totp_secret, totp_ativo) VALUES (1, ?, ?)",
                       (secret, False))
        else:
            execute(conn, "UPDATE usuarios SET totp_secret = ?, totp_ativo = ? WHERE id = ?",
                   (secret, False, filtro))

    uri = uri_provisionamento(secret, conta)
    return jsonify({"secret": secret, "qr": qr_data_uri(uri), "uri": uri})


@auth_bp.route("/api/2fa/confirmar", methods=["POST"])
def confirmar_2fa():
    from services.totp import verificar_codigo

    codigo = (request.get_json(silent=True) or {}).get("codigo", "").strip()
    tabela, filtro = _alvo_2fa()
    with db_conn() as conn:
        linha = fetch_one(conn, f"SELECT totp_secret FROM {tabela} WHERE id = ?", (filtro,))
    if not linha or not verificar_codigo(linha.get("totp_secret"), codigo):
        return jsonify({"erro": "Código inválido. Confira o horário do celular e tente de novo."}), 400

    with db_conn(commit=True) as conn:
        execute(conn, f"UPDATE {tabela} SET totp_ativo = ? WHERE id = ?", (True, filtro))
    return jsonify({"mensagem": "2FA ativado. Da próxima vez, o login vai pedir o código."})


@auth_bp.route("/api/2fa/desativar", methods=["POST"])
def desativar_2fa():
    tabela, filtro = _alvo_2fa()
    with db_conn(commit=True) as conn:
        execute(conn, f"UPDATE {tabela} SET totp_ativo = ?, totp_secret = NULL WHERE id = ?",
               (False, filtro))
    return jsonify({"mensagem": "2FA desativado."})


@auth_bp.route("/api/permissoes/catalogo", methods=["GET"])
def catalogo_permissoes():
    """Lista de ações que dá para ligar/desligar — alimenta o editor."""
    if not e_admin():
        return jsonify({"erro": "Só o administrador"}), 403
    from permissoes import CATALOGO
    return jsonify({"catalogo": CATALOGO})


# ─── Cadastro de pessoas (só admin) ─────────────────────────────────────
@auth_bp.route("/api/usuarios", methods=["GET"])
def listar_usuarios():
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode ver os acessos"}), 403

    from permissoes import efetivas
    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT u.id, u.nome, u.login, u.papel, u.tecnico_id, u.ativo,
                   u.permissoes, u.criado_em, u.ultimo_acesso, t.nome AS tecnico_nome
              FROM usuarios u
              LEFT JOIN tecnicos t ON t.id = u.tecnico_id
             ORDER BY u.papel, u.nome
        """)
    for u in linhas:
        # Permissões já resolvidas (papel + ajustes), para o editor marcar certo.
        u["permissoes"] = efetivas(u.get("papel"), u.get("permissoes"))
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


@auth_bp.route("/api/usuarios/<int:usuario_id>/permissoes", methods=["PUT"])
def salvar_permissoes(usuario_id):
    """Grava as permissões de um usuário (o editor manda o mapa {acao: bool}).

    Não deixa mexer nas próprias permissões (evita o admin se auto-trancar) e
    ignora chave que não está no catálogo (lixo não vira permissão)."""
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode mudar permissões"}), 403
    if usuario_id == session.get("usuario_id"):
        return jsonify({"erro": "Você não pode mudar as próprias permissões"}), 400

    import json as _json

    from permissoes import TODAS
    data = request.get_json(silent=True) or {}
    entra = data.get("permissoes") or {}
    limpo = {a: bool(entra[a]) for a in TODAS if a in entra}

    with db_conn(commit=True) as conn:
        usuario = fetch_one(conn, "SELECT id, papel FROM usuarios WHERE id = ?", (usuario_id,))
        if not usuario:
            return jsonify({"erro": "Usuário não encontrado"}), 404
        # Admin tem tudo por definição — guardar ajuste nele só confunde.
        if usuario.get("papel") == "admin":
            return jsonify({"erro": "Administrador já tem todas as permissões. "
                            "Baixe o papel para 'técnico' antes de restringir."}), 400
        execute(conn, "UPDATE usuarios SET permissoes = ? WHERE id = ?",
                (_json.dumps(limpo), usuario_id))
        from routes.auditoria import registrar
        registrar(conn, "alterar_permissoes", "usuarios", usuario_id, _json.dumps(limpo))

    return jsonify({"mensagem": "Permissões atualizadas"})


@auth_bp.route("/api/usuarios/<int:usuario_id>", methods=["DELETE"])
def remover_usuario(usuario_id):
    if not e_admin():
        return jsonify({"erro": "Só o administrador pode remover acessos"}), 403
    if usuario_id == session.get("usuario_id"):
        return jsonify({"erro": "Você não pode remover o próprio acesso"}), 400

    with db_conn(commit=True) as conn:
        apagados = execute(conn, "DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        if apagados:
            from routes.auditoria import registrar
            registrar(conn, "remover_usuario", "usuarios", usuario_id)

    if not apagados:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    return jsonify({"mensagem": "Acesso removido"})
