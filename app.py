from dotenv import load_dotenv

load_dotenv()

import logging
import os
import secrets
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from database import IS_PG, bump_revisao, db_conn, fetch_one, init_db, ler_revisao
from extensions import VERSAO_APP, limiter
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.clientes import clientes_bp
from routes.cotacoes import cotacoes_bp
from routes.estoque import estoque_bp
from routes.ordens_servico import (TERMOS_PADRAO, TERMOS_POR_TIPO,
                                   TIPOS_OS_ROTULO, ordens_servico_bp)
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
# Guardado para o /api/health poder denunciar o problema sem expor o valor:
# sem SECRET_KEY fixa, CADA DEPLOY gera outra chave e derruba a sessão de
# todo mundo. O sintoma é o site "dando erro toda hora" logo depois de uma
# atualização — e ninguém liga uma coisa à outra.
SECRET_DO_AMBIENTE = bool(_secret)
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
app.register_blueprint(chat_bp, url_prefix="/api")
app.register_blueprint(estoque_bp, url_prefix="/api")
app.register_blueprint(cotacoes_bp, url_prefix="/api")
app.register_blueprint(clientes_bp, url_prefix="/api")
app.register_blueprint(ordens_servico_bp, url_prefix="/api")


def _e_api() -> bool:
    return request.path.startswith("/api")


_CAMINHOS_PUBLICOS = {"/login", "/api/health", "/api/erro-cliente"}
# /acompanhar/ e /api/rastreio/ são públicos porque quem abre é o CLIENTE, que
# não tem conta no sistema. O link de 16 bytes é a credencial — mesmo modelo do
# link do técnico. Só expõem posição e destino daquele atendimento.
_PREFIXOS_PUBLICOS = ("/static/", "/tecnico/", "/api/t/",
                      "/acompanhar/", "/api/rastreio/", "/api/chat/")


# Controle de acesso por AÇÃO (ver permissoes.py), no lugar do antigo "só
# admin". Cada área sensível exige uma capacidade que o admin liga/desliga por
# pessoa. Bloqueio no SERVIDOR — esconder o botão sem barrar a rota é decoração.
@app.before_request
def _exigir_permissao():
    if not request.path.startswith("/api"):
        return
    if not session.get("admin"):
        return  # o _exigir_autenticacao abaixo trata quem nem logado está
    from permissoes import checar_acesso
    faltou = checar_acesso(request.path, request.method)
    if faltou:
        return jsonify({"erro": "Você não tem permissão para esta ação",
                        "acao": faltou}), 403


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
    return render_template("index.html", versao=VERSAO_APP)


@app.route("/api/health")
def health():
    """Sinais que explicam falha silenciosa, sem expor nenhum segredo."""
    return jsonify({
        "status": "ok",
        "app": VERSAO_APP,
        # False aqui significa: cada deploy troca a chave e derruba a sessão de
        # todo mundo. É a causa mais provável de "o site fica dando erro toda
        # hora" logo depois de uma atualização.
        "secret_fixa": SECRET_DO_AMBIENTE,
    })


