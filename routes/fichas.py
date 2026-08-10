from flask import Blueprint, jsonify, request

from database import db_conn, execute, fetch_all, fetch_one, insert_returning_id
from services.geo import geocode_cep
from services.otimizador import (
    MINUTOS_PARADA, calcular_rota_fixa, calcular_tempo, otimizar_rota,
)
from services.push import notificar_tecnico

fichas_bp = Blueprint("fichas", __name__)

DIAS_VALIDOS = {
    "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado", "Domingo",
}


@fichas_bp.route("/fichas", methods=["GET"])
def listar_fichas():
    tecnico_id = request.args.get("tecnico_id")
    status = request.args.get("status")

    condicoes, params = [], []
    if tecnico_id:
        if not str(tecnico_id).isdigit():
            return jsonify({"erro": "tecnico_id inválido"}), 400
        condicoes.append("f.tecnico_id = ?")
        params.append(int(tecnico_id))
    if status:
        condicoes.append("f.status = ?")
        params.append(status)

    filtro = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""

    query = f"""
        SELECT f.*,
               COUNT(s.id) AS total_servicos,
               t.nome AS tecnico_nome,
               t.cor  AS tecnico_cor
        FROM fichas f
        LEFT JOIN servicos s ON s.ficha_id = f.id
        LEFT JOIN tecnicos t ON t.id = f.tecnico_id
        {filtro}
        GROUP BY f.id, t.nome, t.cor
        ORDER BY f.updated_at DESC, f.id DESC
    """

    with db_conn() as conn:
        return jsonify(fetch_all(conn, query, tuple(params)))


