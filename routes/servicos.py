from flask import Blueprint, jsonify, request

from database import IS_PG, db_conn, execute, fetch_all, fetch_one
from extensions import limiter
from routes.fichas import recalcular_rota
from services.geo import geocode_cep

servicos_bp = Blueprint("servicos", __name__)

AVISO_IMPRECISO = ("Endereço aproximado (centroide do CEP). "
                   "Confira o número da casa para maior precisão.")

STATUS_SERVICO_VALIDOS = {"pendente", "concluido"}

# "ativo" é BOOLEAN no Postgres e INTEGER no SQLite — comparar com o literal
# errado quebra num dos dois. Mesmo motivo do ATIVO em routes/setores.py.
_SETOR_ATIVO = "ativo IS TRUE" if IS_PG else "ativo = 1"


def _validar_setor(valor):
    """Devolve (mensagem_de_erro, setor_id). Erro vazio significa que passou.

    Rejeita setor ausente, inexistente e desativado. O desativado importa: o
    sistema desativa em vez de apagar setor em uso, e sem esta checagem daria
    para classificar ponto novo numa frente que não existe mais.
    """
    if valor in (None, "", 0, "0"):
        return "Escolha o setor do atendimento (Panasonic, Philco, Loja...).", None

    try:
        setor_id = int(valor)
    except (TypeError, ValueError):
        return "Setor inválido.", None

    with db_conn() as conn:
        setor = fetch_one(
            conn, f"SELECT id FROM setores WHERE id = ? AND {_SETOR_ATIVO}", (setor_id,)
        )
    if not setor:
        return "Esse setor não existe ou foi desativado.", None

    return "", setor_id


def aplicar_status_servico(conn, servico_id: int, novo_status: str) -> None:
    """UPDATE puro, sem validação — quem chama já garantiu que o status é
    válido e que o serviço existe e pertence a quem está pedindo a mudança.
    Compartilhado entre a rota admin (servicos_bp) e a rota escopada por
    token do técnico (tecnico_api_bp)."""
    if novo_status == "concluido":
        execute(conn, """
            UPDATE servicos SET status = ?, concluido_em = CURRENT_TIMESTAMP WHERE id = ?
        """, (novo_status, servico_id))
    else:
        execute(conn, """
            UPDATE servicos SET status = ?, concluido_em = NULL WHERE id = ?
        """, (novo_status, servico_id))


