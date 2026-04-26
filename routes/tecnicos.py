from flask import Blueprint, request, jsonify
from database import get_db
import os

tecnicos_bp = Blueprint("tecnicos", __name__)

CORES_PADRAO = [
    "#1a6fd4", "#e05c2a", "#2aa05c", "#9b3db8",
    "#d4a01a", "#2aaab8", "#d41a5c", "#5c7ad4"
]

PG = bool(os.environ.get("DATABASE_URL"))
PH = "%s" if PG else "?"


def _fetchall(cur):
    rows = cur.fetchall()
    if PG:
        return [dict(r) for r in rows]
    return [dict(r) for r in rows]


def _fetchone(cur):
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


@tecnicos_bp.route("/tecnicos", methods=["GET"])
def listar_tecnicos():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, COUNT(f.id) as total_fichas
        FROM tecnicos t
        LEFT JOIN fichas f ON f.tecnico_id = t.id
        GROUP BY t.id
        ORDER BY t.nome
    """)
    tecnicos = _fetchall(cur)
    cur.close()
    conn.close()
    return jsonify(tecnicos)


@tecnicos_bp.route("/tecnicos", methods=["POST"])
def criar_tecnico():
    data = request.json
    nome = data.get("nome", "").strip()

    if not nome:
        return jsonify({"erro": "Nome é obrigatório"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM tecnicos")
    row = cur.fetchone()
    total = row["total"] if PG else row[0]
    cor = data.get("cor", CORES_PADRAO[total % len(CORES_PADRAO)])

    if PG:
        cur.execute(
            "INSERT INTO tecnicos (nome, cor) VALUES (%s, %s) RETURNING id",
            (nome, cor)
        )
        tecnico_id = cur.fetchone()["id"]
    else:
        cur.execute("INSERT INTO tecnicos (nome, cor) VALUES (?, ?)", (nome, cor))
        tecnico_id = cur.lastrowid

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": tecnico_id, "nome": nome, "cor": cor})


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>", methods=["DELETE"])
def deletar_tecnico(tecnico_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM tecnicos WHERE id = {PH}", (tecnico_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"mensagem": "Técnico removido"})


@tecnicos_bp.route("/verificar-cep", methods=["POST"])
def verificar_cep():
    data = request.json
    cep = data.get("cep", "").replace("-", "").strip()

    if not cep:
        return jsonify({"erro": "CEP é obrigatório"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM cache_geo WHERE cep = {PH}", (cep,))
    geo = _fetchone(cur)

    if not geo:
        cur.close()
        conn.close()
        from services.geo import geocode_cep
        geo_data = geocode_cep(cep)
        if not geo_data:
            return jsonify({"erro": "CEP não encontrado"}), 404
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM cache_geo WHERE cep = {PH}", (cep,))
        geo = _fetchone(cur)

    if not geo:
        cur.close()
        conn.close()
        return jsonify({"erro": "CEP não encontrado"}), 404

    lat_alvo = geo["lat"]
    lng_alvo = geo["lng"]
    endereco_alvo = geo["endereco"]

    cur.execute("""
        SELECT s.*, f.dia_semana, f.tecnico_id, f.id as ficha_id,
               t.nome as tecnico_nome, t.cor as tecnico_cor
        FROM servicos s
        JOIN fichas f ON f.id = s.ficha_id
        JOIN tecnicos t ON t.id = f.tecnico_id
        WHERE s.lat IS NOT NULL
    """)
    servicos = _fetchall(cur)
    cur.close()
    conn.close()

    if not servicos:
        return jsonify({
            "cep": cep,
            "endereco": endereco_alvo,
            "sugestoes": [],
            "mensagem": "Nenhuma rota cadastrada ainda."
        })

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

    sugestoes = sorted(fichas_dist.values(), key=lambda x: x["dist_minima"])[:3]
    for s in sugestoes:
        s["dist_minima"] = round(s["dist_minima"], 1)

    return jsonify({
        "cep": cep,
        "endereco": endereco_alvo,
        "sugestoes": sugestoes
    })