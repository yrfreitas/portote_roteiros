import urllib.request
import urllib.error
import json
import math

from flask import Blueprint, request, jsonify
from database import get_db

cep_checker_bp = Blueprint("cep_checker", __name__)


def _buscar_viacep(cep: str) -> dict | None:
    """Consulta a API ViaCEP e retorna os dados ou None em caso de erro."""
    cep = cep.replace("-", "").strip()
    if len(cep) != 8 or not cep.isdigit():
        return None
    try:
        url = f"https://viacep.com.br/ws/{cep}/json/"
        req = urllib.request.Request(url, headers={"User-Agent": "Portotec/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("erro"):
                return None
            return data
    except Exception:
        return None


def _haversine(lat1, lng1, lat2, lng2) -> float:
    """Distância em km entre dois pontos geográficos."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _analisar_encaixe(bairro: str, cidade: str, uf: str, fichas_com_servicos: list) -> dict:
    """
    Verifica se o bairro/cidade do CEP aparece (ou é próximo) nos serviços
    já cadastrados nas fichas existentes.
    Retorna dict com status, ficha_sugerida e justificativa.
    """
    bairro_lower = (bairro or "").lower().strip()
    cidade_lower = (cidade or "").lower().strip()

    melhor_ficha = None
    melhor_score = 0
    melhor_motivo = ""

    for ficha in fichas_com_servicos:
        score = 0
        motivos = []

        enderecos = [
            (s.get("endereco_completo") or "").lower()
            for s in ficha.get("servicos", [])
        ]
        enderecos_str = " | ".join(enderecos)

        # Bairro exato encontrado nos endereços da ficha
        if bairro_lower and bairro_lower in enderecos_str:
            score += 3
            motivos.append(f"bairro '{bairro}' já presente na rota")

        # Cidade encontrada nos endereços
        if cidade_lower and cidade_lower in enderecos_str:
            score += 1
            motivos.append(f"mesma cidade '{cidade}'")

        # Ponto de partida da ficha é da mesma cidade/UF
        partida = (ficha.get("ponto_partida") or "").lower()
        if cidade_lower and cidade_lower in partida:
            score += 1
            motivos.append("partida na mesma cidade")

        if score > melhor_score:
            melhor_score = score
            melhor_ficha = ficha
            melhor_motivo = ", ".join(motivos) if motivos else "região próxima à rota"

    if melhor_score >= 3:
        status = "encaixa"
        justificativa = f"O bairro já consta na rota existente ({melhor_motivo})."
    elif melhor_score >= 1:
        status = "possivel"
        justificativa = f"A região é compatível com a rota ({melhor_motivo})."
    else:
        status = "nao_encaixa"
        justificativa = "Nenhuma ficha cobre esse bairro/região ainda."

    return {
        "status": status,
        "ficha_sugerida": melhor_ficha,
        "justificativa": justificativa,
        "score": melhor_score,
    }


@cep_checker_bp.route("/verificar-cep", methods=["POST"])
def verificar_cep():
    data = request.json or {}
    cep_raw = (data.get("cep") or "").replace("-", "").strip()

    if len(cep_raw) != 8 or not cep_raw.isdigit():
        return jsonify({"erro": "CEP inválido. Informe 8 dígitos."}), 400

    # 1. Geocodificação via ViaCEP
    info = _buscar_viacep(cep_raw)
    if not info:
        return jsonify({"erro": "CEP não encontrado na base dos Correios."}), 404

    # 2. Carrega fichas + serviços do banco
    conn = get_db()
    fichas = conn.execute("""
        SELECT f.id, f.dia_semana, f.data_referencia,
               f.ponto_partida, f.ponto_partida_lat, f.ponto_partida_lng,
               f.distancia_total
        FROM fichas f
        ORDER BY f.updated_at DESC
    """).fetchall()

    fichas_completas = []
    for ficha in fichas:
        f = dict(ficha)
        servicos = conn.execute(
            "SELECT endereco_completo, lat, lng, cep FROM servicos WHERE ficha_id = ?",
            (f["id"],)
        ).fetchall()
        f["servicos"] = [dict(s) for s in servicos]
        fichas_completas.append(f)
    conn.close()

    # 3. Análise de encaixe
    resultado = _analisar_encaixe(
        bairro=info.get("bairro", ""),
        cidade=info.get("localidade", ""),
        uf=info.get("uf", ""),
        fichas_com_servicos=fichas_completas,
    )

    ficha_sug = resultado["ficha_sugerida"]

    # Monta sugestão de texto
    sugestoes_texto = {
        "encaixa": (
            f"Adicione este CEP à ficha de {ficha_sug['dia_semana']} "
            f"— ela já passa por essa região."
            if ficha_sug else "Encaixa bem em uma das fichas existentes."
        ),
        "possivel": (
            f"Avalie incluir na ficha de {ficha_sug['dia_semana']} "
            f"({ficha_sug.get('distancia_total', 0):.1f} km atualmente)."
            if ficha_sug else "Pode ser encaixado com ajuste de rota."
        ),
        "nao_encaixa": (
            "Considere criar uma nova ficha para essa área ou rever as rotas existentes."
        ),
    }

    return jsonify({
        "cep": info.get("cep"),
        "logradouro": info.get("logradouro", ""),
        "bairro": info.get("bairro", ""),
        "cidade": info.get("localidade", ""),
        "uf": info.get("uf", ""),
        "status": resultado["status"],
        "ficha_sugerida": {
            "id": ficha_sug["id"],
            "dia_semana": ficha_sug["dia_semana"],
            "data_referencia": ficha_sug.get("data_referencia"),
            "distancia_total": ficha_sug.get("distancia_total", 0),
            "total_servicos": len(ficha_sug.get("servicos", [])),
        } if ficha_sug else None,
        "justificativa": resultado["justificativa"],
        "sugestao": sugestoes_texto[resultado["status"]],
    })