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
    return [dict(r) for r in rows]


def _fetchone(cur):
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def zona_sp(cep_num):
    n = int(cep_num[:5])
    if   1000  <= n <= 9999:   return "centro"
    elif 10000 <= n <= 19999:  return "centro"
    elif 20000 <= n <= 23999:  return "oeste"
    elif 24000 <= n <= 24999:  return "norte"
    elif 25000 <= n <= 29999:  return "norte"
    elif 30000 <= n <= 37999:  return "norte"
    elif 38000 <= n <= 38999:  return "leste"
    elif 39000 <= n <= 39999:  return "leste"
    elif 40000 <= n <= 44999:  return "sul"
    elif 45000 <= n <= 45999:  return "sul"
    elif 46000 <= n <= 47999:  return "oeste"
    elif 48000 <= n <= 49999:  return "leste"
    elif 50000 <= n <= 52999:  return "leste"
    elif 53000 <= n <= 54999:  return "norte"
    elif 55000 <= n <= 55999:  return "norte"
    elif 56000 <= n <= 57999:  return "oeste"
    elif 58000 <= n <= 58999:  return "norte"
    elif 59000 <= n <= 59999:  return "norte"
    elif 60000 <= n <= 60999:  return "leste"
    elif 61000 <= n <= 61999:  return "leste"
    elif 62000 <= n <= 62999:  return "norte"
    elif 63000 <= n <= 63999:  return "leste"
    elif 64000 <= n <= 64999:  return "leste"
    elif 65000 <= n <= 65999:  return "sul"
    elif 66000 <= n <= 67999:  return "leste"
    elif 68000 <= n <= 68999:  return "sul"
    elif 69000 <= n <= 69999:  return "sul"
    elif 70000 <= n <= 72999:  return "sul"
    elif 73000 <= n <= 73999:  return "sul"
    elif 74000 <= n <= 74999:  return "oeste"
    elif 75000 <= n <= 75999:  return "oeste"
    elif 76000 <= n <= 76999:  return "oeste"
    elif 77000 <= n <= 77999:  return "norte"
    elif 78000 <= n <= 79999:  return "sul"
    elif 80000 <= n <= 82999:  return "sul"
    elif 83000 <= n <= 83999:  return "leste"
    elif 84000 <= n <= 84999:  return "leste"
    elif 85000 <= n <= 87999:  return "sul"
    elif 88000 <= n <= 88999:  return "sul"
    elif 89000 <= n <= 89999:  return "norte"
    else: return "outros"


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

    # ── 1. Geocodifica o CEP alvo ──────────────────────────────────
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM cache_geo WHERE cep = {PH}", (cep,))
    geo = _fetchone(cur)
    cur.close()
    conn.close()

    if not geo:
        from services.geo import geocode_cep
        geo_data = geocode_cep(cep)
        if not geo_data:
            return jsonify({"erro": "CEP não encontrado"}), 404
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM cache_geo WHERE cep = {PH}", (cep,))
        geo = _fetchone(cur)
        cur.close()
        conn.close()

    if not geo:
        return jsonify({"erro": "CEP não encontrado"}), 404

    lat_alvo      = geo["lat"]
    lng_alvo      = geo["lng"]
    endereco_alvo = geo["endereco"]
    zona_alvo     = zona_sp(cep)

    # ── 2. Busca todos os serviços cadastrados ────────────────────
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.lat, s.lng, s.cep as s_cep,
               f.dia_semana, f.tecnico_id, f.id as ficha_id,
               t.nome as tecnico_nome, t.cor as tecnico_cor
        FROM servicos s
        JOIN fichas f ON f.id = s.ficha_id
        JOIN tecnicos t ON t.id = f.tecnico_id
        WHERE s.lat IS NOT NULL AND s.lng IS NOT NULL
    """)
    servicos = _fetchall(cur)
    cur.close()
    conn.close()

    if not servicos:
        return jsonify({
            "cep":      cep,
            "endereco": endereco_alvo,
            "zona":     zona_alvo,
            "sugestoes": [],
            "mensagem": "Nenhuma rota cadastrada ainda."
        })

    from services.otimizador import haversine

    # ── 3. Pontua cada ficha ──────────────────────────────────────
    fichas = {}
    for s in servicos:
        dist   = haversine(lat_alvo, lng_alvo, s["lat"], s["lng"])
        zona_s = zona_sp(s["s_cep"]) if s.get("s_cep") else "outros"
        fid    = s["ficha_id"]

        if fid not in fichas:
            fichas[fid] = {
                "ficha_id":          fid,
                "dia_semana":        s["dia_semana"],
                "tecnico_id":        s["tecnico_id"],
                "tecnico_nome":      s["tecnico_nome"],
                "tecnico_cor":       s["tecnico_cor"],
                "dist_minima":       dist,
                "total_pontos":      0,
                "pontos_mesma_zona": 0,
            }
        else:
            if dist < fichas[fid]["dist_minima"]:
                fichas[fid]["dist_minima"] = dist

        fichas[fid]["total_pontos"] += 1
        if zona_s == zona_alvo:
            fichas[fid]["pontos_mesma_zona"] += 1

    # ── 4. Score final ────────────────────────────────────────────
    def score(f):
        zona_bonus   = 100 if f["pontos_mesma_zona"] > 0 else 0
        dist_score   = max(0, 50 - f["dist_minima"])
        regiao_bonus = f["pontos_mesma_zona"] * 5
        return zona_bonus + dist_score + regiao_bonus

    lista = sorted(fichas.values(), key=score, reverse=True)
    sugestoes = lista[:3]

    for s in sugestoes:
        s["dist_minima"]       = round(s["dist_minima"], 1)
        s["mesma_zona"]        = s["pontos_mesma_zona"] > 0
        s["zona_alvo"]         = zona_alvo
        s["pontos_mesma_zona"] = s["pontos_mesma_zona"]

    return jsonify({
        "cep":      cep,
        "endereco": endereco_alvo,
        "zona":     zona_alvo,
        "sugestoes": sugestoes
    })