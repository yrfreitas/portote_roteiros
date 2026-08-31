from flask import Blueprint, jsonify, request, session

from database import (IS_PG, db_conn, execute, fetch_all, fetch_one,
                      insert_returning_id, sql)
from extensions import limiter
from routes.fichas import obter_ou_criar_ficha, recalcular_rota
from services.geo import geocode_cep

servicos_bp = Blueprint("servicos", __name__)

AVISO_IMPRECISO = ("Endereço aproximado (centroide do CEP). "
                   "Confira o número da casa para maior precisão.")

STATUS_SERVICO_VALIDOS = {"pendente", "concluido"}


def _servico_de_outro_tecnico(conn, ficha_id: int) -> bool:
    """True quando quem faz a requisição é um login "tecnico" mexendo num
    atendimento de ficha de OUTRO técnico.

    Mesma falha de escopo achada em 2026-08-31 nas rotas de listagem (ver
    routes/fichas.py e routes/tecnicos.py) — esta é a versão de ESCRITA: sem
    isso, um login de campo com a permissão "atendimentos" ligada (padrão
    para todo mundo) conseguia editar, dar baixa ou excluir o atendimento de
    QUALQUER colega, não só o próprio."""
    if session.get("papel") != "tecnico":
        return False
    ficha = fetch_one(conn, "SELECT tecnico_id FROM fichas WHERE id = ?", (ficha_id,))
    return not ficha or ficha.get("tecnico_id") != session.get("tecnico_id")

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


@servicos_bp.route("/servicos/buscar", methods=["GET"])
def buscar():
    """Acha em qual dia e com qual técnico um cliente está, por nome ou CEP —
    sem precisar abrir ficha por ficha até achar (era assim antes: 20+
    atendimentos, um por um, pra responder "o Fulano é hoje ou amanhã?").

    ?q= aceita nome parcial (case-insensitive) OU o CEP (com ou sem traço).
    """
    termo = (request.args.get("q") or "").strip()
    if len(termo) < 3:
        return jsonify({"resultados": []})

    condicoes = ["LOWER(s.cliente) LIKE ?"]
    params = [f"%{termo.lower()}%"]

    cep_digitos = "".join(c for c in termo if c.isdigit())
    if len(cep_digitos) >= 5:
        condicoes.append("s.cep LIKE ?")
        params.append(f"{cep_digitos}%")

    with db_conn() as conn:
        # Ficha em aberto primeiro — é quem está procurando "cadê o Fulano"
        # quer saber a próxima visita, não escavar o histórico de anos atrás.
        linhas = fetch_all(conn, f"""
            SELECT s.id AS servico_id, s.cliente, s.cep, s.endereco_completo,
                   s.status AS servico_status, f.id AS ficha_id, f.dia_semana,
                   f.data_referencia, f.status AS ficha_status,
                   t.id AS tecnico_id, t.nome AS tecnico_nome, t.cor AS tecnico_cor
              FROM servicos s
              JOIN fichas f ON f.id = s.ficha_id
              LEFT JOIN tecnicos t ON t.id = f.tecnico_id
             WHERE {' OR '.join(condicoes)}
             ORDER BY (CASE WHEN f.status = 'concluida' THEN 1 ELSE 0 END), f.id DESC
             LIMIT 25
        """, tuple(params))

    return jsonify({"resultados": linhas})


