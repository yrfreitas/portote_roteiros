from flask import Blueprint, render_template

from database import db_conn, fetch_one
from services.push import VAPID_PUBLIC_KEY

tecnico_view_bp = Blueprint("tecnico_view", __name__)


@tecnico_view_bp.route("/tecnico/<token>")
def pagina_tecnico(token):
    with db_conn() as conn:
        tecnico = fetch_one(conn, "SELECT id, nome, cor FROM tecnicos WHERE token = ?", (token,))

    if not tecnico:
        return render_template("tecnico_invalido.html"), 404

    return render_template(
        "tecnico.html", tecnico=tecnico, token=token, vapid_public_key=VAPID_PUBLIC_KEY
    )
