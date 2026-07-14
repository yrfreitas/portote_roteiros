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

# Score mínimo para considerar uma sugestão um "bom encaixe".
# Abaixo disso, o front sugere criar um novo dia.
SCORE_MINIMO_BOM = 30

# Nº de paradas que uma rota "comporta bem" num dia antes de começar a penalizar
CAPACIDADE_IDEAL = 8


def _fetchall(cur):
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def _fetchone(cur):
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def zona_sp(cep_num):
    """
    Zonas da cidade de São Paulo com base no prefixo real do CEP (5 primeiros dígitos).
    Cobre a capital (01000-09999). CEPs fora desse intervalo (interior/outros estados)
    caem em "outros".
    """
    n = int(cep_num[:5])
    if   1000  <= n <= 1999:   return "centro"
    elif 2000  <= n <= 2999:   return "norte"
    elif 7000  <= n <= 7999:   return "norte"   # Guarulhos (extensão zona norte)
    elif 3000  <= n <= 3999:   return "leste"
    elif 8000  <= n <= 8499:   return "leste"   # Itaquera / São Miguel etc.
    elif 4000  <= n <= 4999:   return "sul"
    elif 9000  <= n <= 9999:   return "sul"     # ABC (extensão zona sul)
    elif 5000  <= n <= 5999:   return "oeste"
    elif 6000  <= n <= 6999:   return "oeste"   # Osasco (extensão zona oeste)
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

    # Lista de técnicos para sugestão de "criar novo dia"
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, cor FROM tecnicos ORDER BY nome")
    lista_tecnicos = _fetchall(cur)
    cur.close()
    conn.close()

    if not servicos:
        return jsonify({
            "cep":          cep,
            "endereco":     endereco_alvo,
            "zona":         zona_alvo,
            "sugestoes":    [],
            "tem_boa_opcao": False,
            "tecnicos":     lista_tecnicos,
            "mensagem":     "Nenhuma rota cadastrada ainda."
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
        total = f["total_pontos"]
        pct_mesma_zona = f["pontos_mesma_zona"] / total if total else 0

        zona_bonus    = 100 * pct_mesma_zona        # proporcional, não all-or-nothing
        dist_score    = max(0, 50 - f["dist_minima"])
        regiao_bonus  = f["pontos_mesma_zona"] * 3
        excesso       = max(0, total - CAPACIDADE_IDEAL)
        penal_lotacao = excesso * 15                # cada ponto acima do ideal derruba o score

        return zona_bonus + dist_score + regiao_bonus - penal_lotacao

    lista = sorted(fichas.values(), key=score, reverse=True)
    sugestoes = lista[:10]

    for s in sugestoes:
        s["score"]             = max(0, round(score(s), 1))   # nunca mostra score negativo
        s["dist_minima"]       = round(s["dist_minima"], 1)
        s["mesma_zona"]        = s["pontos_mesma_zona"] > 0
        s["zona_alvo"]         = zona_alvo
        s["pontos_mesma_zona"] = s["pontos_mesma_zona"]

    # Considera "boa opção" se a melhor sugestão atingir o score mínimo
    tem_boa_opcao = len(sugestoes) > 0 and sugestoes[0]["score"] >= SCORE_MINIMO_BOM

    return jsonify({
        "cep":           cep,
        "endereco":      endereco_alvo,
        "zona":          zona_alvo,
        "sugestoes":     sugestoes,
        "tem_boa_opcao": tem_boa_opcao,
        "tecnicos":      lista_tecnicos
    })