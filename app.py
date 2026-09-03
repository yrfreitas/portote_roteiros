from dotenv import load_dotenv

load_dotenv()

import calendar
import json
import logging
import os
import secrets
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from database import (IS_PG, bump_revisao, db_conn, fetch_all, fetch_one,
                      init_db, ler_revisao)
from extensions import VERSAO_APP, limiter
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.clientes import clientes_bp
from routes.cotacoes import cotacoes_bp
from routes.estoque import estoque_bp
from routes.ordens_servico import (MODELOS_OS_ROTULO, TERMOS_PADRAO,
                                   TERMOS_POR_TIPO, TIPOS_OS_ROTULO,
                                   ordens_servico_bp)
from routes.fichas import fichas_bp
from routes.pedidos import pedidos_bp
from routes.rastreio import rastreio_bp
from routes.relatorios import relatorios_bp
from routes.servicos import servicos_bp
from routes.setores import setores_bp
from routes.tecnico_api import tecnico_api_bp
from routes.tecnico_view import tecnico_view_bp
from routes.substituicoes import substituicoes_bp
from routes.tecnicos import tecnicos_bp
from routes.vendas import vendas_bp

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
app.register_blueprint(vendas_bp, url_prefix="/api")
app.register_blueprint(substituicoes_bp, url_prefix="/api")


def _e_api() -> bool:
    return request.path.startswith("/api")


_CAMINHOS_PUBLICOS = {"/login", "/api/health", "/api/erro-cliente"}
# /acompanhar/ e /api/rastreio/ são públicos porque quem abre é o CLIENTE, que
# não tem conta no sistema. O link de 16 bytes é a credencial — mesmo modelo do
# link do técnico. Só expõem posição e destino daquele atendimento.
_PREFIXOS_PUBLICOS = ("/static/", "/tecnico/", "/api/t/",
                      "/acompanhar/", "/api/rastreio/", "/api/chat/", "/os/cliente/",
                      "/api/precos-panasonic")
# /api/precos-panasonic* é público na camada de sessão porque quem chama é o
# robô local (Portotec/Softwear para Pedidos), sem cookie de usuário — a
# proteção real é o token compartilhado (_token_valido em substituicoes.py),
# checado dentro da própria rota.


# Controle de acesso por AÇÃO (ver permissoes.py), no lugar do antigo "só
# admin". Cada área sensível exige uma capacidade que o admin liga/desliga por
# pessoa. Bloqueio no SERVIDOR — esconder o botão sem barrar a rota é decoração.
@app.before_request
def _exigir_permissao():
    if not request.path.startswith("/api"):
        return
    # /api/t/<token>/... é a API do técnico em campo: a autorização ali é o
    # TOKEN em si (quem tem o link é aquele técnico), não papel/permissões de
    # sessão — existe até pra quem não está logado em lugar nenhum. Achado em
    # 2026-08-31 ao reaproveitar essas rotas no botão de almoço do PAINEL: com
    # uma sessão de papel "tecnico" ativa (session["admin"]=True vale pra
    # qualquer login), este gate barrava a chamada com "sem_regra_definida"
    # porque /api/t nunca teve (nem precisa ter) regra em permissoes.py.
    if request.path.startswith("/api/t/"):
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

    def _operacional():
        # Pedido de 2026-08-29: "coisas reais" no Diagnóstico — números do
        # dia a dia, não só saúde de integração. LIKE em vez de função de
        # data porque criado_em é texto 'AAAA-MM-DD HH:MM:SS' nos dois
        # bancos (SQLite/Postgres); comparar por prefixo funciona igual nos
        # dois sem precisar de SQL específico de cada um.
        hoje = datetime.now().strftime("%Y-%m-%d")
        with db_conn() as conn:
            os_status = fetch_all(conn, "SELECT status, COUNT(*) AS n FROM ordens_servico GROUP BY status")
            precisa_peca = fetch_one(conn, """
                SELECT COUNT(*) AS n FROM servico_desfecho
                 WHERE desfecho = 'precisa_peca' AND pedido_em IS NULL
            """)["n"]
            eventos_almoco = fetch_all(conn, "SELECT tecnico_id, tipo FROM almoco_eventos ORDER BY tecnico_id, id")
            vendas_hoje = fetch_one(conn, """
                SELECT COUNT(*) AS n, COALESCE(SUM(valor_total), 0) AS total
                  FROM vendas WHERE criado_em LIKE ?
            """, (hoje + '%',))

        ultimo_por_tecnico = {}
        for l in eventos_almoco:
            ultimo_por_tecnico[l["tecnico_id"]] = l["tipo"]
        tecnicos_em_almoco = sum(1 for t in ultimo_por_tecnico.values() if t == "inicio")

        return {
            "os_por_status": {l["status"]: l["n"] for l in os_status},
            "precisa_peca": precisa_peca,
            "tecnicos_em_almoco": tecnicos_em_almoco,
            "vendas_hoje": {"quantidade": vendas_hoje["n"], "total": float(vendas_hoje["total"] or 0)},
        }

    bloco("rastreio", _rastreio)
    bloco("agoraos", _agoraos)
    bloco("planilha", _planilha)
    bloco("setores", _setores)
    bloco("ia", _ia)
    bloco("erros", _erros)
    bloco("operacional", _operacional)

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


