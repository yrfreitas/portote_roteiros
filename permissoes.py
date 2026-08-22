"""Camada de PERMISSÕES granulares por usuário.

Antes só havia `papel` (admin vê tudo / técnico bloqueado do que é "de
desenvolvedor"). Aqui isso vira um conjunto de AÇÕES nomeadas (capacidades) que
o admin liga/desliga por pessoa. O objetivo é o Kalebe poder dizer, por
exemplo, "o JP pode ver o estoque e dar entrada, mas não excluir peça".

COMO O EFETIVO É CALCULADO (ordem importa):
  1. Admin (papel 'admin' ou o admin-mestre do login por senha) tem TUDO,
     sempre — não dá para trancar o dono do sistema para fora.
  2. Para os demais, cada ação vale o que estiver em `usuarios.permissoes`
     (JSON {acao: true/false}); o que não estiver lá cai no PADRÃO do papel.

O bloqueio de verdade é no SERVIDOR (ver `checar_acesso`, chamado no
before_request do app). O front usa a mesma lista só para esconder o que a
pessoa não pode — esconder botão sem bloquear rota seria decoração.
"""
import json

from flask import g, session

from database import db_conn, fetch_one

# Catálogo de ações. `area` só agrupa na tela. A ordem é a de exibição.
CATALOGO = [
    # Sistema
    {"chave": "diagnostico",        "area": "Sistema",     "rotulo": "Ver Diagnóstico do sistema"},
    {"chave": "diagnostico_editar", "area": "Sistema",     "rotulo": "Editar diagnóstico (status/observação dos erros)"},
    {"chave": "gerenciar_usuarios", "area": "Sistema",     "rotulo": "Gerenciar acessos e permissões"},
    {"chave": "gerenciar_tecnicos", "area": "Sistema",     "rotulo": "Criar / editar / remover técnicos"},
    {"chave": "gerenciar_setores",  "area": "Sistema",     "rotulo": "Criar / editar / remover setores"},
    # Roteiros e atendimentos
    {"chave": "roteiros",           "area": "Roteiros",    "rotulo": "Mexer nos roteiros (criar dia, otimizar, adicionar atendimento)"},
    {"chave": "atendimentos",       "area": "Roteiros",    "rotulo": "Editar / mover / excluir atendimentos"},
    # Peças e estoque
    {"chave": "pecas",              "area": "Peças",       "rotulo": "Ver a aba Peças (compras / nota fiscal)"},
    {"chave": "cotacao",            "area": "Peças",       "rotulo": "Ver e usar a aba Cotação (peças aguardando preço)"},
    {"chave": "ordens_servico",     "area": "OS",          "rotulo": "Ver e abrir Ordens de Serviço"},
    {"chave": "estoque_ver",        "area": "Estoque",     "rotulo": "Ver o Estoque"},
    {"chave": "estoque_editar",     "area": "Estoque",     "rotulo": "Mexer no Estoque (entrada, saída, ajuste, criar)"},
    {"chave": "estoque_excluir",    "area": "Estoque",     "rotulo": "Excluir peças e estoques"},
    # Comunicação e relatórios
    {"chave": "chat_equipe",        "area": "Comunicação", "rotulo": "Usar o chat da equipe"},
    {"chave": "relatorios",         "area": "Relatórios",  "rotulo": "Ver relatórios e exportações"},
]

TODAS = [c["chave"] for c in CATALOGO]

# O que um TÉCNICO recebe por padrão (sem nenhum ajuste). Vazio: por padrão o
# técnico continua só com o trabalho de campo (rotas via token, fora daqui).
PADRAO_TECNICO = set()