@app.route("/api/erro-cliente", methods=["POST"])
def registrar_erro_cliente():
    """Recebe erro de JavaScript acontecido no navegador de quem usa o sistema.

    Existe porque "o site fica dando erro" é impossível de investigar do
    servidor: as rotas respondem 200 em 0,2s e o defeito mora na tela de outra
    pessoa. Aqui o erro real chega com mensagem, tela e versão do código.

    Público de propósito: erro pode acontecer ANTES ou DEPOIS de a sessão
    valer, e justamente o caso de sessão expirada é o que mais interessa
    registrar. Não grava nada de cliente — só mensagem, origem e versão.
    """
    dados = request.get_json(silent=True) or {}
    mensagem = str(dados.get("mensagem") or "")[:500]
    if not mensagem:
        return jsonify({"ok": False}), 200

    from datetime import datetime, timezone
    from database import execute

    try:
        with db_conn(commit=True) as conn:
            execute(conn, """
                INSERT INTO erros_cliente (quando, origem, versao, url, mensagem)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                  str(dados.get("origem") or "")[:40],
                  str(dados.get("versao") or "")[:20],
                  str(dados.get("url") or "")[:200],
                  mensagem))
            # Mantém só os 200 mais recentes: isto é diagnóstico, não histórico,
            # e tabela de log sem poda cresce para sempre.
            execute(conn, """
                DELETE FROM erros_cliente
                 WHERE id < (SELECT MAX(id) - 200 FROM erros_cliente)
            """)
    except Exception:
        log.exception("Falha ao registrar erro de cliente")
        return jsonify({"ok": False}), 200

    return jsonify({"ok": True}), 200


@app.route("/api/diagnostico/geral", methods=["GET"])
def diagnostico_geral():
    """TUDO que responde "está funcionando?" numa resposta só.

    Existe para o Kalebe parar de depender de mim para saber se o GPS do
    técnico está chegando, se a peça foi para o AgoraOS ou se a planilha
    sincronizou. Cada um desses diagnósticos já existia como endereço solto de
    JSON — o que faltava era juntar e mostrar numa tela.

    Cada bloco vai dentro de try: um serviço externo fora do ar (AgoraOS,
    Google Sheets) não pode derrubar o painel inteiro de saúde, senão a tela
    de diagnóstico quebra justamente quando ela é mais necessária.
    """
    from database import fetch_all

    saida = {"app": VERSAO_APP, "secret_fixa": SECRET_DO_AMBIENTE}

    def bloco(nome, fn):
        try:
            saida[nome] = fn()
        except Exception as exc:
            saida[nome] = {"erro": str(exc)[:200]}

    def _rastreio():
        from routes.rastreio import diagnostico as diag_rastreio
        return diag_rastreio().get_json()

    def _agoraos():
        from services import agoraos
        return agoraos.diagnostico()

    def _planilha():
        from services.nfe import diagnostico_imap
        from services.planilha import diagnostico as diag_planilha
        return {"planilha": diag_planilha(), "email": diagnostico_imap()}

    def _setores():
        with db_conn() as conn:
            orfaos = fetch_all(conn, """
                SELECT COUNT(*) AS total FROM servicos sv
                  JOIN fichas f ON f.id = sv.ficha_id
                 WHERE sv.setor_id IS NULL AND f.status <> 'concluida'
            """)
        return {"sem_setor": (orfaos[0] if orfaos else {}).get("total", 0)}

    def _erros():
        with db_conn() as conn:
            linhas = fetch_all(conn, """
                SELECT id, quando, origem, versao, url, mensagem, status, obs
                  FROM erros_cliente ORDER BY id DESC
            """)
        # abertos = tudo que não foi marcado como resolvido — é o que importa ver.
        abertos = sum(1 for l in linhas if (l.get("status") or "novo") != "resolvido")
        return {"total": len(linhas), "abertos": abertos, "ultimos": linhas[:30]}

    def _ia():
        from services.ia import MODELO, configurado
        return {"configurado": configurado(), "modelo": MODELO}

    bloco("rastreio", _rastreio)
    bloco("agoraos", _agoraos)
    bloco("planilha", _planilha)
    bloco("setores", _setores)
    bloco("ia", _ia)
    bloco("erros", _erros)

    return jsonify(saida)


@app.route("/api/erros-cliente", methods=["GET"])
def listar_erros_cliente():
    """Os últimos erros de navegador. Atrás da permissão de diagnóstico."""
    from database import fetch_all

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT id, quando, origem, versao, url, mensagem, status, obs
              FROM erros_cliente ORDER BY id DESC
        """)
    return jsonify({"total": len(linhas), "erros": linhas[:50]})


# Status válidos de um erro de diagnóstico: do "acabou de aparecer" ao "tratado".
_STATUS_ERRO = ("novo", "investigando", "resolvido", "ignorado")


