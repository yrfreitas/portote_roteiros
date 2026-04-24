from flask import Blueprint, request, jsonify
from database import get_db

tecnicos_bp = Blueprint("tecnicos", __name__)

CORES_PADRAO = [
    "#1a6fd4", "#e05c2a", "#2aa05c", "#9b3db8",
    "#d4a01a", "#2aaab8", "#d41a5c", "#5c7ad4"
]

@tecnicos_bp.route("/tecnicos", methods=["GET"])
def listar_tecnicos():
    conn = get_db()
    tecnicos = conn.execute("""
        SELECT t.*, COUNT(f.id) as total_fichas
        FROM tecnicos t
        LEFT JOIN fichas f ON f.tecnico_id = t.id
        GROUP BY t.id
        ORDER BY t.nome
    """).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tecnicos])


@tecnicos_bp.route("/tecnicos", methods=["POST"])
def criar_tecnico():
    try:
        # get_json(silent=True) evita que o Flask quebre se o cabeçalho estiver errado
        data = request.get_json(silent=True) or {}
        nome = data.get("nome", "").strip()

        if not nome:
            return jsonify({"erro": "Nome é obrigatório"}), 400

        conn = get_db()

        # Escolhe cor automática baseada na quantidade de técnicos
        total = conn.execute("SELECT COUNT(*) as c FROM tecnicos").fetchone()["c"]
        cor = data.get("cor", CORES_PADRAO[total % len(CORES_PADRAO)])

        cur = conn.execute(
            "INSERT INTO tecnicos (nome, cor) VALUES (?, ?)",
            (nome, cor)
        )
        tecnico_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Retorna 201 (Created) que é a boa prática para POST
        return jsonify({"id": tecnico_id, "nome": nome, "cor": cor}), 201

    except Exception as e:
        # Se QUALQUER coisa der errado, o front-end vai receber um JSON amigável
        return jsonify({"erro": f"Erro interno no servidor: {str(e)}"}), 500


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>", methods=["DELETE"])
def deletar_tecnico(tecnico_id):
    conn = get_db()
    conn.execute("DELETE FROM tecnicos WHERE id = ?", (tecnico_id,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Técnico removido"})


@tecnicos_bp.route("/verificar-cep", methods=["POST"])
def verificar_cep():
    data = request.json
    cep = data.get("cep", "").replace("-", "").strip()

    if not cep:
        return jsonify({"erro": "CEP é obrigatório"}), 400

    # Busca o CEP no cache
    conn = get_db()
    geo = conn.execute(
        "SELECT * FROM cache_geo WHERE cep = ?", (cep,)
    ).fetchone()

    if not geo:
        conn.close()
        from services.geo import geocode_cep
        geo_data = geocode_cep(cep)
        if not geo_data:
            return jsonify({"erro": "CEP não encontrado"}), 404
        conn = get_db()
        geo = conn.execute(
            "SELECT * FROM cache_geo WHERE cep = ?", (cep,)
        ).fetchone()

    if not geo:
        conn.close()
        return jsonify({"erro": "CEP não encontrado"}), 404

    lat_alvo = geo["lat"]
    lng_alvo = geo["lon"] if "lon" in geo.keys() else geo["lng"]
    endereco_alvo = geo["endereco"]

    # Busca todos os serviços com coordenadas
    servicos = conn.execute("""
        SELECT s.*, f.dia_semana, f.tecnico_id, f.id as ficha_id,
               t.nome as tecnico_nome, t.cor as tecnico_cor
        FROM servicos s
        JOIN fichas f ON f.id = s.ficha_id
        JOIN tecnicos t ON t.id = f.tecnico_id
        WHERE s.lat IS NOT NULL
    """).fetchall()
    conn.close()

    if not servicos:
        return jsonify({
            "cep": cep,
            "endereco": endereco_alvo,
            "sugestoes": [],
            "mensagem": "Nenhuma rota cadastrada ainda."
        })

    # Calcula distância para cada serviço e agrupa por ficha
    from services.otimizador import haversine

    fichas_dist = {}
    for s in servicos:
        dist = haversine(lat_alvo, lng_alvo, s["lat"], s["lng"])
        fid = s["ficha_id"]
        if fid not in fichas_dist:
            fichas_dist[fid] = {
                "ficha_id": fid,
                "dia_semana": s["dia_semana"],
                "tecnico_id": s["tecnico_id"],
                "tecnico_nome": s["tecnico_nome"],
                "tecnico_cor": s["tecnico_cor"],
                "dist_minima": dist,
                "total_pontos": 0
            }
        else:
            if dist < fichas_dist[fid]["dist_minima"]:
                fichas_dist[fid]["dist_minima"] = dist
        fichas_dist[fid]["total_pontos"] += 1

    # Ordena por distância mínima e pega top 3
    sugestoes = sorted(fichas_dist.values(), key=lambda x: x["dist_minima"])[:3]

    for s in sugestoes:
        s["dist_minima"] = round(s["dist_minima"], 1)

    return jsonify({
        "cep": cep,
        "endereco": endereco_alvo,
        "sugestoes": sugestoes
    })