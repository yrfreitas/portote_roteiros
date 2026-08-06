from flask import Blueprint, jsonify, request

from database import db_conn, execute, fetch_all, fetch_one, insert_returning_id
from services.geo import geocode_cep
from services.otimizador import haversine

tecnicos_bp = Blueprint("tecnicos", __name__)

CORES_PADRAO = [
    "#1a6fd4", "#e05c2a", "#2aa05c", "#9b3db8",
    "#d4a01a", "#2aaab8", "#d41a5c", "#5c7ad4",
]

SCORE_MINIMO_BOM = 30
CAPACIDADE_IDEAL = 8


def zona_sp(cep) -> str:
    digitos = "".join(c for c in str(cep or "") if c.isdigit())
    if len(digitos) < 5:
        return "outros"

    n = int(digitos[:5])

    if   1000 <= n <= 1999: return "centro"
    elif 2000 <= n <= 2999: return "norte"
    elif 3000 <= n <= 3999: return "leste"
    elif 4000 <= n <= 4999: return "sul"
    elif 5000 <= n <= 5999: return "oeste"
    elif 6000 <= n <= 6999: return "oeste"
    elif 7000 <= n <= 7999: return "norte"
    elif 8000 <= n <= 8999: return "leste"
    elif 9000 <= n <= 9999: return "sul"
    return "outros"


@tecnicos_bp.route("/tecnicos", methods=["GET"])
def listar_tecnicos():
    with db_conn() as conn:
        tecnicos = fetch_all(conn, """
            SELECT t.*, COUNT(f.id) AS total_fichas
            FROM tecnicos t
            LEFT JOIN fichas f ON f.tecnico_id = t.id
            GROUP BY t.id
            ORDER BY t.nome
        """)
    return jsonify(tecnicos)


@tecnicos_bp.route("/tecnicos", methods=["POST"])
def criar_tecnico():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()

    if not nome:
        return jsonify({"erro": "Nome é obrigatório"}), 400
    if len(nome) > 80:
        return jsonify({"erro": "Nome muito longo (máx. 80 caracteres)"}), 400

    with db_conn(commit=True) as conn:
        existente = fetch_one(
            conn, "SELECT id FROM tecnicos WHERE LOWER(nome) = LOWER(?)", (nome,)
        )
        if existente:
            return jsonify({"erro": f'Já existe um técnico chamado "{nome}"'}), 409

        total = fetch_one(conn, "SELECT COUNT(*) AS total FROM tecnicos")["total"]
        cor = (data.get("cor") or CORES_PADRAO[total % len(CORES_PADRAO)])

        tecnico_id = insert_returning_id(
            conn, "INSERT INTO tecnicos (nome, cor) VALUES (?, ?)", (nome, cor)
        )

    return jsonify({"id": tecnico_id, "nome": nome, "cor": cor}), 201


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>", methods=["DELETE"])
def deletar_tecnico(tecnico_id):
    with db_conn(commit=True) as conn:
        execute(conn, """
            DELETE FROM servicos
             WHERE ficha_id IN (SELECT id FROM fichas WHERE tecnico_id = ?)
        """, (tecnico_id,))
        execute(conn, "DELETE FROM fichas WHERE tecnico_id = ?", (tecnico_id,))
        apagados = execute(conn, "DELETE FROM tecnicos WHERE id = ?", (tecnico_id,))

    if not apagados:
        return jsonify({"erro": "Técnico não encontrado"}), 404
    return jsonify({"mensagem": "Técnico removido"})


