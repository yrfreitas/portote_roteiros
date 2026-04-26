from flask import Blueprint, request, jsonify
from database import get_db
from services.geo import geocode_cep
from routes.fichas import recalcular_rota, _fetchone
import os

servicos_bp = Blueprint("servicos", __name__)

PG = bool(os.environ.get("DATABASE_URL"))
PH = "%s" if PG else "?"


@servicos_bp.route("/fichas/<int:ficha_id>/servicos", methods=["POST"])
def adicionar_servico(ficha_id):
    data = request.json
    cep = data.get("cep", "").replace("-", "").strip()
    numero = data.get("numero", "").strip()

    if not cep:
        return jsonify({"erro": "CEP é obrigatório"}), 400

    geo = geocode_cep(cep)
    if not geo:
        return jsonify({"erro": f"CEP {cep} não encontrado. Verifique e tente novamente."}), 400

    lat = geo.lat if PG else geo["lat"]
    lng = geo.lng if PG else geo["lng"]
    endereco = geo.endereco if PG else geo["endereco"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM fichas WHERE id = {PH}", (ficha_id,))
    ficha = _fetchone(cur)

    if not ficha:
        cur.close()
        conn.close()
        return jsonify({"erro": "Ficha não encontrada"}), 404

    cur.execute(
        f"""INSERT INTO servicos (ficha_id, cep, endereco_completo, lat, lng, cliente, descricao, numero)
           VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})""",
        (ficha_id, cep, endereco, lat, lng,
         data.get("cliente", ""), data.get("descricao", ""), numero)
    )
    cur.close()

    resultado = recalcular_rota(conn, ficha_id, ficha)
    conn.commit()
    conn.close()

    return jsonify({
        "mensagem": "Serviço adicionado e rota otimizada",
        "endereco": endereco,
        "numero": numero,
        "distancia_total": resultado["distancia_total"]
    })


@servicos_bp.route("/servicos/<int:servico_id>", methods=["DELETE"])
def remover_servico(servico_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM servicos WHERE id = {PH}", (servico_id,))
    servico = _fetchone(cur)

    if not servico:
        cur.close()
        conn.close()
        return jsonify({"erro": "Serviço não encontrado"}), 404

    ficha_id = servico["ficha_id"]
    cur.execute(f"DELETE FROM servicos WHERE id = {PH}", (servico_id,))

    cur.execute(f"SELECT * FROM fichas WHERE id = {PH}", (ficha_id,))
    ficha = _fetchone(cur)
    cur.close()

    resultado = recalcular_rota(conn, ficha_id, ficha)
    conn.commit()
    conn.close()

    return jsonify({
        "mensagem": "Serviço removido e rota recalculada",
        "distancia_total": resultado["distancia_total"]
    })