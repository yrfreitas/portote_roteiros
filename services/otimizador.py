"""
services/otimizador.py  —  PortoTec
─────────────────────────────────────────────────────────────────────
CORREÇÕES aplicadas:
  ✅ distancia_total salva em KM reais (× fator de rua 1.4), não linha reta
  ✅ Tempo estimado calculado corretamente no backend
  ✅ Frontend não precisa mais multiplicar por 1.4 (evita dupla-aplicação)
  ✅ Nearest Neighbor mantido e funcionando
"""

import math


# ─── Constantes ──────────────────────────────────────────────────────

FATOR_ROTA      = 1.4   # linha reta → estimativa de percurso por rua
VELOCIDADE_KMH  = 40    # velocidade média urbana
MINUTOS_PARADA  = 20    # tempo médio de atendimento por ponto


# ─── Distância ───────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distância em KM em linha reta entre dois pontos geográficos.
    Usado apenas internamente para o algoritmo de otimização.
    """
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def distancia_rua(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Estimativa de distância real por rua (linha reta × fator).
    Retorna KM.
    """
    return haversine(lat1, lon1, lat2, lon2) * FATOR_ROTA


# ─── Algoritmo Nearest Neighbor ──────────────────────────────────────

def otimizar_rota(partida: dict, pontos: list) -> tuple[list, float]:
    """
    Ordena os pontos pelo algoritmo Nearest Neighbor (vizinho mais próximo).

    Args:
        partida: {"lat": float, "lng": float}
        pontos:  [{"lat": float, "lng": float, "id": int}, ...]

    Returns:
        (ordem, dist_total_km_real)
        - ordem: lista de índices em pontos[] na sequência otimizada
        - dist_total_km_real: distância total estimada por rua em KM
    """
    if not pontos:
        return [], 0.0

    n          = len(pontos)
    visitados  = [False] * n
    ordem      = []
    dist_total = 0.0

    cur_lat = partida["lat"]
    cur_lng = partida["lng"]

    for _ in range(n):
        melhor_idx  = -1
        melhor_dist = float("inf")

        for i, p in enumerate(pontos):
            if visitados[i]:
                continue
            d = haversine(cur_lat, cur_lng, p["lat"], p["lng"])
            if d < melhor_dist:
                melhor_dist = d
                melhor_idx  = i

        if melhor_idx == -1:
            break

        visitados[melhor_idx] = True
        ordem.append(melhor_idx)
        dist_total += melhor_dist
        cur_lat = pontos[melhor_idx]["lat"]
        cur_lng = pontos[melhor_idx]["lng"]

    # ── CORREÇÃO PRINCIPAL ────────────────────────────────────────────
    # Antes: salvava dist_total (linha reta) e o frontend multiplicava por 1.4
    # Agora: salva já com fator de rua aplicado → valor único e correto
    dist_total_real = dist_total * FATOR_ROTA

    return ordem, round(dist_total_real, 2)


# ─── Tempo estimado ──────────────────────────────────────────────────

def calcular_tempo(dist_km_real: float, num_paradas: int) -> int:
    """
    Estima tempo total em minutos: deslocamento + atendimentos.

    Args:
        dist_km_real: distância já com fator de rua (KM)
        num_paradas:  número de pontos de atendimento

    Returns:
        Minutos totais (int)
    """
    tempo_deslocamento = (dist_km_real / VELOCIDADE_KMH) * 60
    tempo_atendimento  = num_paradas * MINUTOS_PARADA
    return round(tempo_deslocamento + tempo_atendimento)


def formatar_tempo(minutos: int) -> str:
    if minutos < 60:
        return f"{minutos}min"
    h = minutos // 60
    m = minutos % 60
    return f"{h}h {m}min" if m else f"{h}h"