@tecnicos_bp.route("/verificar-cep", methods=["POST"])
def verificar_cep():
    data = request.get_json(silent=True) or {}
    cep = "".join(c for c in (data.get("cep") or "") if c.isdigit())

    if len(cep) != 8:
        return jsonify({"erro": "Informe um CEP válido com 8 dígitos"}), 400

    geo = geocode_cep(cep)
    if not geo:
        return jsonify({"erro": "CEP não encontrado"}), 404

    lat_alvo, lng_alvo = geo.lat, geo.lng
    zona_alvo = zona_sp(cep)

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT f.id AS ficha_id, f.dia_semana, f.data_referencia,
                   f.tecnico_id, f.ponto_partida_lat, f.ponto_partida_lng,
                   f.ponto_partida_cep,
                   t.nome AS tecnico_nome, t.cor AS tecnico_cor,
                   s.lat AS s_lat, s.lng AS s_lng, s.cep AS s_cep
            FROM fichas f
            JOIN tecnicos t ON t.id = f.tecnico_id
            LEFT JOIN servicos s
                   ON s.ficha_id = f.id
                  AND s.lat IS NOT NULL AND s.lng IS NOT NULL
        """)
        lista_tecnicos = fetch_all(
            conn, "SELECT id, nome, cor FROM tecnicos ORDER BY nome"
        )

    base = {
        "cep":       cep,
        "endereco":  geo.endereco,
        "zona":      zona_alvo,
        "preciso":   geo.preciso,
        "tecnicos":  lista_tecnicos,
    }

    if not linhas:
        return jsonify({
            **base, "sugestoes": [], "tem_boa_opcao": False,
            "mensagem": "Nenhuma rota cadastrada ainda.",
        })

    fichas = {}
    for l in linhas:
        fid = l["ficha_id"]
        if fid not in fichas:
            fichas[fid] = {
                "ficha_id":          fid,
                "dia_semana":        l["dia_semana"],
                "data_referencia":   l.get("data_referencia") or "",
                "tecnico_id":        l["tecnico_id"],
                "tecnico_nome":      l["tecnico_nome"],
                "tecnico_cor":       l["tecnico_cor"] or CORES_PADRAO[0],
                "dist_minima":       None,
                "total_pontos":      0,
                "pontos_mesma_zona": 0,
                "vazia":             True,
                "_base_lat":         l.get("ponto_partida_lat"),
                "_base_lng":         l.get("ponto_partida_lng"),
                "_base_cep":         l.get("ponto_partida_cep"),
            }

        if l.get("s_lat") is None:
            continue

        f = fichas[fid]
        f["vazia"] = False
        f["total_pontos"] += 1

        dist = haversine(lat_alvo, lng_alvo, l["s_lat"], l["s_lng"])
        if f["dist_minima"] is None or dist < f["dist_minima"]:
            f["dist_minima"] = dist

        if zona_sp(l.get("s_cep")) == zona_alvo:
            f["pontos_mesma_zona"] += 1

    for f in fichas.values():
        if not f["vazia"]:
            continue
        if f["_base_lat"] is not None and f["_base_lng"] is not None:
            f["dist_minima"] = haversine(
                lat_alvo, lng_alvo, f["_base_lat"], f["_base_lng"]
            )
            f["mesma_zona_base"] = zona_sp(f["_base_cep"]) == zona_alvo
        else:
            f["dist_minima"] = None
            f["mesma_zona_base"] = False

    def score(f):
        if f["dist_minima"] is None:
            return 0.0

        dist_score = max(0, 50 - f["dist_minima"])

        if f["vazia"]:
            zona_bonus = 60 if f.get("mesma_zona_base") else 0
            return zona_bonus + dist_score + 20

        total = f["total_pontos"]
        pct_mesma_zona = f["pontos_mesma_zona"] / total if total else 0
        zona_bonus   = 100 * pct_mesma_zona
        regiao_bonus = min(30, f["pontos_mesma_zona"] * 3)
        penal_lotacao = max(0, total - CAPACIDADE_IDEAL) * 15

        return zona_bonus + dist_score + regiao_bonus - penal_lotacao

    ordenadas = sorted(fichas.values(), key=score, reverse=True)
    sugestoes = []

    for f in ordenadas[:10]:
        sugestoes.append({
            "ficha_id":          f["ficha_id"],
            "dia_semana":        f["dia_semana"],
            "data_referencia":   f["data_referencia"],
            "tecnico_id":        f["tecnico_id"],
            "tecnico_nome":      f["tecnico_nome"],
            "tecnico_cor":       f["tecnico_cor"],
            "total_pontos":      f["total_pontos"],
            "pontos_mesma_zona": f["pontos_mesma_zona"],
            "dist_minima":       round(f["dist_minima"], 1) if f["dist_minima"] is not None else None,
            "mesma_zona":        f["pontos_mesma_zona"] > 0 or f.get("mesma_zona_base", False),
            "zona_alvo":         zona_alvo,
            "vazia":             f["vazia"],
            "score":             max(0, round(score(f), 1)),
        })

    tem_boa_opcao = bool(sugestoes) and sugestoes[0]["score"] >= SCORE_MINIMO_BOM

    return jsonify({**base, "sugestoes": sugestoes, "tem_boa_opcao": tem_boa_opcao})