@app.route("/api/erros-cliente/<int:erro_id>", methods=["PUT"])
def editar_erro_cliente(erro_id):
    """Atualiza status e/ou observação de um erro — a tela de diagnóstico deixa
    de ser só leitura. Só quem tem a permissão de diagnóstico chega aqui."""
    from database import execute, fetch_one

    dados = request.get_json(silent=True) or {}
    campos, valores = [], []
    if "status" in dados:
        st = (dados.get("status") or "").strip()
        if st not in _STATUS_ERRO:
            return jsonify({"erro": f"Status inválido. Use um de: {', '.join(_STATUS_ERRO)}"}), 400
        campos.append("status = ?"); valores.append(st)
    if "obs" in dados:
        campos.append("obs = ?"); valores.append((dados.get("obs") or "").strip()[:500] or None)
    if not campos:
        return jsonify({"mensagem": "Nada para mudar"})

    valores.append(erro_id)
    with db_conn(commit=True) as conn:
        if not fetch_one(conn, "SELECT id FROM erros_cliente WHERE id = ?", (erro_id,)):
            return jsonify({"erro": "Registro não encontrado"}), 404
        execute(conn, f"UPDATE erros_cliente SET {', '.join(campos)} WHERE id = ?", valores)
    return jsonify({"mensagem": "Diagnóstico atualizado"})


@app.route("/api/erros-cliente/<int:erro_id>", methods=["DELETE"])
def remover_erro_cliente(erro_id):
    """Apaga um erro do log de diagnóstico."""
    from database import execute

    with db_conn(commit=True) as conn:
        apagados = execute(conn, "DELETE FROM erros_cliente WHERE id = ?", (erro_id,))
    if not apagados:
        return jsonify({"erro": "Registro não encontrado"}), 404
    return jsonify({"mensagem": "Registro removido"})


@app.route("/api/erros-cliente/<int:erro_id>/analisar", methods=["POST"])
def analisar_erro_cliente(erro_id):
    """Manda o erro para a IA (Claude) e devolve o diagnóstico + a correção
    sugerida. Exige a permissão de diagnóstico (POST cai na regra de ver)."""
    from database import fetch_one

    from services.ia import analisar_erro
    with db_conn() as conn:
        erro = fetch_one(conn, """
            SELECT quando, origem, versao, url, mensagem
              FROM erros_cliente WHERE id = ?
        """, (erro_id,))
    if not erro:
        return jsonify({"erro": "Registro não encontrado"}), 404

    r = analisar_erro(dict(erro))
    if not r.get("ativo"):
        return jsonify({"erro": r.get("motivo") or "IA indisponível"}), 503
    return jsonify({"analise": r["analise"]})


@app.route("/api/erros-cliente/resolvidos", methods=["DELETE"])
def limpar_erros_resolvidos():
    """Limpa de uma vez tudo que já foi tratado (resolvido/ignorado)."""
    from database import execute

    with db_conn(commit=True) as conn:
        n = execute(conn, "DELETE FROM erros_cliente WHERE status IN ('resolvido', 'ignorado')")
    return jsonify({"mensagem": f"{n} registro(s) limpos", "removidos": n})


@app.route("/acompanhar/<token>")
def acompanhar(token):
    """Página pública onde o cliente vê o técnico a caminho.

    Sem login de propósito: o cliente não tem conta. O link é a credencial,
    mesmo modelo do link do técnico. Fica aqui e não no blueprint de rastreio
    porque lá tudo vive sob /api — isto é HTML.
    """
    return render_template("acompanhar.html", token=token)


