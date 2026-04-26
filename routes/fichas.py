from flask import Blueprint, request, jsonify
from database import get_db
from services.geo import geocode_cep
from services.otimizador import otimizar_rota
import os

fichas_bp = Blueprint("fichas", __name__)

PG = bool(os.environ.get("DATABASE_URL"))
PH = "%s" if PG else "?"


def _fetchall(cur):
    rows = cur.fetchall()
    if PG:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


def _fetchone(cur):
    row = cur.fetchone()
    if row is None:
        return None
    if PG:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return dict(row)


@fichas_bp.route("/fichas", methods=["GET"])
def listar_fichas():
    conn = get_db()
    cur = conn.cursor()
    tecnico_id = request.args.get("tecnico_id")

    query = """
        SELECT f.*, COUNT(s.id) as total_servicos,
               t.nome as tecnico_nome, t.cor as tecnico_cor
        FROM fichas f
        LEFT JOIN servicos s ON s.ficha_id = f.id
        LEFT JOIN tecnicos t ON t.id = f.tecnico_id
    """
    params = []
    if tecnico_id:
        query += f" WHERE f.tecnico_id = {PH}"
        params.append(tecnico_id)

    query += " GROUP BY f.id ORDER BY f.updated_at DESC"

    cur.execute(query, params)
    fichas = _fetchall(cur)
    cur.close()
    conn.close()
    return jsonify(fichas)


@fichas_bp.route("/fichas", methods=["POST"])
def criar_ficha():
    data = request.json
    dia = data.get("dia_semana")
    tecnico_id = data.get("tecnico_id")

    if not dia:
        return jsonify({"erro": "dia_semana é obrigatório"}), 400
    if not tecnico_id:
        return jsonify({"erro": "tecnico_id é obrigatório"}), 400

    partida = data.get("ponto_partida", "")
    partida_cep = data.get("ponto_partida_cep", "")
    lat_p, lng_p = None, None

    if partida_cep:
        geo = geocode_cep(partida_cep)
        if geo:
            lat_p = geo.lat if PG else geo["lat"]
            lng_p = geo.lng if PG else geo["lng"]
            if not partida:
                partida = geo.endereco if PG else geo["endereco"]

    conn = get_db()
    cur = conn.cursor()

    if PG:
        cur.execute(
            """INSERT INTO fichas
               (tecnico_id, dia_semana, data_referencia, ponto_partida,
                ponto_partida_cep, ponto_partida_lat, ponto_partida_lng)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (tecnico_id, dia, data.get("data_referencia", ""),
             partida, partida_cep, lat_p, lng_p)
        )
        ficha_id = cur.fetchone()[0]
    else:
        cur.execute(
            """INSERT INTO fichas
               (tecnico_id, dia_semana, data_referencia, ponto_partida,
                ponto_partida_cep, ponto_partida_lat, ponto_partida_lng)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tecnico_id, dia, data.get("data_referencia", ""),
             partida, partida_cep, lat_p, lng_p)
        )
        ficha_id = cur.lastrowid

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": ficha_id, "mensagem": "Ficha criada com sucesso"})


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["GET"])
def obter_ficha(ficha_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM fichas WHERE id = {PH}", (ficha_id,))
    ficha = _fetchone(cur)

    if not ficha:
        cur.close()
        conn.close()
        return jsonify({"erro": "Ficha não encontrada"}), 404

    cur.execute(f"SELECT * FROM servicos WHERE ficha_id = {PH} ORDER BY ordem", (ficha_id,))
    servicos = _fetchall(cur)
    cur.close()
    conn.close()

    return jsonify({"ficha": ficha, "servicos": servicos})


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["DELETE"])
def deletar_ficha(ficha_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM fichas WHERE id = {PH}", (ficha_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"mensagem": "Ficha removida"})


@fichas_bp.route("/fichas/<int:ficha_id>/otimizar", methods=["POST"])
def otimizar_ficha(ficha_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM fichas WHERE id = {PH}", (ficha_id,))
    ficha = _fetchone(cur)
    cur.close()

    if not ficha:
        conn.close()
        return jsonify({"erro": "Ficha não encontrada"}), 404

    resultado = recalcular_rota(conn, ficha_id, ficha)
    conn.commit()
    conn.close()
    return jsonify(resultado)


def recalcular_rota(conn, ficha_id, ficha):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM servicos WHERE ficha_id = {PH}", (ficha_id,))
    servicos = _fetchall(cur)
    cur.close()

    if not servicos or ficha["ponto_partida_lat"] is None:
        return {"distancia_total": 0}

    partida = {"lat": ficha["ponto_partida_lat"], "lng": ficha["ponto_partida_lng"]}
    pontos = [{"lat": s["lat"], "lng": s["lng"], "id": s["id"]} for s in servicos]

    ordem, dist_total = otimizar_rota(partida, pontos)

    cur = conn.cursor()
    for posicao, idx in enumerate(ordem):
        cur.execute(
            f"UPDATE servicos SET ordem = {PH} WHERE id = {PH}",
            (posicao + 1, pontos[idx]["id"])
        )
    cur.execute(
        f"UPDATE fichas SET distancia_total = {PH}, updated_at = CURRENT_TIMESTAMP WHERE id = {PH}",
        (dist_total, ficha_id)
    )
    cur.close()

    return {"distancia_total": dist_total, "total_servicos": len(servicos)}