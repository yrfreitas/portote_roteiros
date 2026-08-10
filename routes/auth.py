import os

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from extensions import limiter

auth_bp = Blueprint("auth", __name__)


def _hash_admin() -> str:
    return os.environ.get("ADMIN_PASSWORD_HASH", "")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if request.method == "GET":
        if session.get("admin"):
            return redirect(url_for("index"))
        return render_template("login.html", erro=None)

    senha = request.form.get("senha", "")
    hash_configurado = _hash_admin()

    if not hash_configurado:
        return render_template(
            "login.html",
            erro="ADMIN_PASSWORD_HASH não está configurada no servidor.",
        ), 500

    if not senha or not check_password_hash(hash_configurado, senha):
        return render_template("login.html", erro="Senha incorreta."), 401

    session.clear()
    session["admin"] = True
    session.permanent = True

    destino = request.args.get("next") or ""
    if not destino.startswith("/") or destino.startswith("//"):
        destino = url_for("index")
    return redirect(destino)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