@app.route("/os/<int:os_id>/imprimir")
def imprimir_os(os_id):
    """Documento da OS pronto pra impressão. Exige login (não está nos
    caminhos públicos) — é documento interno, diferente do link de
    acompanhamento do cliente."""
    with db_conn() as conn:
        ordem = fetch_one(conn, """
            SELECT os.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
                   c.email AS cliente_email, c.cpf_cnpj AS cliente_cpf_cnpj,
                   c.endereco AS cliente_endereco, c.numero AS cliente_numero,
                   c.complemento AS cliente_complemento, c.bairro AS cliente_bairro,
                   c.cidade AS cliente_cidade, c.estado AS cliente_estado,
                   c.cep AS cliente_cep
              FROM ordens_servico os
              JOIN clientes c ON c.id = os.cliente_id
             WHERE os.id = ?
        """, (os_id,))
        if not ordem:
            return "<h1>Ordem de serviço não encontrada</h1>", 404

        visita = fetch_one(conn, """
            SELECT f.dia_semana, f.data_referencia, t.nome AS tecnico_nome
              FROM servicos s
              JOIN fichas f ON f.id = s.ficha_id
              LEFT JOIN tecnicos t ON t.id = f.tecnico_id
             WHERE s.ordem_servico_id = ?
             ORDER BY s.id DESC LIMIT 1
        """, (os_id,))

    # Formatação BR feita aqui, não no template: "%.2f" de Python usa ponto
    # decimal, e um documento pra cliente assinar com "R$ 90.00" e data em
    # ISO (2026-08-22) parece rascunho de sistema, não papel de assistência
    # técnica de verdade.
    def _data_br(iso: str) -> str:
        try:
            return datetime.strptime((iso or "")[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return iso or "—"

    def _moeda_br(valor) -> str:
        return f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if visita and visita.get("data_referencia"):
        visita = dict(visita)
        visita["data_referencia_br"] = _data_br(visita["data_referencia"])

    termos = TERMOS_POR_TIPO.get(ordem.get("tipo_os"), TERMOS_PADRAO)
    tipo_os_rotulo = TIPOS_OS_ROTULO.get(ordem.get("tipo_os"), "")

    return render_template(
        "os_imprimir.html", ordem=ordem, visita=visita, termos=termos,
        tipo_os_rotulo=tipo_os_rotulo,
        data_abertura_br=_data_br(ordem.get("criado_em")),
        taxa_br=_moeda_br(ordem.get("taxa_avaliacao")),
        gerado_em_br=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


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


# Escritas que NÃO mexem no que o painel mostra.
#
# O contador de revisão existe para o painel saber que a ROTA mudou e
# rebaixar fichas e técnicos. Posição de GPS, mensagem de chat e registro de
# erro não alteram rota nenhuma — mas passavam por aqui e incrementavam o
# contador do mesmo jeito.
#
# O estrago: o OwnTracks manda posição a cada 30 segundos POR TÉCNICO. Com
# dois em campo, o painel do Kalebe recarregava a tela inteira a cada ~15
# segundos e ficava impossível de usar ("não consigo mexer no site",
# 2026-08-18). Foi a funcionalidade de rastreio que travou o painel.
_SEM_REVISAO = ("/rastreador", "/posicao", "/api/chat/", "/api/equipe/",
                "/api/erro-cliente")


@app.after_request
def _marcar_revisao(resp):
    if request.method not in _METODOS_DE_ESCRITA:
        return resp
    if not request.path.startswith("/api"):
        return resp
    if any(p in request.path for p in _SEM_REVISAO):
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
    """`revisao` = os DADOS mudaram. `app` = o CÓDIGO mudou.

    O painel fica aberto o dia inteiro e o JS só é buscado da rede quando a
    PÁGINA recarrega — que era o problema do app do técnico e voltou a morder
    aqui: o Kalebe tentou subir foto rodando a versão anterior.
    """
    from database import fetch_one
    from extensions import VERSAO_APP

    # O contador de mensagens não lidas PEGA CARONA aqui.
    #
    # Ele tinha polling próprio de 10s: com o painel aberto eram 12 pedidos por
    # minuto por aba, num servidor de UM worker. Como esta rota já é chamada no
    # mesmo ritmo, mandar o número junto custa uma consulta barata e elimina
    # metade do tráfego do painel.
    with db_conn() as conn:
        dados = {**ler_revisao(conn), "app": VERSAO_APP}
        try:
            nl = fetch_one(conn, """
                SELECT COUNT(*) AS n FROM mensagens
                 WHERE autor_tipo = 'cliente' AND lida = FALSE
            """ if IS_PG else """
                SELECT COUNT(*) AS n FROM mensagens
                 WHERE autor_tipo = 'cliente' AND lida = 0
            """)
            dados["chat_nao_lidas"] = (nl or {}).get("n", 0)
        except Exception:
            dados["chat_nao_lidas"] = 0
        return jsonify(dados)


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