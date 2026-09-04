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
    {"chave": "roteiros_ver",       "area": "Roteiros",    "rotulo": "Ver a aba Roteiros"},
    {"chave": "roteiros",           "area": "Roteiros",    "rotulo": "Mexer nos roteiros (criar dia, otimizar, adicionar atendimento)"},
    {"chave": "atendimentos",       "area": "Roteiros",    "rotulo": "Editar / mover / excluir atendimentos"},
    {"chave": "cep_ver",            "area": "Roteiros",    "rotulo": "Ver e usar o Verificador de CEP"},
    {"chave": "desfechos_ver",      "area": "Roteiros",    "rotulo": "Ver a aba Atendimentos (o que o técnico registrou em campo)"},
    {"chave": "almoco_ver",         "area": "Roteiros",    "rotulo": "Ver o horário de almoço dos técnicos (aviso e selo no painel)"},
    {"chave": "torre_controle",     "area": "Roteiros",    "rotulo": "Ver a Torre de Controle (mapa ao vivo com a posição de todos os técnicos)"},
    # Peças e estoque
    {"chave": "pecas",              "area": "Peças",       "rotulo": "Ver a aba Peças (compras / nota fiscal)"},
    {"chave": "cotacao",            "area": "Peças",       "rotulo": "Ver e usar a aba Cotação (peças aguardando preço / substituição)"},
    {"chave": "ordens_servico",     "area": "OS",          "rotulo": "Ver e abrir Ordens de Serviço (inclui Agendar Clientes)"},
    {"chave": "ver_cpf_completo",   "area": "OS",          "rotulo": "Ver CPF/CNPJ do cliente por completo (sem quem não tem, vem mascarado)"},
    {"chave": "estoque_ver",        "area": "Estoque",     "rotulo": "Ver o Estoque"},
    {"chave": "estoque_editar",     "area": "Estoque",     "rotulo": "Mexer no Estoque (entrada, saída, ajuste, criar)"},
    {"chave": "estoque_excluir",    "area": "Estoque",     "rotulo": "Excluir peças e estoques"},
    {"chave": "vendas",             "area": "Vendas",      "rotulo": "Vender peças no balcão e imprimir a nota"},
    # Comunicação e relatórios
    {"chave": "chat_equipe",        "area": "Comunicação", "rotulo": "Usar o chat da equipe"},
    {"chave": "relatorios",         "area": "Relatórios",  "rotulo": "Ver a aba Histórico, relatórios e exportações"},
]

TODAS = [c["chave"] for c in CATALOGO]

# O que um TÉCNICO recebe por padrão (sem nenhum ajuste explícito na pessoa).
#
# Era vazio de propósito (nasce sem nada, alguém libera cada área na mão) —
# só que login novo nasce sem NENHUMA permissão, e enquanto ninguém entra em
# Acessos e configura, a pessoa não consegue fazer nada no site. Isso é
# exatamente o "site travado/piscando pros outros logins" que o Kalebe
# reportou repetidas vezes em 2026-08-25/26: não era bug, era permissão nunca
# dada. Pedido explícito dele em 2026-08-26: todo mundo com o mesmo acesso
# que ele. Agora o padrão é TUDO liberado, e restringir alguém específico
# continua possível — quem editar as permissões dessa pessoa no painel grava
# um "false" explícito, que sempre vence sobre este padrão (ver `efetivas`).
PADRAO_TECNICO = set(TODAS)

# Papel "tecnico" é diferente: pedido explícito de 2026-09-02, ao contrário
# da decisão de 2026-08-26 acima (que continua valendo pra recepcionista). O
# técnico já tem uma tela própria pra tudo que precisa (o link pessoal em
# /t/<token>: própria rota, reordenar parada, dar baixa, bater o almoço) —
# aqui no painel principal ele só deve ENXERGAR a própria rota (ver_rota),
# sem editar ficha/cliente nem se meter em Estoque, OS, Peças etc. Chat de
# cliente e chat de equipe não são catálogo (são recorte por papel direto em
# routes/chat.py), por isso não aparecem aqui.
PADRAO_PAPEL_TECNICO = {"roteiros_ver", "atendimentos"}

