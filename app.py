from dotenv import load_dotenv

load_dotenv()

import logging
import os
import secrets
from datetime import timedelta

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from database import bump_revisao, db_conn, init_db, ler_revisao
from extensions import limiter
from routes.auth import auth_bp
from routes.fichas import fichas_bp
from routes.pedidos import pedidos_bp
from routes.rastreio import rastreio_bp
from routes.relatorios import relatorios_bp
from routes.servicos import servicos_bp
from routes.setores import setores_bp
from routes.tecnico_api import tecnico_api_bp
from routes.tecnico_view import tecnico_view_bp
from routes.tecnicos import tecnicos_bp

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("portotec")

app = Flask(__name__)

# O Railway serve a aplicação atrás de um proxy reverso. Sem isso, o Flask lê o
# IP da borda da Railway em vez do IP de quem realmente chamou — o que fazia o
# rate limiting contar todo mundo como se fosse um cliente só (confirmado em
# 2026-08-12: 44 tentativas de login erradas seguidas, nenhuma bloqueada).
# x_for/x_proto=1 = confiar em exatamente UM proxy à frente. Confiar em mais do
# que existe permitiria a um cliente forjar o próprio IP via X-Forwarded-For.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

_secret = os.environ.get("SECRET_KEY")
if not _secret:
    _secret = secrets.token_hex(32)
    log.warning(
        "SECRET_KEY não definida — gerada uma temporária. "
        "Defina SECRET_KEY nas variáveis de ambiente do Railway."
    )
app.config["SECRET_KEY"] = _secret
app.config["JSON_SORT_KEYS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# O cookie de sessão só pode trafegar por HTTPS. Fica desligado quando
# FLASK_DEBUG está ativo porque o servidor de desenvolvimento roda em HTTP puro —
# com Secure=True o navegador simplesmente descarta o cookie e o login local
# entra em laço infinito de "senha correta mas continua deslogado".
_debug_local = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
app.config["SESSION_COOKIE_SECURE"] = not _debug_local

_origens = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if _origens:
    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": _origens}})
    log.info("CORS liberado para: %s", ", ".join(_origens))

limiter.init_app(app)

init_db()

app.register_blueprint(auth_bp)
app.register_blueprint(fichas_bp, url_prefix="/api")
app.register_blueprint(servicos_bp, url_prefix="/api")
app.register_blueprint(tecnicos_bp, url_prefix="/api")
app.register_blueprint(relatorios_bp, url_prefix="/api")
app.register_blueprint(pedidos_bp, url_prefix="/api")
app.register_blueprint(setores_bp, url_prefix="/api")
app.register_blueprint(tecnico_api_bp, url_prefix="/api/t")
app.register_blueprint(tecnico_view_bp)
app.register_blueprint(rastreio_bp, url_prefix="/api")


def _e_api() -> bool:
    return request.path.startswith("/api")


_CAMINHOS_PUBLICOS = {"/login", "/api/health"}
# /acompanhar/ e /api/rastreio/ são públicos porque quem abre é o CLIENTE, que
# não tem conta no sistema. O link de 16 bytes é a credencial — mesmo modelo do
# link do técnico. Só expõem posição e destino daquele atendimento.
_PREFIXOS_PUBLICOS = ("/static/", "/tecnico/", "/api/t/",
                      "/acompanhar/", "/api/rastreio/")


@app.before_request
def _exigir_autenticacao():
    if request.path in _CAMINHOS_PUBLICOS or request.path.startswith(_PREFIXOS_PUBLICOS):
        return
    if session.get("admin"):
        return
    if _e_api():
        return jsonify({"erro": "Não autenticado"}), 401
    return redirect(url_for("auth.login", next=request.path))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/acompanhar/<token>")
def acompanhar(token):
    """Página pública onde o cliente vê o técnico a caminho.

    Sem login de propósito: o cliente não tem conta. O link é a credencial,
    mesmo modelo do link do técnico. Fica aqui e não no blueprint de rastreio
    porque lá tudo vive sob /api — isto é HTML.
    """
    return render_template("acompanhar.html", token=token)


# ─── Auto-refresh: quem está com a tela aberta vê a mudança sozinho ──────
# O navegador pergunta a revisão a cada poucos segundos e só recarrega dados
# de verdade quando o número mudou. Duas decisões por trás disso:
#
# 1. Polling e não WebSocket/SSE. O gunicorn roda com 1 worker e 8 threads
#    (ver Procfile); cada conexão SSE aberta prenderia UMA thread pelo tempo
#    todo, então oito abas abertas travariam a aplicação inteira. Polling não
#    segura thread, sobrevive a restart do Railway e atravessa proxy sem
#    tratamento especial.
# 2. O bump vive num after_request central, e não espalhado pelas rotas de
#    escrita — mesmo motivo do _exigir_autenticacao: numa rota nova, é
#    impossível esquecer de chamar.
_METODOS_DE_ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}


@app.after_request
def _marcar_revisao(resp):
    if request.method not in _METODOS_DE_ESCRITA:
        return resp
    if not request.path.startswith("/api"):
        return resp
    # 4xx/5xx não mudaram nada no banco. Bumpar aqui faria todo mundo
    # rebaixar dados à toa a cada tentativa malsucedida.
    if resp.status_code >= 400:
        return resp

    try:
        with db_conn(commit=True) as conn:
            bump_revisao(conn)
    except Exception:
        # A escrita do usuário já foi concluída com sucesso — derrubar a
        # resposta agora por causa do contador seria trocar um problema
        # cosmético (alguém aperta F5) por perda de trabalho real.
        log.exception("Falha ao incrementar a revisão em %s", request.path)

    return resp


@app.route("/api/versao")
def versao():
    with db_conn() as conn:
        return jsonify(ler_revisao(conn))


# 'unsafe-inline' em script-src é uma concessão consciente: index.html e app.js
# usam handlers onclick= inline em dezenas de lugares, e uma CSP estrita
# quebraria o painel inteiro. A proteção que de fato importa aqui é
# frame-ancestors 'none' (impede o painel de ser embutido em iframe alheio, base
# do clickjacking) somada a object-src/base-uri/form-action. Para endurecer o
# script-src depois, é preciso antes migrar os onclick para addEventListener.
_CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://unpkg.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://unpkg.com",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
])


@app.after_request
def _headers_de_seguranca(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), payment=()")
    resp.headers.setdefault("Content-Security-Policy", _CSP)

    # HSTS só faz sentido (e só é honrado) sobre HTTPS. Enviar em HTTP local
    # não quebra nada, mas sujar o header à toa não ajuda ninguém a depurar.
    # request.is_secure funciona porque o ProxyFix já traduziu X-Forwarded-Proto.
    if request.is_secure:
        resp.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return resp


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