@servicos_bp.route("/fichas/<int:ficha_id>/servicos", methods=["POST"])
@limiter.limit("60 per minute")
def adicionar_servico(ficha_id):
    data = request.get_json(silent=True) or {}

    cep = "".join(c for c in (data.get("cep") or "") if c.isdigit())
    numero = (data.get("numero") or "").strip()

    if len(cep) != 8:
        return jsonify({"erro": "Informe um CEP válido com 8 dígitos"}), 400

    # Setor virou obrigatório em 2026-08-13. Era opcional e ficava no fim do
    # formulário: 32 dos 38 pontos em aberto (84%) estavam sem classificação
    # nenhuma, o que tornava o relatório por setor inútil — não dava para dizer
    # quanto do mês foi Panasonic e quanto foi Philco. Ninguém preenche o que
    # dá para pular, então o jeito é não deixar pular.
    erro_setor, setor_id = _validar_setor(data.get("setor_id"))
    if erro_setor:
        return jsonify({"erro": erro_setor}), 400

    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
    if not ficha:
        return jsonify({"erro": "Ficha não encontrada"}), 404

    geo = geocode_cep(cep, numero=numero)
    if not geo:
        return jsonify({
            "erro": f"CEP {cep[:5]}-{cep[5:]} não encontrado. "
                    f"Confira o número e tente novamente."
        }), 400

    with db_conn(commit=True) as conn:
        execute(conn, """
            INSERT INTO servicos
                (ficha_id, cep, endereco_completo, lat, lng,
                 cliente, descricao, numero, tipo_aparelho, modelo, numero_os, setor_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ficha_id, cep, geo.endereco, geo.lat, geo.lng,
              (data.get("cliente") or "").strip(),
              (data.get("descricao") or "").strip(),
              numero,
              (data.get("tipo_aparelho") or "").strip(),
              (data.get("modelo") or "").strip(),
              (data.get("numero_os") or "").strip(),
              setor_id))

        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        resultado = recalcular_rota(conn, ficha_id, ficha)

    resposta = {
        "mensagem": "Serviço adicionado e rota otimizada",
        "endereco": geo.endereco,
        "numero":   numero,
        **resultado,
    }

    if not geo.preciso:
        resposta["aviso"] = AVISO_IMPRECISO
    elif resultado.get("sem_partida"):
        resposta["aviso"] = ("Ponto adicionado, mas esta ficha não tem CEP de "
                             "partida — a rota não pode ser otimizada ainda.")

    return jsonify(resposta), 201


@servicos_bp.route("/servicos/<int:servico_id>", methods=["PUT"])
def editar_servico(servico_id):
    data = request.get_json(silent=True) or {}

    with db_conn() as conn:
        servico = fetch_one(conn, "SELECT * FROM servicos WHERE id = ?", (servico_id,))
    if not servico:
        return jsonify({"erro": "Serviço não encontrado"}), 404

    # Editar também exige setor. Assim, abrir um ponto antigo para corrigir
    # qualquer coisa já força a classificação que faltava, em vez de perpetuar
    # o ponto órfão. Se o cliente não mandou o campo, cai no que já estava —
    # só bloqueia mesmo quando continua vazio dos dois lados.
    erro_setor, setor_id = _validar_setor(
        data.get("setor_id") if "setor_id" in data else servico.get("setor_id")
    )
    if erro_setor:
        return jsonify({"erro": erro_setor}), 400

    cep_novo = "".join(c for c in (data.get("cep") or servico["cep"]) if c.isdigit())
    numero_novo = (data.get("numero") if data.get("numero") is not None
                   else servico.get("numero") or "").strip()

    mudou_local = (cep_novo != servico["cep"]
                   or numero_novo != (servico.get("numero") or ""))

    lat, lng = servico.get("lat"), servico.get("lng")
    endereco = servico.get("endereco_completo")
    geo = None

    if mudou_local:
        if len(cep_novo) != 8:
            return jsonify({"erro": "Informe um CEP válido com 8 dígitos"}), 400
        geo = geocode_cep(cep_novo, numero=numero_novo)
        if not geo:
            return jsonify({"erro": f"CEP {cep_novo} não encontrado"}), 400
        lat, lng, endereco = geo.lat, geo.lng, geo.endereco

    with db_conn(commit=True) as conn:
        execute(conn, """
            UPDATE servicos
               SET cep = ?, numero = ?, endereco_completo = ?,
                   lat = ?, lng = ?, cliente = ?, descricao = ?,
                   tipo_aparelho = ?, modelo = ?, numero_os = ?,
                   setor_id = ?
             WHERE id = ?
        """, (cep_novo, numero_novo, endereco, lat, lng,
              (data.get("cliente") if data.get("cliente") is not None
               else servico.get("cliente") or ""),
              (data.get("descricao") if data.get("descricao") is not None
               else servico.get("descricao") or ""),
              (data.get("tipo_aparelho") if data.get("tipo_aparelho") is not None
               else servico.get("tipo_aparelho") or ""),
              (data.get("modelo") if data.get("modelo") is not None
               else servico.get("modelo") or ""),
              (data.get("numero_os") if data.get("numero_os") is not None
               else servico.get("numero_os") or ""),
              setor_id,
              servico_id))

        ficha_id = servico["ficha_id"]
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        resultado = recalcular_rota(conn, ficha_id, ficha) if mudou_local else {}

    resposta = {"mensagem": "Serviço atualizado", "endereco": endereco, **resultado}
    if geo and not geo.preciso:
        resposta["aviso"] = AVISO_IMPRECISO
    return jsonify(resposta)


@servicos_bp.route("/servicos/<int:servico_id>/status", methods=["PUT"])
def alterar_status_servico(servico_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_SERVICO_VALIDOS:
        return jsonify({
            "erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_SERVICO_VALIDOS))}"
        }), 400

    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, "SELECT id FROM servicos WHERE id = ?", (servico_id,))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404
        aplicar_status_servico(conn, servico_id, novo_status)

    return jsonify({"mensagem": f"Serviço marcado como {novo_status}", "status": novo_status})


@servicos_bp.route("/servicos/<int:servico_id>", methods=["DELETE"])
def remover_servico(servico_id):
    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, "SELECT * FROM servicos WHERE id = ?", (servico_id,))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404

        ficha_id = servico["ficha_id"]
        execute(conn, "DELETE FROM servicos WHERE id = ?", (servico_id,))

        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        resultado = recalcular_rota(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Serviço removido e rota recalculada", **resultado})


# ─── Pontos órfãos: os que ficaram sem setor de antes da obrigatoriedade ──
# Tornar o campo obrigatório resolve daqui pra frente, mas não conserta o
# passado: a base já tinha 32 pontos sem classificação. Sem uma forma de
# atribuir em lote, a única saída seria abrir ponto por ponto — que é
# exatamente o atrito que fez ninguém preencher em primeiro lugar.


@servicos_bp.route("/servicos/sem-setor", methods=["GET"])
def listar_sem_setor():
    """Pontos sem setor, agrupáveis por ficha. Só de rotas ainda em aberto:
    reclassificar rota já fechada mexeria em número de mês que já passou."""
    incluir_concluidas = str(request.args.get("todas", "")).lower() in ("1", "true", "sim")
    filtro = "" if incluir_concluidas else "AND f.status <> 'concluida'"

    with db_conn() as conn:
        linhas = fetch_all(conn, f"""
            SELECT sv.id, sv.cliente, sv.tipo_aparelho, sv.modelo,
                   sv.endereco_completo, sv.numero_os,
                   f.id AS ficha_id, f.dia_semana, f.status AS ficha_status,
                   t.nome AS tecnico_nome, t.cor AS tecnico_cor
              FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id
              LEFT JOIN tecnicos t ON t.id = f.tecnico_id
             WHERE sv.setor_id IS NULL {filtro}
             ORDER BY f.id DESC, sv.ordem, sv.id
        """)

    return jsonify({"servicos": linhas, "total": len(linhas)})


@servicos_bp.route("/servicos/setor-em-lote", methods=["PUT"])
def definir_setor_em_lote():
    data = request.get_json(silent=True) or {}

    erro_setor, setor_id = _validar_setor(data.get("setor_id"))
    if erro_setor:
        return jsonify({"erro": erro_setor}), 400

    ids = data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"erro": "Selecione ao menos um ponto."}), 400

    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        return jsonify({"erro": "Lista de pontos inválida."}), 400

    # Limite defensivo: o IN abaixo monta um placeholder por id, e uma lista
    # gigante viraria uma query absurda. 500 cobre qualquer uso real aqui.
    if len(ids) > 500:
        return jsonify({"erro": "Selecione no máximo 500 pontos por vez."}), 400

    marcadores = ", ".join("?" for _ in ids)
    with db_conn(commit=True) as conn:
        alteradas = execute(
            conn,
            f"UPDATE servicos SET setor_id = ? WHERE id IN ({marcadores})",
            tuple([setor_id] + ids),
        )

    return jsonify({
        "mensagem": f"{alteradas} ponto{'s' if alteradas != 1 else ''} classificado"
                    f"{'s' if alteradas != 1 else ''}.",
        "atualizados": alteradas,
    })