# Portão central: (prefixo_da_rota, métodos ou None p/ todos, ação exigida).
# É avaliado em ordem; a PRIMEIRA regra cujo prefixo casa decide. Por isso as
# regras mais específicas de estoque (por método) vêm antes da genérica.
REGRAS = [
    # Diagnóstico: ver vs. mexer. A regra de editar vem ANTES da de ver, senão
    # a de ver (prefixo igual, sem método) casaria primeiro e o editar nunca
    # seria exigido. PUT/DELETE nos erros = editar; o resto (GET) = ver.
    ("/api/erros-cliente",         ("PUT", "DELETE"),        "diagnostico_editar"),
    ("/api/erros-cliente",         None,                     "diagnostico"),
    # Chat/changelog do Diagnóstico: mais específico que a regra genérica
    # de /api/diagnostico logo abaixo, por isso vem antes.
    ("/api/diagnostico/chat",      ("DELETE",),              "diagnostico_editar"),
    ("/api/diagnostico/chat",      None,                     "diagnostico"),
    ("/api/changelog",             ("POST",),                "diagnostico_editar"),
    ("/api/changelog",             None,                     "diagnostico"),
    # Log de exportação (LGPD, 2026-09-02): informação sobre uso do sistema,
    # mesma sensibilidade do resto do Diagnóstico.
    ("/api/log-exportacoes",       None,                     "diagnostico"),
    ("/api/diagnostico",           None,                     "diagnostico"),
    ("/api/rastreios/diagnostico", None,                     "diagnostico"),
    ("/api/pedidos/diagnostico",   None,                     "diagnostico"),
    # Ponto de almoço: mais específico que a regra genérica de /api/tecnicos
    # logo abaixo, por isso vem antes — senão nunca seria alcançada.
    ("/api/tecnicos/almoco",       None,                     "almoco_ver"),
    # Torre de Controle: mais específica que a regra genérica de /api/tecnicos
    # logo abaixo, por isso vem antes — senão nunca seria alcançada.
    ("/api/torre-controle",        None,                     "torre_controle"),
    # Cadastros de sistema (GET fica livre — os selects do painel precisam dele).
    ("/api/tecnicos",              ("POST", "PUT", "DELETE"), "gerenciar_tecnicos"),
    ("/api/setores",               ("POST", "PUT", "DELETE"), "gerenciar_setores"),
    # Roteiros: escrita em fichas (inclui adicionar atendimento, otimizar...).
    ("/api/fichas",                ("POST", "PUT", "DELETE"), "roteiros"),
    # Verificar CEP: essas duas rotas de busca nunca tiveram regra mapeada
    # (achado em 2026-08-31, pedido pra liberar a Gabriela) — POST sem regra
    # fecha por padrão pra quem não é admin (ver fim de checar_acesso), então
    # cep_ver=True na pessoa não bastava, a busca sempre dava 403
    # "sem_regra_definida" mesmo com a aba visível.
    ("/api/verificar-cep",         None,                     "cep_ver"),
    ("/api/verificar-endereco",    None,                     "cep_ver"),
    # Atendimentos existentes: editar, mover, transferir, excluir.
    ("/api/servicos",              ("POST", "PUT", "DELETE"), "atendimentos"),
    # Peças, usuários, relatórios, chat da equipe.
    # "/api/pedidos-peca-os" tem que vir ANTES de "/api/pedidos" — senão o
    # startswith mais curto casaria primeiro (o hífen não conta como
    # fronteira) e "já pedi" de peça pedida na OS nunca exigiria
    # desfechos_ver, só pecas.
    ("/api/pedidos-peca-os",       None,                     "desfechos_ver"),
    ("/api/pedidos",               None,                     "pecas"),
    ("/api/cotacoes",              None,                     "cotacao"),
    ("/api/pecas-substituicao",    None,                     "cotacao"),
    ("/api/clientes",              None,                     "ordens_servico"),
    ("/api/ordens-servico",        None,                     "ordens_servico"),
    ("/api/usuarios",              None,                     "gerenciar_usuarios"),
    ("/api/permissoes",            None,                     "gerenciar_usuarios"),
    ("/api/equipe",                None,                     "chat_equipe"),
    ("/api/relatorios",            None,                     "relatorios"),
    ("/api/historico",             None,                     "relatorios"),
    ("/api/metricas",              None,                     "relatorios"),
    # "Pedidos com comprovante" é conteúdo da aba Peças, mesmo vivendo sob
    # /api/desfechos/... por causa de como foi implementado — por isso essa
    # regra, mais específica, vem ANTES da genérica de /api/desfechos (que é
    # a aba Atendimentos de verdade).
    ("/api/desfechos/pedidos",     None,                     "pecas"),
    ("/api/desfechos",             None,                     "desfechos_ver"),
    # Estoque: ver / editar / excluir.
    ("/api/estoque",               ("GET",),                 "estoque_ver"),
    ("/api/estoque",               ("POST", "PUT", "PATCH"), "estoque_editar"),
    ("/api/estoque",               ("DELETE",),              "estoque_excluir"),
    ("/api/vendas",                None,                     "vendas"),
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
    papel = (papel or "").strip()
    if papel == "admin":
        return {a: True for a in TODAS}
    ov = _overrides(permissoes_bruto)
    padrao = PADRAO_PAPEL_TECNICO if papel == "tecnico" else PADRAO_TECNICO
    return {a: bool(ov[a]) if a in ov else (a in padrao) for a in TODAS}


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
    # Peça no carro do técnico (/api/tecnicos/<id>/carro) é ESTOQUE, não
    # cadastro de técnico — mas o id no meio do path impede casar isso por
    # prefixo em REGRAS (que só faz startswith), daí o caso especial aqui,
    # ANTES do loop. Sem isso o POST caía na regra genérica de
    # /api/tecnicos e exigia gerenciar_tecnicos: quem só mexe em estoque
    # ficava travado, e quem só gerencia técnico dava entrada/saída de peça
    # sem ter permissão nenhuma de estoque.
    if path.startswith("/api/tecnicos/") and path.endswith("/carro") and metodo.upper() == "POST":
        return None if pode("estoque_editar") else "estoque_editar"

    # Trajeto do dia (/api/tecnicos/<id>/trajeto-hoje) é histórico de GPS --
    # mesma sensibilidade da Torre de Controle, mas o id no meio do path
    # também impede casar por prefixo simples (mesmo problema do /carro
    # acima). Pedido de 2026-09-04 ("replay do dia").
    if path.startswith("/api/tecnicos/") and path.endswith("/trajeto-hoje") and metodo.upper() == "GET":
        return None if pode("torre_controle") else "torre_controle"

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
