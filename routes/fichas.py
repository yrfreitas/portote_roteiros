from flask import Blueprint, request, jsonify
from database import get_db
from services.geo import geocode_cep
from services.otimizador import otimizar_rota

fichas_bp = Blueprint("fichas", __name__)


@fichas_bp.route("/fichas", methods=["GET"])
def listar_fichas():
    conn = get_db()
    fichas = conn.execute("""
        SELECT f.*, COUNT(s.id) as total_servicos
        FROM fichas f
        LEFT JOIN servicos s ON s.ficha_id = f.id
        GROUP BY f.id
        ORDER BY f.updated_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(f) for f in fichas])


@fichas_bp.route("/fichas", methods=["POST"])
def criar_ficha():
    data = request.json
    dia = data.get("dia_semana")

    if not dia:
        return jsonify({"erro": "dia_semana é obrigatório"}), 400

    partida = data.get("ponto_partida", "")
    partida_cep = data.get("ponto_partida_cep", "")
    lat_p, lng_p = None, None

    if partida_cep:
        geo = geocode_cep(partida_cep)
        if geo:
            lat_p = geo["lat"]
            lng_p = geo["lng"]
            if not partida:
                partida = geo["endereco"]

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO fichas
           (dia_semana, data_referencia, ponto_partida, ponto_partida_cep, ponto_partida_lat, ponto_partida_lng)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (dia, data.get("data_referencia", ""), partida, partida_cep, lat_p, lng_p)
    )
    ficha_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"id": ficha_id, "mensagem": "Ficha criada com sucesso"})


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["GET"])
def obter_ficha(ficha_id):
    conn = get_db()
    ficha = conn.execute(
        "SELECT * FROM fichas WHERE id = ?", (ficha_id,)
    ).fetchone()

    if not ficha:
        conn.close()
        return jsonify({"erro": "Ficha não encontrada"}), 404

    servicos = conn.execute(
        "SELECT * FROM servicos WHERE ficha_id = ? ORDER BY ordem",
        (ficha_id,)
    ).fetchall()
    conn.close()

    return jsonify({
        "ficha": dict(ficha),
        "servicos": [dict(s) for s in servicos]
    })


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["DELETE"])
def deletar_ficha(ficha_id):
    conn = get_db()
    conn.execute("DELETE FROM fichas WHERE id = ?", (ficha_id,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Ficha removida"})


@fichas_bp.route("/fichas/<int:ficha_id>/otimizar", methods=["POST"])
def otimizar_ficha(ficha_id):
    conn = get_db()
    ficha = conn.execute(
        "SELECT * FROM fichas WHERE id = ?", (ficha_id,)
    ).fetchone()

    if not ficha:
        conn.close()
        return jsonify({"erro": "Ficha não encontrada"}), 404

    resultado = recalcular_rota(conn, ficha_id, ficha)
    conn.commit()
    conn.close()
    return jsonify(resultado)


def recalcular_rota(conn, ficha_id, ficha):
    """Recalcula e salva a ordem otimizada dos serviços"""
    servicos = conn.execute(
        "SELECT * FROM servicos WHERE ficha_id = ?", (ficha_id,)
    ).fetchall()

    if not servicos or ficha["ponto_partida_lat"] is None:
        return {"distancia_total": 0}

    partida = {
        "lat": ficha["ponto_partida_lat"],
        "lng": ficha["ponto_partida_lng"]
    }
    pontos = [
        {"lat": s["lat"], "lng": s["lng"], "id": s["id"]}
        for s in servicos
    ]

    ordem, dist_total = otimizar_rota(partida, pontos)

    for posicao, idx in enumerate(ordem):
        conn.execute(
            "UPDATE servicos SET ordem = ? WHERE id = ?",
            (posicao + 1, pontos[idx]["id"])
        )

    conn.execute(
        "UPDATE fichas SET distancia_total = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (dist_total, ficha_id)
    )

    return {"distancia_total": dist_total, "total_servicos": len(servicos)}