# ─── Changelog — "o que já foi pedido e entregue" (2026-08-29) ───────────
#
# Alimentado a cada deploy (junto com o versionamento) pra não depender de
# rolar a conversa com a IA pra lembrar o que já mudou. Kalebe também pode
# escrever uma linha aqui na mão, se quiser anotar algo.
@app.route("/api/changelog", methods=["GET"])
def listar_changelog():
    from database import fetch_all

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT id, versao, resumo, criado_em FROM changelog_entradas
             ORDER BY id DESC LIMIT 60
        """)
    return jsonify({"entradas": linhas})


@app.route("/api/log-exportacoes", methods=["GET"])
def listar_log_exportacoes():
    """Rastreabilidade de exportação de dados (pedido de 2026-09-02, LGPD)
    — quem baixou o quê e quando. Atrás da mesma permissão de diagnóstico:
    é informação sobre o USO do sistema, não do dia a dia do atendimento."""
    from database import fetch_all

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT id, usuario, rota, detalhe, criado_em FROM log_exportacoes
             ORDER BY id DESC LIMIT 100
        """)
    return jsonify({"registros": linhas})


@app.route("/api/changelog", methods=["POST"])
def criar_changelog():
    from database import execute

    d = request.get_json(silent=True) or {}
    resumo = (d.get("resumo") or "").strip()
    if not resumo:
        return jsonify({"erro": "Escreva o que mudou"}), 400
    versao = (d.get("versao") or "").strip()[:20] or None
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_conn(commit=True) as conn:
        execute(conn, """
            INSERT INTO changelog_entradas (versao, resumo, criado_em) VALUES (?, ?, ?)
        """, (versao, resumo[:2000], agora))
    return jsonify({"mensagem": "Registrado"}), 201


