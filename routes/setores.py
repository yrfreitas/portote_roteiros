"""Setores: separa o trabalho por marca/frente de negócio.

Panasonic, Philco, Loja — cada atendimento pertence a um setor, e assim dá
pra ver quanto cada frente representa sem misturar tudo num balde só.

Setor é uma dimensão do atendimento, não da ficha: uma mesma rota do dia
pode ter uma geladeira Panasonic e uma lavadora Philco, e separar no nível
do ponto é o que permite contabilizar certo.
"""
import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from database import (IS_PG, db_conn, execute, fetch_all, fetch_one,
                      insert_returning_id)

log = logging.getLogger("portotec.setores")

setores_bp = Blueprint("setores", __name__)

CORES_PADRAO = ["#1a6fd4", "#e05c2a", "#2aa05c", "#9b3db8",
                "#d4a01a", "#2aaab8", "#d41a5c", "#5c7ad4"]

# "ativo" é BOOLEAN no Postgres e INTEGER no SQLite. Comparar com 1 quebra no
# Postgres (tipos incompatíveis) e comparar com TRUE não existe no SQLite —
# então o predicado tem que ser escolhido conforme o banco.
ATIVO = "s.ativo IS TRUE" if IS_PG else "s.ativo = 1"


@setores_bp.route("/setores", methods=["GET"])
def listar():
    """Setores + quanto cada um tem de atendimento.

    ?todos=true inclui os desativados (por padrão só os ativos, que é o que
    interessa na hora de classificar um atendimento novo).
    """
    todos = str(request.args.get("todos", "")).lower() in ("1", "true", "sim")

    filtro = "" if todos else f"WHERE {ATIVO}"

    with db_conn() as conn:
        setores = fetch_all(conn, f"""
            SELECT s.*,
                   COUNT(sv.id) AS total_servicos,
                   COUNT(CASE WHEN sv.status = 'concluido' THEN 1 END) AS concluidos
              FROM setores s
              LEFT JOIN servicos sv ON sv.setor_id = s.id
              {filtro}
             GROUP BY s.id
             ORDER BY s.nome
        """)

        # Atendimentos ainda sem setor: some no relatório se ninguém olhar.
        sem_setor = fetch_one(conn, """
            SELECT COUNT(*) AS total FROM servicos WHERE setor_id IS NULL
        """)

    return jsonify({
        "setores": setores,
        "sem_setor": (sem_setor or {}).get("total", 0),
    })


@setores_bp.route("/setores", methods=["POST"])
def criar():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()

    if not nome:
        return jsonify({"erro": "Nome é obrigatório"}), 400
    if len(nome) > 60:
        return jsonify({"erro": "Nome muito longo (máx. 60 caracteres)"}), 400

    with db_conn(commit=True) as conn:
        existente = fetch_one(
            conn, "SELECT id FROM setores WHERE LOWER(nome) = LOWER(?)", (nome,)
        )
        if existente:
            return jsonify({"erro": f'Já existe um setor "{nome}"'}), 409

        total = fetch_one(conn, "SELECT COUNT(*) AS total FROM setores")["total"]
        cor = data.get("cor") or CORES_PADRAO[total % len(CORES_PADRAO)]

        setor_id = insert_returning_id(
            conn, "INSERT INTO setores (nome, cor) VALUES (?, ?)", (nome, cor)
        )

    return jsonify({"id": setor_id, "nome": nome, "cor": cor}), 201


@setores_bp.route("/setores/<int:setor_id>", methods=["PUT"])
def editar(setor_id):
    data = request.get_json(silent=True) or {}

    with db_conn(commit=True) as conn:
        setor = fetch_one(conn, "SELECT * FROM setores WHERE id = ?", (setor_id,))
        if not setor:
            return jsonify({"erro": "Setor não encontrado"}), 404

        nome = (data.get("nome") if data.get("nome") is not None
                else setor["nome"]).strip()
        if not nome:
            return jsonify({"erro": "Nome é obrigatório"}), 400

        cor = data.get("cor") or setor["cor"]
        ativo = data.get("ativo")
        ativo = setor["ativo"] if ativo is None else bool(ativo)

        execute(conn, """
            UPDATE setores SET nome = ?, cor = ?, ativo = ? WHERE id = ?
        """, (nome, cor, ativo, setor_id))

    return jsonify({"mensagem": "Setor atualizado", "id": setor_id})


@setores_bp.route("/setores/<int:setor_id>", methods=["DELETE"])
def remover(setor_id):
    """Desativa em vez de apagar quando já tem atendimento ligado.

    Apagar de verdade deixaria os atendimentos órfãos e sumiria com o
    histórico daquela frente — que é justamente o que o setor serve pra
    preservar. Só apaga o que nunca foi usado.
    """
    with db_conn(commit=True) as conn:
        setor = fetch_one(conn, "SELECT * FROM setores WHERE id = ?", (setor_id,))
        if not setor:
            return jsonify({"erro": "Setor não encontrado"}), 404

        usos = fetch_one(
            conn, "SELECT COUNT(*) AS total FROM servicos WHERE setor_id = ?",
            (setor_id,)
        )["total"]

        if usos:
            execute(conn, "UPDATE setores SET ativo = ? WHERE id = ?", (False, setor_id))
            return jsonify({
                "mensagem": f'Setor "{setor["nome"]}" desativado '
                            f"({usos} atendimento(s) mantidos no histórico)",
                "desativado": True,
            })

        execute(conn, "DELETE FROM setores WHERE id = ?", (setor_id,))

    return jsonify({"mensagem": f'Setor "{setor["nome"]}" removido', "removido": True})


