from flask import Blueprint, request, jsonify
from database import get_db
from services.geo import geocode_cep
from routes.fichas import recalcular_rota

servicos_bp = Blueprint("servicos", __name__)


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

    conn = get_db()
    ficha = conn.execute(
        "SELECT * FROM fichas WHERE id = ?", (ficha_id,)
    ).fetchone()

    if not ficha:
        conn.close()
        return jsonify({"erro": "Ficha não encontrada"}), 404

    conn.execute(
        """INSERT INTO servicos (ficha_id, cep, endereco_completo, lat, lng, cliente, descricao, numero)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ficha_id,
            cep,
            geo["endereco"],
            geo["lat"],
            geo["lng"],
            data.get("cliente", ""),
            data.get("descricao", ""),
            numero
        )
    )

    resultado = recalcular_rota(conn, ficha_id, ficha)
    conn.commit()
    conn.close()

    return jsonify({
        "mensagem": "Serviço adicionado e rota otimizada",
        "endereco": geo["endereco"],
        "numero": numero,
        "distancia_total": resultado["distancia_total"]
    })


@servicos_bp.route("/servicos/<int:servico_id>", methods=["DELETE"])
def remover_servico(servico_id):
    conn = get_db()
    servico = conn.execute(
        "SELECT * FROM servicos WHERE id = ?", (servico_id,)
    ).fetchone()

    if not servico:
        conn.close()
        return jsonify({"erro": "Serviço não encontrado"}), 404

    ficha_id = servico["ficha_id"]
    conn.execute("DELETE FROM servicos WHERE id = ?", (servico_id,))

    ficha = conn.execute(
        "SELECT * FROM fichas WHERE id = ?", (ficha_id,)
    ).fetchone()

    resultado = recalcular_rota(conn, ficha_id, ficha)
    conn.commit()
    conn.close()

    return jsonify({
        "mensagem": "Serviço removido e rota recalculada",
        "distancia_total": resultado["distancia_total"]
    })