# ─── Chat de diagnóstico com IA (2026-08-29) ─────────────────────────────
#
# Diferente do "Analisar com IA" acima (um erro, uma resposta): aqui é
# conversa mesmo, com histórico. Ver o aviso embutido no próprio prompt em
# services/ia.py — essa IA só analisa/sugere, não edita nada do sistema.
@app.route("/api/diagnostico/chat", methods=["GET"])
def listar_chat_diagnostico():
    from database import fetch_all

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT id, autor, texto, criado_em FROM diagnostico_chat
             ORDER BY id ASC LIMIT 200
        """)
    return jsonify({"mensagens": linhas})


@app.route("/api/diagnostico/chat", methods=["POST"])
def enviar_chat_diagnostico():
    from database import execute, fetch_all, insert_returning_id

    from services.ia import conversar

    d = request.get_json(silent=True) or {}
    texto = (d.get("texto") or "").strip()
    if not texto:
        return jsonify({"erro": "Escreva uma mensagem"}), 400

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_conn(commit=True) as conn:
        insert_returning_id(conn, """
            INSERT INTO diagnostico_chat (autor, texto, criado_em) VALUES ('kalebe', ?, ?)
        """, (texto[:4000], agora))
        # Só as últimas 20 pra não estourar contexto/custo — uma conversa de
        # diagnóstico não precisa lembrar de meses atrás pra continuar coerente.
        recentes = fetch_all(conn, """
            SELECT autor, texto FROM diagnostico_chat ORDER BY id DESC LIMIT 20
        """)
        historico = [{"autor": r["autor"], "texto": r["texto"]} for r in reversed(recentes)]

    r = conversar(historico)
    if not r.get("ativo"):
        return jsonify({"erro": r.get("motivo") or "IA indisponível"}), 503

    agora2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_conn(commit=True) as conn:
        execute(conn, """
            INSERT INTO diagnostico_chat (autor, texto, criado_em) VALUES ('ia', ?, ?)
        """, (r["resposta"][:8000], agora2))

    return jsonify({"resposta": r["resposta"]}), 201


@app.route("/api/diagnostico/chat", methods=["DELETE"])
def limpar_chat_diagnostico():
    from database import execute

    with db_conn(commit=True) as conn:
        execute(conn, "DELETE FROM diagnostico_chat")
    return jsonify({"mensagem": "Conversa limpa"})


@app.route("/tv")
def tv_painel_pagina():
    """Painel em tela cheia pra rodar numa TV do escritório — pedido de
    2026-09-03 ("modo TV da parede"). Reaproveita as MESMAS rotas que o
    painel principal já usa (/api/fichas, /api/tecnicos,
    /api/relatorios/resumo-dia); atrás do login normal como qualquer outra
    página do site."""
    return render_template("tv_painel.html")


@app.route("/torre-controle")
def torre_controle_pagina():
    """Mapa ao vivo com todos os técnicos — pedido de 2026-09-03. Fica atrás
    do login normal (não está em _CAMINHOS_PUBLICOS); quem não tem a
    permissão `torre_controle` chega até a página, mas a chamada à API
    embaixo devolve 403 e a tela mostra a mensagem, mesmo padrão do resto do
    painel (o servidor barra, a tela só explica)."""
    return render_template("torre_controle.html")


@app.route("/acompanhar/<token>")
def acompanhar(token):
    """Página pública onde o cliente vê o técnico a caminho.

    Sem login de propósito: o cliente não tem conta. O link é a credencial,
    mesmo modelo do link do técnico. Fica aqui e não no blueprint de rastreio
    porque lá tudo vive sob /api — isto é HTML.
    """
    return render_template("acompanhar.html", token=token)


def _montar_documento_os(os_id):
    """Monta o contexto de impressão de uma OS — reaproveitado pela rota
    interna (login) e pela pública por token (ver /os/cliente/<token>),
    que existe pra o técnico poder mandar o documento pro cliente na hora,
    do próprio atendimento em campo (pedido de 2026-08-28)."""
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
            return None

        visita = fetch_one(conn, """
            SELECT f.dia_semana, f.data_referencia, t.nome AS tecnico_nome
              FROM servicos s
              JOIN fichas f ON f.id = s.ficha_id
              LEFT JOIN tecnicos t ON t.id = f.tecnico_id
             WHERE s.ordem_servico_id = ?
             ORDER BY s.id DESC LIMIT 1
        """, (os_id,))

        # Itens (Serviço/Peças/Mão de obra) valem pra qualquer modelo agora —
        # baseado no modelo de impressão do Kalebe, que traz essa seção na
        # OS padrão também, não só no Orçamento.
        itens = fetch_all(conn, """
            SELECT nome, valor FROM ordem_servico_itens
             WHERE ordem_servico_id = ? ORDER BY id
        """, (os_id,))
        tecnico_atendeu_nome = None
        if ordem.get("tecnico_atendeu_id"):
            tecnico_row = fetch_one(conn, "SELECT nome FROM tecnicos WHERE id = ?",
                                    (ordem["tecnico_atendeu_id"],))
            tecnico_atendeu_nome = tecnico_row["nome"] if tecnico_row else None

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

    # "R$ 0,00" impresso lê como "não custou nada" pro cliente, quando na
    # real é só um campo que ninguém preencheu ainda — pedido de 2026-08-28
    # pra sumir com o "R$ 0,00" e deixar o espaço em branco mesmo.
    def _moeda_fmt(valor) -> str:
        try:
            numero = float(valor or 0)
        except (TypeError, ValueError):
            numero = 0
        return f"R$ {_moeda_br(numero)}" if numero else ""

    if visita and visita.get("data_referencia"):
        visita = dict(visita)
        visita["data_referencia_br"] = _data_br(visita["data_referencia"])

    # Garantia calculada, não preenchida à mão — pedido de 2026-08-28 pra
    # não admitir erro de conta: começa NO DIA EM QUE A FOLHA É IMPRESSA
    # (não na data de abertura da OS, que pode ser bem anterior a quando o
    # documento realmente sai impresso pro cliente assinar).
    # "saida_oficina" soma aos outros três em 2026-08-29: o termo dela promete
    # 3 meses "a partir da data da conclusão do reparo" (ver TERMOS_POR_TIPO),
    # só que essa data é escolhida à mão no painel (ordem.garantia_inicio) —
    # o dia em que o aparelho de fato saiu, não necessariamente hoje. Os
    # outros três tipos não têm esse campo preenchido, então continuam
    # caindo no "hoje" de sempre.
    _GARANTIA_MESES = {"garantia_3_meses": 3, "garantia_6_meses": 6, "garantia_1_ano": 12,
                       "saida_oficina": 3}

    def _somar_meses(data, meses):
        mes_total = data.month - 1 + meses
        ano = data.year + mes_total // 12
        mes = mes_total % 12 + 1
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        return data.replace(year=ano, month=mes, day=min(data.day, ultimo_dia))

    # "saida_oficina" pode escolher 3/6/12 meses (pedido de 2026-08-29) em vez
    # do padrão fixo — os outros três tipos já SÃO um prazo fixo cada um (é a
    # própria escolha do tipo que decide), então ordem.garantia_meses não se
    # aplica a eles. O modelo Orçamento entra na mesma regra (2026-08-29):
    # não tem tipo_os fixo, mas aceita o mesmo campo de prazo escolhido à mão.
    garantia_meses = (
        ordem.get("garantia_meses")
        if (ordem.get("tipo_os") == "saida_oficina" or ordem.get("modelo_os") == "orcamento")
           and ordem.get("garantia_meses")
        else _GARANTIA_MESES.get(ordem.get("tipo_os"))
    )
    # Pedido de 2026-09-02: "não ir do dia que colocamos pra imprimir" — sem
    # garantia_inicio preenchida, isto aqui caía pra datetime.now() e
    # imprimia a garantia começando no dia em que ALGUÉM CLICOU IMPRIMIR
    # (podia ser semanas depois do atendimento de verdade). O template já
    # tinha um "else" pronto pra esse caso (linhas em branco pra preencher
    # à mão, ver os_imprimir.html) — só nunca era usado porque o fallback
    # aqui embaixo sempre entregava uma data "válida" antes de chegar lá.
    garantia_inicio_br = garantia_fim_br = garantia_prazo_rotulo = None
    if garantia_meses:
        garantia_prazo_rotulo = "1 ano" if garantia_meses == 12 else f"{garantia_meses} meses"
        if ordem.get("garantia_inicio"):
            try:
                base = datetime.strptime(ordem["garantia_inicio"], "%Y-%m-%d")
                garantia_inicio_br = base.strftime("%d/%m/%Y")
                garantia_fim_br = _somar_meses(base, garantia_meses).strftime("%d/%m/%Y")
            except ValueError:
                pass   # data inválida no banco — imprime em branco, não inventa uma

    termos = TERMOS_POR_TIPO.get(ordem.get("tipo_os"), TERMOS_PADRAO)
    # O termo padrão de "saida_oficina" tem "03 (três) meses" escrito por
    # extenso no texto jurídico — pedido de 2026-08-29 pra poder escolher
    # 6 ou 12 meses deixaria a cláusula MENTINDO se só a data fosse trocada
    # sem tocar no texto. Troca só essa frase, no documento, sem mexer no
    # termo-fonte (TERMOS_POR_TIPO segue sendo o padrão de 3 meses).
    if ordem.get("tipo_os") == "saida_oficina" and garantia_meses and garantia_meses != 3:
        _REDACAO_MESES = {6: "06 (seis)", 12: "12 (doze)"}
        termos = termos.replace("garantia de 03 (três) meses",
                                f"garantia de {_REDACAO_MESES[garantia_meses]} meses")
    tipo_os_rotulo = TIPOS_OS_ROTULO.get(ordem.get("tipo_os"), "")
    modelo_os_rotulo = MODELOS_OS_ROTULO.get(ordem.get("modelo_os"), MODELOS_OS_ROTULO["os"])

    itens_com_valor_fmt = [{"nome": i["nome"], "valor_fmt": _moeda_fmt(i["valor"])} for i in itens]
    total_orcamento_fmt = _moeda_fmt(sum(float(i["valor"] or 0) for i in itens))

    try:
        ocultar_impressao = set(json.loads(ordem.get("imprimir_ocultar") or "[]"))
    except (TypeError, ValueError):
        ocultar_impressao = set()

    return dict(
        ordem=ordem, visita=visita, termos=termos,
        tipo_os_rotulo=tipo_os_rotulo, modelo_os_rotulo=modelo_os_rotulo,
        itens=itens_com_valor_fmt, total_orcamento_fmt=total_orcamento_fmt,
        tecnico_atendeu_nome=tecnico_atendeu_nome,
        data_abertura_br=_data_br(ordem.get("criado_em")),
        taxa_fmt=_moeda_fmt(ordem.get("taxa_avaliacao")),
        taxa_vistoria_fmt=_moeda_fmt(ordem.get("taxa_vistoria")),
        ocultar_impressao=ocultar_impressao,
        garantia_inicio_br=garantia_inicio_br,
        garantia_fim_br=garantia_fim_br,
        garantia_prazo_rotulo=garantia_prazo_rotulo,
        gerado_em_br=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


@app.route("/os/<int:os_id>/imprimir")
def imprimir_os(os_id):
    """Documento da OS pronto pra impressão. Exige login (não está nos
    caminhos públicos) — é documento interno, diferente do link de
    acompanhamento do cliente."""
    contexto = _montar_documento_os(os_id)
    if not contexto:
        return "<h1>Ordem de serviço não encontrada</h1>", 404
    return render_template("os_imprimir.html", **contexto)


@app.route("/os/<int:os_id>/abrir")
def abrir_os_por_qr(os_id):
    """Pra onde o QR Code da etiqueta aponta (ver /os/<id>/etiqueta).

    Não é um link público: cai no mesmo _exigir_autenticacao de sempre —
    sem sessão, o próprio before_request redireciona pro login com
    ?next=/os/<id>/abrir, e depois de entrar volta exatamente pra cá. Exige
    login de propósito: quem escaneia a etiqueta física já está na oficina
    trabalhando, não é o cliente.
    """
    return render_template("index.html", versao=VERSAO_APP, abrir_os=os_id)


@app.route("/os/<int:os_id>/etiqueta")
def etiqueta_os(os_id):
    """Etiqueta pra colar no aparelho na entrada — pedido de 2026-08-31:
    achar/trocar aparelho na bancada dependia de decorar ou escrever o
    número da OS à mão. O QR aponta pra /os/<id>/abrir: escaneia com o
    celular (já logado) e abre a OS direto, sem digitar nada.
    """
    import base64
    import io as _io

    import qrcode

    with db_conn() as conn:
        ordem = fetch_one(conn, """
            SELECT os.id, os.tipo_aparelho, os.marca, os.modelo, os.defeito_declarado,
                   c.nome AS cliente_nome
              FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
             WHERE os.id = ?
        """, (os_id,))
    if not ordem:
        return "<h1>Ordem de serviço não encontrada</h1>", 404

    url_abrir = url_for("abrir_os_por_qr", os_id=os_id, _external=True)
    img = qrcode.make(url_abrir, box_size=8, border=2)
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    qr_data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    return render_template("os_etiqueta.html", ordem=ordem, qr_data_uri=qr_data_uri)


@app.route("/os/cliente/<token>")
def imprimir_os_cliente(token):
    """Mesmo documento, sem login — o token de 32 bytes é a credencial
    (mesmo modelo do link de acompanhamento). Existe pra o técnico poder
    mandar a OS pro cliente pelo WhatsApp assim que colhe a assinatura em
    campo, sem precisar que o escritório mande depois."""
    with db_conn() as conn:
        os_row = fetch_one(conn, "SELECT id FROM ordens_servico WHERE token_cliente = ?", (token,))
    if not os_row:
        return "<h1>Link inválido</h1>", 404
    contexto = _montar_documento_os(os_row["id"])
    if not contexto:
        return "<h1>Ordem de serviço não encontrada</h1>", 404
    return render_template("os_imprimir.html", **contexto)


def _montar_documento_venda(venda_id):
    """Contexto pra nota de venda — bem mais simples que _montar_documento_os
    porque uma venda de balcão não tem endereço de visita, garantia calculada
    por data nem termo jurídico: é nome, produto, valor e a garantia que foi
    combinada na hora (texto livre, não uma cláusula inteira)."""
    with db_conn() as conn:
        venda = fetch_one(conn, "SELECT * FROM vendas WHERE id = ?", (venda_id,))
        if not venda:
            return None
        itens = fetch_all(conn, "SELECT * FROM venda_itens WHERE venda_id = ? ORDER BY id", (venda_id,))

    def _moeda_br(valor) -> str:
        return f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    for item in itens:
        item["quantidade_fmt"] = f"{float(item['quantidade'] or 0):g}"
        item["valor_unit_fmt"] = _moeda_br(item["valor_unit"])
        item["valor_total_fmt"] = _moeda_br(item["valor_total"])

    criado_em = (venda.get("criado_em") or "")[:16].replace("T", " ")
    if criado_em and len(criado_em) >= 10:
        criado_em_br = criado_em[8:10] + "/" + criado_em[5:7] + "/" + criado_em[0:4] + criado_em[10:]
    else:
        criado_em_br = criado_em

    return dict(
        venda=venda,
        itens=itens,
        valor_total_fmt=_moeda_br(venda.get("valor_total")),
        criado_em_br=criado_em_br,
        gerado_em_br=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


@app.route("/vendas/<int:venda_id>/imprimir")
def imprimir_venda(venda_id):
    """Nota de venda pronta pra impressão — pequena de propósito, não é o
    modelo de OS (pedido explícito de 2026-08-29: "não precisa ser igual
    quando imprimimos a os, fica muito grande, tem que ser pequeno")."""
    contexto = _montar_documento_venda(venda_id)
    if not contexto:
        return "<h1>Venda não encontrada</h1>", 404
    return render_template("venda_imprimir.html", **contexto)


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

        # Mesma lógica da badge de chat: números da central de notificações
        # (pedido de 2026-09-02) pegam carona aqui em vez de abrir polling
        # próprio — são só COUNT() simples, custo desprezível a cada 10s.
        try:
            erros = fetch_one(conn, """
                SELECT COUNT(*) AS n FROM erros_cliente
                 WHERE status IS NULL OR status != 'resolvido'
            """)
            dados["erros_abertos"] = (erros or {}).get("n", 0)
        except Exception:
            dados["erros_abertos"] = 0

        try:
            pecas = fetch_one(conn, """
                SELECT
                    (SELECT COUNT(*) FROM servico_desfecho
                      WHERE desfecho = 'precisa_peca' AND pedido_em IS NULL) +
                    (SELECT COUNT(*) FROM pedido_peca_os WHERE pedido_em IS NULL) AS n
            """)
            dados["pecas_pendentes"] = (pecas or {}).get("n", 0)
        except Exception:
            dados["pecas_pendentes"] = 0

        try:
            agendar = fetch_one(conn, """
                SELECT COUNT(*) AS n FROM ordens_servico
                 WHERE status = 'aguardando_agendamento'
            """)
            dados["agendar_pendentes"] = (agendar or {}).get("n", 0)
        except Exception:
            dados["agendar_pendentes"] = 0

        # SOS de técnico em campo (pedido de 2026-09-02) — prioridade máxima,
        # por isso lista NOME, não só contagem (o sino já mostra número pros
        # outros itens, mas "alguém precisa de ajuda" merece dizer quem).
        try:
            sos = fetch_all(conn, """
                SELECT t.id, t.nome, ts.sos_em FROM tecnico_status ts
                  JOIN tecnicos t ON t.id = ts.tecnico_id
                 WHERE ts.sos_ativo = TRUE
            """ if IS_PG else """
                SELECT t.id, t.nome, ts.sos_em FROM tecnico_status ts
                  JOIN tecnicos t ON t.id = ts.tecnico_id
                 WHERE ts.sos_ativo = 1
            """)
            dados["sos_tecnicos"] = sos
        except Exception:
            dados["sos_tecnicos"] = []

        # Estoque abaixo do mínimo (pedido de 2026-09-02) — a aba Estoque já
        # calculava isso por item; só faltava alguém fora dela saber que
        # existe sem precisar abrir a aba pra descobrir.
        try:
            estoque = fetch_one(conn, """
                SELECT COUNT(*) AS n FROM estoque_itens
                 WHERE minimo > 0 AND saldo <= minimo
            """)
            dados["estoque_abaixo_minimo"] = (estoque or {}).get("n", 0)
        except Exception:
            dados["estoque_abaixo_minimo"] = 0

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