@setores_bp.route("/setores/resumo", methods=["GET"])
def resumo():
    """Números por setor para a Visão Geral.

    Conta por padrão só o trabalho EM ABERTO (fichas não concluídas). Antes
    somava tudo desde sempre, sem filtro de data nem de status: num painel
    chamado "Visão Geral" isso ia virando um acumulado de meses que misturava
    o serviço de hoje com tudo que já foi fechado. O acumulado histórico tem
    aba própria — `?escopo=tudo` devolve ele para quem precisar.

    Devolve também `total` e `sem_setor`, e essa é a parte que importa: sem o
    total real, o front calculava a fatia de cada setor dividindo pela soma dos
    pontos JÁ classificados. Com 5 pontos classificados de 44, Panasonic
    aparecia como 100% do trabalho quando era 11%. O percentual precisa do
    denominador certo, e os pontos sem setor precisam aparecer — enquanto forem
    invisíveis, ninguém vai classificá-los.
    """
    escopo_tudo = request.args.get("escopo") == "tudo"
    filtro_ficha = "" if escopo_tudo else "WHERE f.status <> 'concluida'"

    with db_conn() as conn:
        # Subconsulta em vez de filtrar no ON do LEFT JOIN: com o filtro no ON,
        # os serviços de ficha concluída continuariam entrando na contagem
        # (a linha existe, só vem com f.* nulo). Restringindo antes, o LEFT
        # JOIN volta a significar o que se espera dele.
        linhas = fetch_all(conn, f"""
            SELECT s.id, s.nome, s.cor,
                   COUNT(sv.id) AS pontos,
                   COUNT(CASE WHEN sv.status = 'concluido' THEN 1 END) AS concluidos,
                   COUNT(DISTINCT sv.ficha_id) AS rotas
              FROM setores s
              LEFT JOIN (
                   SELECT sv.id, sv.setor_id, sv.status, sv.ficha_id
                     FROM servicos sv
                     JOIN fichas f ON f.id = sv.ficha_id
                     {filtro_ficha}
              ) sv ON sv.setor_id = s.id
             WHERE {ATIVO}
             GROUP BY s.id, s.nome, s.cor
             ORDER BY pontos DESC, s.nome
        """)

        total = fetch_one(conn, f"""
            SELECT COUNT(*) AS total
              FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id
              {filtro_ficha}
        """)["total"]

    # sem_setor por subtração, não por "setor_id IS NULL": assim os pontos
    # presos num setor desativado também entram na conta em vez de sumirem do
    # painel sem deixar rastro.
    classificados = sum(linha["pontos"] for linha in linhas)

    # Alertas da Visão Geral (pedido de 2026-09-02) pegam carona aqui — é o
    # mesmo endpoint que a tela já chama pra montar o resumo por setor, então
    # nenhum polling novo. "Atrasada" e "esperando muito" são limiares
    # arbitrários (3 e 2 dias) — não existe SLA configurável no sistema hoje,
    # e um número fixo já é bem melhor que nenhum alerta.
    with db_conn() as conn:
        limite_os = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        os_atrasadas = fetch_one(conn, """
            SELECT COUNT(*) AS n FROM ordens_servico
             WHERE status = 'aguardando_agendamento' AND criado_em < ?
        """, (limite_os,))["n"]

        limite_peca = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        pecas_esperando_muito = fetch_one(conn, """
            SELECT
                (SELECT COUNT(*) FROM servico_desfecho
                  WHERE desfecho = 'precisa_peca' AND pedido_em IS NULL
                    AND registrado_em < ?) +
                (SELECT COUNT(*) FROM pedido_peca_os
                  WHERE pedido_em IS NULL AND criado_em < ?) AS n
        """, (limite_peca, limite_peca))["n"]

        # Hoje x ontem (pedido de 2026-09-02): comparação por INTERVALO de data
        # calculado em Python, não por função de data do banco — SQLite e
        # Postgres não compartilham a mesma sintaxe (ver comentário em
        # routes/fichas.py) e isso aqui já resolve pros dois.
        hoje_inicio = datetime.now().strftime("%Y-%m-%d 00:00:00")
        ontem_inicio = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        concluidos = fetch_one(conn, """
            SELECT
                (SELECT COUNT(*) FROM servico_desfecho WHERE registrado_em >= ?) AS hoje,
                (SELECT COUNT(*) FROM servico_desfecho
                  WHERE registrado_em >= ? AND registrado_em < ?) AS ontem
        """, (hoje_inicio, ontem_inicio, hoje_inicio))

        estoque_baixo = fetch_one(conn, """
            SELECT COUNT(*) AS n FROM estoque_itens
             WHERE minimo > 0 AND saldo <= minimo
        """)["n"]

    return jsonify({
        "setores": linhas,
        "total": total,
        "sem_setor": total - classificados,
        "escopo": "tudo" if escopo_tudo else "abertas",
        "os_atrasadas": os_atrasadas,
        "pecas_esperando_muito": pecas_esperando_muito,
        "concluidos_hoje": concluidos["hoje"],
        "concluidos_ontem": concluidos["ontem"],
        "estoque_abaixo_minimo": estoque_baixo,
    })