# Portão central: (prefixo_da_rota, métodos ou None p/ todos, ação exigida).
# É avaliado em ordem; a PRIMEIRA regra cujo prefixo casa decide. Por isso as
# regras mais específicas de estoque (por método) vêm antes da genérica.
REGRAS = [
    # Diagnóstico: ver vs. mexer. A regra de editar vem ANTES da de ver, senão
    # a de ver (prefixo igual, sem método) casaria primeiro e o editar nunca
    # seria exigido. PUT/DELETE nos erros = editar; o resto (GET) = ver.
    ("/api/erros-cliente",         ("PUT", "DELETE"),        "diagnostico_editar"),
    ("/api/erros-cliente",         None,                     "diagnostico"),
    ("/api/diagnostico",           None,                     "diagnostico"),
    ("/api/rastreios/diagnostico", None,                     "diagnostico"),
    ("/api/pedidos/diagnostico",   None,                     "diagnostico"),
    # Cadastros de sistema (GET fica livre — os selects do painel precisam dele).
    ("/api/tecnicos",              ("POST", "PUT", "DELETE"), "gerenciar_tecnicos"),
    ("/api/setores",               ("POST", "PUT", "DELETE"), "gerenciar_setores"),
    # Roteiros: escrita em fichas (inclui adicionar atendimento, otimizar...).
    ("/api/fichas",                ("POST", "PUT", "DELETE"), "roteiros"),
    # Atendimentos existentes: editar, mover, transferir, excluir.
    ("/api/servicos",              ("POST", "PUT", "DELETE"), "atendimentos"),
    # Peças, usuários, relatórios, chat da equipe.
    ("/api/pedidos",               None,                     "pecas"),
    ("/api/cotacoes",              None,                     "cotacao"),
    ("/api/clientes",              None,                     "ordens_servico"),
    ("/api/ordens-servico",        None,                     "ordens_servico"),
    ("/api/usuarios",              None,                     "gerenciar_usuarios"),
    ("/api/permissoes",            None,                     "gerenciar_usuarios"),
    ("/api/equipe",                None,                     "chat_equipe"),
    ("/api/relatorios",            None,                     "relatorios"),
    ("/api/historico",             None,                     "relatorios"),
    ("/api/metricas",              None,                     "relatorios"),
    ("/api/desfechos",             None,                     "relatorios"),
    # Estoque: ver / editar / excluir.
    ("/api/estoque",               ("GET",),                 "estoque_ver"),
    ("/api/estoque",               ("POST", "PUT", "PATCH"), "estoque_editar"),
    ("/api/estoque",               ("DELETE",),              "estoque_excluir"),
]


def _overrides(bruto) -> dict:
    """Lê o JSON de permissoes com tolerância — texto zoado não derruba nada."""
    if isinstance(bruto, dict):
        return bruto
    if not bruto:
        return {}
    try:
        d = json.loads(bruto)
        return d if isinstance(d, dict) else {}
    except (ValueError, TypeError):
        return {}


def efetivas(papel: str, permissoes_bruto=None) -> dict:
    """Dicionário {acao: bool} já resolvido para um usuário."""
    if (papel or "").strip() == "admin":
        return {a: True for a in TODAS}
    ov = _overrides(permissoes_bruto)
    return {a: bool(ov[a]) if a in ov else (a in PADRAO_TECNICO) for a in TODAS}


def _caps_do_request() -> dict:
    """Permissões efetivas de quem está fazendo a requisição AGORA.

    Admin-mestre (login só por senha, sem usuario_id) e papel admin -> tudo.
    Senão, lê `permissoes` do banco na hora — assim uma mudança feita pelo
    admin vale já na próxima ação da pessoa, sem precisar deslogar. Cacheia no
    `g` para não repetir a leitura dentro da mesma requisição.
    """
    if "caps" in g:
        return g.caps

    papel = session.get("papel") or ("admin" if session.get("admin") else None)
    if papel == "admin":
        g.caps = {a: True for a in TODAS}
        return g.caps

    uid = session.get("usuario_id")
    bruto = None
    if uid:
        try:
            with db_conn() as conn:
                row = fetch_one(conn, "SELECT permissoes FROM usuarios WHERE id = ?", (uid,))
            bruto = row["permissoes"] if row else None
        except Exception:
            bruto = None
    g.caps = efetivas(papel, bruto)
    return g.caps


def pode(acao: str) -> bool:
    return bool(_caps_do_request().get(acao, False))


def checar_acesso(path: str, metodo: str):
    """Devolve a ação exigida se o path/método for barrado para quem chama, ou
    None se pode passar. Usado no before_request para bloquear no servidor."""
    for prefixo, metodos, acao in REGRAS:
        if not path.startswith(prefixo):
            continue
        if metodos is not None and metodo.upper() not in metodos:
            continue
        return None if pode(acao) else acao

    # Nenhuma regra bateu. GET continua livre de propósito — é o que os
    # selects do painel dependem (ver comentário acima, em REGRAS). Mas
    # ESCRITA sem regra nenhuma cobrindo é a rota que ALGUÉM ESQUECEU de
    # mapear, não uma liberada de propósito — foi assim que
    # DELETE /api/rastreios/<id>/posicao ficou acessível pra qualquer
    # usuário logado, contrariando o próprio docstring da rota ("fica atrás
    # da sessão de admin"). Fechar por padrão aqui não tira nada de quem já
    # tinha acesso: toda ação que algum papel realmente precisa já está
    # nomeada em REGRAS; o que sobra fora daqui nunca foi pensado pra ser
    # usado por não-admin.
    if metodo.upper() == "GET":
        return None
    papel = session.get("papel") or ("admin" if session.get("admin") else None)
    if papel == "admin":
        return None
    return "sem_regra_definida"