def aplicar_status_servico(conn, servico_id: int, novo_status: str) -> None:
    """UPDATE puro, sem validação — quem chama já garantiu que o status é
    válido e que o serviço existe e pertence a quem está pedindo a mudança.
    Compartilhado entre a rota admin (servicos_bp) e a rota escopada por
    token do técnico (tecnico_api_bp)."""
    if novo_status == "concluido":
        execute(conn, """
            UPDATE servicos SET status = ?, concluido_em = CURRENT_TIMESTAMP WHERE id = ?
        """, (novo_status, servico_id))
        # Chegou: o rastreio ao vivo perde o sentido e o link do cliente para
        # de expor posição. Fica aqui, no caminho central de conclusão, para
        # valer tanto pela tela do técnico quanto pela do painel.
        from routes.rastreio import encerrar_por_servico
        encerrar_por_servico(conn, servico_id)
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
    telefone = (data.get("telefone") or "").strip()

    if len(cep) != 8:
        return jsonify({"erro": "Informe um CEP válido com 8 dígitos"}), 400

    # Obrigatório desde 2026-08-25: sem número de contato, confirmar horário
    # ou avisar atraso dependia de achar o telefone em outro lugar (papel,
    # WhatsApp antigo) bem na hora que o técnico já estava a caminho.
    if not telefone:
        return jsonify({"erro": "Informe o telefone do cliente"}), 400

    # Setor virou obrigatório em 2026-08-13. Era opcional e ficava no fim do
    # formulário: 32 dos 38 pontos em aberto (84%) estavam sem classificação
    # nenhuma, o que tornava o relatório por setor inútil — não dava para dizer
    # quanto do mês foi Panasonic e quanto foi Philco. Ninguém preenche o que
    # dá para pular, então o jeito é não deixar pular.
    erro_setor, setor_id = _validar_setor(data.get("setor_id"))
    if erro_setor:
        return jsonify({"erro": erro_setor}), 400

    # Liga o atendimento a uma OS já existente — pedido de 2026-08-28, pra
    # cliente que já tem caso aberto não precisar redigitar tudo de novo
    # (ver addPuxarDadosDaOS no front). Mesma trava de sempre: valida que
    # a OS existe antes de gravar a referência.
    ordem_servico_id = data.get("ordem_servico_id")
    if ordem_servico_id:
        with db_conn() as conn:
            os_existe = fetch_one(conn, "SELECT id FROM ordens_servico WHERE id = ?", (ordem_servico_id,))
        if not os_existe:
            return jsonify({"erro": "Ordem de serviço não encontrada"}), 404

    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
    if not ficha:
        return jsonify({"erro": "Ficha não encontrada"}), 404
    if session.get("papel") == "tecnico" and ficha.get("tecnico_id") != session.get("tecnico_id"):
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
                 cliente, descricao, numero, tipo_aparelho, modelo, numero_os,
                 setor_id, telefone, ordem_servico_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ficha_id, cep, geo.endereco, geo.lat, geo.lng,
              (data.get("cliente") or "").strip(),
              (data.get("descricao") or "").strip(),
              numero,
              (data.get("tipo_aparelho") or "").strip(),
              (data.get("modelo") or "").strip(),
              (data.get("numero_os") or "").strip(),
              setor_id, telefone, ordem_servico_id or None))

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
        if _servico_de_outro_tecnico(conn, servico["ficha_id"]):
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

    # Mesma régua do setor: telefone virou obrigatório em 2026-08-25, então
    # editar um ponto de antes dessa data também força preencher — sem isso
    # o campo nunca seria corrigido pra quem já passou pela tela uma vez.
    telefone = (data.get("telefone") if "telefone" in data
                else servico.get("telefone") or "").strip()
    if not telefone:
        return jsonify({"erro": "Informe o telefone do cliente"}), 400

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
                   setor_id = ?, telefone = ?
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
              setor_id, telefone,
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
        servico = fetch_one(conn, """
            SELECT sv.* FROM servicos sv JOIN fichas f ON f.id = sv.ficha_id
             WHERE sv.id = ?
        """, (servico_id,))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404
        if _servico_de_outro_tecnico(conn, servico["ficha_id"]):
            return jsonify({"erro": "Serviço não encontrado"}), 404
        aplicar_status_servico(conn, servico_id, novo_status)
        # Mesma função que o app do técnico usa: o desfecho tem de ser gravado
        # igual venha de onde vier, senão as duas origens divergem e o
        # relatório passa a depender de quem concluiu.
        from routes.tecnico_api import _gravar_desfecho
        desfecho = _gravar_desfecho(conn, servico, novo_status,
                                    data.get("desfecho"),
                                    (session.get("usuario_nome") or "").strip())

    return jsonify({"mensagem": f"Serviço marcado como {novo_status}",
                    "status": novo_status, "desfecho": desfecho})