@fichas_bp.route("/fichas", methods=["POST"])
def criar_ficha():
    data = request.get_json(silent=True) or {}

    dia = (data.get("dia_semana") or "").strip()
    tecnico_id = data.get("tecnico_id")

    if not dia:
        return jsonify({"erro": "dia_semana é obrigatório"}), 400
    if dia not in DIAS_VALIDOS:
        return jsonify({"erro": f"Dia da semana inválido: {dia}"}), 400
    if not tecnico_id:
        return jsonify({"erro": "tecnico_id é obrigatório"}), 400

    try:
        tecnico_id = int(tecnico_id)
    except (TypeError, ValueError):
        return jsonify({"erro": "tecnico_id inválido"}), 400

    partida = (data.get("ponto_partida") or "").strip()
    partida_cep = "".join(c for c in (data.get("ponto_partida_cep") or "") if c.isdigit())
    numero_partida = (data.get("ponto_partida_numero") or "").strip()

    lat_p = lng_p = None
    aviso = None

    if partida_cep:
        geo = geocode_cep(partida_cep, numero=numero_partida)
        if geo:
            lat_p, lng_p = geo.lat, geo.lng
            if not partida:
                partida = geo.endereco
        else:
            aviso = ("Não foi possível localizar o CEP de partida. "
                     "A ficha foi criada, mas a rota só será otimizada "
                     "depois que você corrigir o ponto de partida.")

    with db_conn(commit=True) as conn:
        tecnico = fetch_one(conn, "SELECT id FROM tecnicos WHERE id = ?", (tecnico_id,))
        if not tecnico:
            return jsonify({"erro": "Técnico não encontrado"}), 404

        ficha_id = insert_returning_id(conn, """
            INSERT INTO fichas
                (tecnico_id, dia_semana, data_referencia, ponto_partida,
                 ponto_partida_cep, ponto_partida_lat, ponto_partida_lng)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tecnico_id, dia, data.get("data_referencia", ""),
              partida, partida_cep, lat_p, lng_p))

    notificar_tecnico(
        tecnico_id, "Nova rota atribuída",
        f"Você tem uma nova ficha de {dia} pra conferir.",
    )

    resposta = {"id": ficha_id, "mensagem": "Ficha criada com sucesso"}
    if aviso:
        resposta["aviso"] = aviso
    return jsonify(resposta), 201


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["GET"])
def obter_ficha(ficha_id):
    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(
            conn,
            "SELECT * FROM servicos WHERE ficha_id = ? ORDER BY ordem, id",
            (ficha_id,),
        )

    dist = ficha.get("distancia_total") or 0.0

    resumo = {
        "distancia_km":  round(dist, 2),
        "tempo_minutos": calcular_tempo(dist, len(servicos)),
        "total_servicos": len(servicos),
        "sem_coordenada": sum(1 for s in servicos if s.get("lat") is None),
    }

    return jsonify({"ficha": ficha, "servicos": servicos, "resumo": resumo})


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["DELETE"])
def deletar_ficha(ficha_id):
    with db_conn(commit=True) as conn:
        execute(conn, "DELETE FROM servicos WHERE ficha_id = ?", (ficha_id,))
        apagadas = execute(conn, "DELETE FROM fichas WHERE id = ?", (ficha_id,))

    if not apagadas:
        return jsonify({"erro": "Ficha não encontrada"}), 404
    return jsonify({"mensagem": "Ficha removida"})


STATUS_VALIDOS = {"pendente", "concluida"}


@fichas_bp.route("/fichas/<int:ficha_id>/status", methods=["PUT"])
def alterar_status_ficha(ficha_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_VALIDOS:
        return jsonify({"erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_VALIDOS))}"}), 400

    with db_conn(commit=True) as conn:
        ficha = fetch_one(conn, "SELECT id FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        if novo_status == "concluida":
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
            """, (novo_status, ficha_id))
        else:
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = NULL,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
            """, (novo_status, ficha_id))

    return jsonify({"mensagem": f"Ficha marcada como {novo_status}", "status": novo_status})


@fichas_bp.route("/fichas/<int:ficha_id>/otimizar", methods=["POST"])
def otimizar_ficha(ficha_id):
    with db_conn(commit=True) as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404
        resultado = recalcular_rota(conn, ficha_id, ficha)

    return jsonify(resultado)


@fichas_bp.route("/fichas/<int:ficha_id>/reordenar", methods=["PUT"])
def reordenar_servicos(ficha_id):
    """Aplica uma ordem escolhida manualmente (arrastar/setas no front) e
    recalcula distância/tempo PARA ESSA ORDEM — sem rodar o otimizador de
    novo, que ia simplesmente desfazer o que o técnico acabou de ajustar."""
    data = request.get_json(silent=True) or {}
    ordem_ids = data.get("ordem_ids")

    if not isinstance(ordem_ids, list) or not ordem_ids:
        return jsonify({"erro": "ordem_ids deve ser uma lista de IDs de serviço"}), 400

    with db_conn(commit=True) as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(conn, "SELECT id FROM servicos WHERE ficha_id = ?", (ficha_id,))
        ids_da_ficha = {s["id"] for s in servicos}

        try:
            ordem_ids = [int(i) for i in ordem_ids]
        except (TypeError, ValueError):
            return jsonify({"erro": "ordem_ids deve conter apenas números"}), 400

        if set(ordem_ids) != ids_da_ficha:
            return jsonify({
                "erro": "A lista enviada não corresponde exatamente aos "
                        "pontos desta ficha (algum foi adicionado, "
                        "removido ou duplicado nesse meio tempo)."
            }), 409

        for posicao, servico_id in enumerate(ordem_ids, start=1):
            execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?",
                    (posicao, servico_id))

        resultado = recalcular_distancia_ordem_fixa(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Ordem atualizada manualmente", **resultado})


def recalcular_rota(conn, ficha_id, ficha) -> dict:
    servicos = fetch_all(
        conn, "SELECT id, lat, lng FROM servicos WHERE ficha_id = ?", (ficha_id,)
    )

    validos = [s for s in servicos
               if s.get("lat") is not None and s.get("lng") is not None]

    tem_partida = bool(ficha) and ficha.get("ponto_partida_lat") is not None

    if not validos or not tem_partida:
        execute(conn, """
            UPDATE fichas SET distancia_total = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (ficha_id,))
        return {
            "distancia_total": 0.0,
            "retorno_km":      0.0,
            "total_servicos":  len(servicos),
            "tempo_minutos":   len(servicos) * MINUTOS_PARADA,
            "sem_partida":     not tem_partida,
            "sem_coordenada":  len(servicos) - len(validos),
        }

    partida = {"lat": ficha["ponto_partida_lat"], "lng": ficha["ponto_partida_lng"]}
    pontos = [{"lat": s["lat"], "lng": s["lng"], "id": s["id"]} for s in validos]

    r = otimizar_rota(partida, pontos)

    for posicao, idx in enumerate(r["ordem"], start=1):
        execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?",
                (posicao, pontos[idx]["id"]))

    for offset, s in enumerate(
        [s for s in servicos if s.get("lat") is None], start=len(pontos) + 1
    ):
        execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?", (offset, s["id"]))

    execute(conn, """
        UPDATE fichas SET distancia_total = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (r["distancia_km"], ficha_id))

    return {
        "distancia_total": r["distancia_km"],
        "retorno_km":      r["retorno_km"],
        "total_km":        r["total_km"],
        "total_servicos":  len(servicos),
        "tempo_minutos":   r["tempo_minutos"],
        "ganho_2opt_km":   r["ganho_2opt_km"],
        "sem_coordenada":  len(servicos) - len(validos),
    }


def recalcular_distancia_ordem_fixa(conn, ficha_id, ficha) -> dict:
    servicos = fetch_all(
        conn,
        "SELECT id, lat, lng FROM servicos WHERE ficha_id = ? ORDER BY ordem, id",
        (ficha_id,),
    )
    validos = [s for s in servicos
               if s.get("lat") is not None and s.get("lng") is not None]
    tem_partida = bool(ficha) and ficha.get("ponto_partida_lat") is not None

    if not validos or not tem_partida:
        execute(conn, """
            UPDATE fichas SET distancia_total = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (ficha_id,))
        return {
            "distancia_total": 0.0,
            "total_servicos":  len(servicos),
            "tempo_minutos":   len(servicos) * MINUTOS_PARADA,
            "sem_partida":     not tem_partida,
            "sem_coordenada":  len(servicos) - len(validos),
        }

    partida = {"lat": ficha["ponto_partida_lat"], "lng": ficha["ponto_partida_lng"]}
    pontos = [{"lat": s["lat"], "lng": s["lng"]} for s in validos]

    r = calcular_rota_fixa(partida, pontos)

    execute(conn, """
        UPDATE fichas SET distancia_total = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (r["distancia_km"], ficha_id))

    return {
        "distancia_total": r["distancia_km"],
        "retorno_km":      r["retorno_km"],
        "total_km":        r["total_km"],
        "total_servicos":  len(servicos),
        "tempo_minutos":   r["tempo_minutos"],
        "sem_coordenada":  len(servicos) - len(validos),
    }