import math

def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def otimizar_rota(partida: dict, pontos: list) -> tuple:
    if not pontos:
        return [], 0.0

    nao_visitados = list(range(len(pontos)))
    rota = []
    atual_lat = partida["lat"]
    atual_lng = partida["lng"]
    distancia_total = 0.0

    while nao_visitados:
        mais_proximo = min(
            nao_visitados,
            key=lambda i: haversine(
                atual_lat, atual_lng,
                pontos[i]["lat"], pontos[i]["lng"]
            )
        )

        dist = haversine(
            atual_lat, atual_lng,
            pontos[mais_proximo]["lat"], pontos[mais_proximo]["lng"]
        )

        distancia_total += dist
        atual_lat = pontos[mais_proximo]["lat"]
        atual_lng = pontos[mais_proximo]["lng"]
        rota.append(mais_proximo)
        nao_visitados.remove(mais_proximo)  # ← estava faltando isso!

    return rota, round(distancia_total, 2)  # ← e isso!