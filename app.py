from dotenv import load_dotenv

load_dotenv()

import logging
import os
import secrets

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from database import init_db
from routes.fichas import fichas_bp
from routes.servicos import servicos_bp
from routes.tecnicos import tecnicos_bp

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("portotec")

app = Flask(__name__)

_secret = os.environ.get("SECRET_KEY")
if not _secret:
    _secret = secrets.token_hex(32)
    log.warning(
        "SECRET_KEY não definida — gerada uma temporária. "
        "Defina SECRET_KEY nas variáveis de ambiente do Railway."
    )
app.config["SECRET_KEY"] = _secret
app.config["JSON_SORT_KEYS"] = False

_origens = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if _origens:
    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": _origens}})
    log.info("CORS liberado para: %s", ", ".join(_origens))

init_db()

app.register_blueprint(fichas_bp, url_prefix="/api")
app.register_blueprint(servicos_bp, url_prefix="/api")
app.register_blueprint(tecnicos_bp, url_prefix="/api")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


def _e_api() -> bool:
    return request.path.startswith("/api")


@app.errorhandler(HTTPException)
def erro_http(e):
    if _e_api():
        return jsonify({"erro": e.description, "status": e.code}), e.code
    return e


@app.errorhandler(Exception)
def erro_inesperado(e):
    log.exception("Erro não tratado em %s %s", request.method, request.path)
    if _e_api():
        return jsonify({
            "erro": "Erro interno no servidor. "
                    "Se persistir, verifique os logs da aplicação."
        }), 500
    return "<h1>Erro interno</h1>", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)