@servicos_bp.route("/servicos/<int:servico_id>", methods=["DELETE"])
def remover_servico(servico_id):
    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, "SELECT * FROM servicos WHERE id = ?", (servico_id,))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404
        if _servico_de_outro_tecnico(conn, servico["ficha_id"]):
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


@servicos_bp.route("/servicos/<int:servico_id>/mover", methods=["PUT"])
def mover_servico(servico_id):
    """Move o atendimento para OUTRO DIA (outra ficha), sem apagar e recriar.

    Pedido do Kalebe em 2026-08-20: hoje, trocar um cliente de dia obriga a
    apagar o ponto e adicionar de novo — perdendo status, nº da OS e o
    trabalho de digitar tudo outra vez.

    A ficha de destino é do MESMO técnico: mudar de técnico já tem rota
    própria (`/tecnico`). Aqui só muda o dia. As duas rotas são recalculadas
    porque uma perdeu parada e a outra ganhou.
    """
    data = request.get_json(silent=True) or {}
    try:
        ficha_destino = int(data.get("ficha_id"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Informe o dia de destino"}), 400

    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, """
            SELECT sv.id, sv.ficha_id, f.tecnico_id
              FROM servicos sv JOIN fichas f ON f.id = sv.ficha_id
             WHERE sv.id = ?
        """, (servico_id,))
        if not servico:
            return jsonify({"erro": "Atendimento não encontrado"}), 404

        ficha_origem = servico["ficha_id"]
        if ficha_destino == ficha_origem:
            return jsonify({"mensagem": "O atendimento já está nesse dia"})

        destino = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_destino,))
        if not destino:
            return jsonify({"erro": "Dia de destino não encontrado"}), 404
        if destino.get("status") == "concluida":
            return jsonify({"erro": "Não dá para mover para um dia já concluído"}), 400
        # Trava de coerência: a ficha destino tem que ser do mesmo técnico. Sem
        # isso, "mover de dia" viraria um jeito escondido de trocar de técnico
        # sem encerrar o rastreio, que a rota /tecnico faz de propósito.
        if destino.get("tecnico_id") != servico.get("tecnico_id"):
            return jsonify({"erro": "Esse dia é de outro técnico. Use "
                                    "'transferir' para mudar de técnico."}), 400

        # Rastreio aberto do ponto perde o sentido: o dia mudou.
        from routes.rastreio import encerrar_por_servico
        encerrar_por_servico(conn, servico_id)

        # Entra no fim; a otimização recoloca no lugar certo.
        ultima = fetch_one(conn, "SELECT MAX(ordem) AS m FROM servicos WHERE ficha_id = ?",
                           (ficha_destino,))
        execute(conn, "UPDATE servicos SET ficha_id = ?, ordem = ? WHERE id = ?",
                (ficha_destino, (ultima or {}).get("m") or 0, servico_id))

        for fid in (ficha_origem, ficha_destino):
            f = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (fid,))
            recalcular_rota(conn, fid, f)

    return jsonify({"mensagem": "Atendimento movido de dia",
                    "ficha_destino": ficha_destino, "ficha_origem": ficha_origem})


@servicos_bp.route("/servicos/<int:servico_id>/tecnico", methods=["PUT"])
def transferir_servico(servico_id):
    """Move UM ponto para outro técnico, no mesmo dia.

    Diferente de transferir a ficha inteira: aqui só um cliente muda de mãos,
    que é o caso real da Porto Tec — a rota do dia é do Pedro e um atendimento
    específico vai com o Igor.

    O ponto precisa cair numa ficha DO DESTINO, porque é a ficha que carrega o
    técnico. Se ele já tem ficha aberta no mesmo dia, o ponto entra nela; se
    não tem, uma é criada copiando dia, data e ponto de partida da origem —
    sem isso o Kalebe teria que criar a ficha na mão antes de cada
    transferência, e ninguém faria isso no meio da correria.

    As DUAS rotas são recalculadas: a de origem perdeu uma parada e a de
    destino ganhou. Deixar a quilometragem velha faria o painel mentir sobre
    o dia dos dois.
    """
    data = request.get_json(silent=True) or {}
    try:
        novo_tecnico = int(data.get("tecnico_id"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Informe o técnico de destino"}), 400

    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, """
            SELECT sv.*, f.id AS f_id, f.tecnico_id, f.dia_semana,
                   f.data_referencia, f.ponto_partida, f.ponto_partida_cep,
                   f.ponto_partida_lat, f.ponto_partida_lng
              FROM servicos sv JOIN fichas f ON f.id = sv.ficha_id
             WHERE sv.id = ?
        """, (servico_id,))
        if not servico:
            return jsonify({"erro": "Ponto não encontrado"}), 404

        destino = fetch_one(conn, "SELECT id, nome FROM tecnicos WHERE id = ?",
                            (novo_tecnico,))
        if not destino:
            return jsonify({"erro": "Técnico de destino não encontrado"}), 404

        if servico.get("tecnico_id") == novo_tecnico:
            return jsonify({"mensagem": f"O ponto já é do {destino['nome']}"})

        ficha_origem = servico["f_id"]

        # Ficha do destino no MESMO dia. Só reaproveita a que está em aberto:
        # jogar ponto novo dentro de rota já concluída mexeria em número de
        # dia fechado. obter_ou_criar_ficha() é travado contra duas
        # transferências simultâneas criarem ficha duplicada — ver fichas.py.
        ficha_destino, criou_ficha = obter_ou_criar_ficha(
            conn, novo_tecnico, servico["dia_semana"], servico.get("data_referencia"),
            ponto_partida=servico.get("ponto_partida"),
            ponto_partida_cep=servico.get("ponto_partida_cep"),
            ponto_partida_lat=servico.get("ponto_partida_lat"),
            ponto_partida_lng=servico.get("ponto_partida_lng"))

        # Rastreio aberto some junto: quem vai ao cliente mudou, e a posição
        # do técnico antigo não diz mais nada sobre esse atendimento.
        from routes.rastreio import encerrar_por_servico
        encerrar_por_servico(conn, servico_id)

        # Entra no fim da rota do destino; a otimização abaixo põe no lugar.
        ultima = fetch_one(conn, "SELECT MAX(ordem) AS m FROM servicos WHERE ficha_id = ?",
                           (ficha_destino,))
        execute(conn, "UPDATE servicos SET ficha_id = ?, ordem = ? WHERE id = ?",
                (ficha_destino, (ultima or {}).get("m") or 0, servico_id))

        for fid in (ficha_origem, ficha_destino):
            f = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (fid,))
            recalcular_rota(conn, fid, f)

    return jsonify({
        "mensagem": f"{servico.get('cliente') or 'Ponto'} transferido para {destino['nome']}"
                    + (" (ficha nova criada)" if criou_ficha else ""),
        "ficha_destino": ficha_destino,
        "ficha_origem": ficha_origem,
        "ficha_criada": criou_ficha,
    })


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

@servicos_bp.route("/servicos/<int:servico_id>/fotos", methods=["GET"])
def fotos_do_servico(servico_id):
    """Fotos enviadas pelo técnico neste atendimento.

    Endpoint separado, e não junto da listagem da ficha: uma imagem em base64
    por atendimento tornaria pesada toda abertura de rota, quando na prática
    só se olha a foto de um ponto por vez.
    """
    with db_conn() as conn:
        fotos = fetch_all(conn, sql(
            "SELECT id, foto, legenda, criado_em, enviado_por "
            "FROM servico_foto WHERE servico_id = ? ORDER BY id"), (servico_id,))
    return jsonify({"fotos": fotos})
