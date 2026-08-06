import math

FATOR_ROTA     = 1.4
VELOCIDADE_KMH = 40
MINUTOS_PARADA = 20

OTIMIZAR_COM_RETORNO = False

_BASE = -1


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def distancia_rua(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return haversine(lat1, lon1, lat2, lon2) * FATOR_ROTA


def _matrizes(partida: dict, pontos: list):
    n = len(pontos)
    dp = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(pontos[i]["lat"], pontos[i]["lng"],
                          pontos[j]["lat"], pontos[j]["lng"])
            dp[i][j] = dp[j][i] = d

    db = [haversine(partida["lat"], partida["lng"], p["lat"], p["lng"])
          for p in pontos]
    return dp, db


def _dist(a: int, b: int, dp, db) -> float:
    if a == _BASE:
        return db[b]
    if b == _BASE:
        return db[a]
    return dp[a][b]


def _nearest_neighbor(n: int, dp, db) -> list:
    visitados = [False] * n
    ordem = []
    atual = _BASE

    for _ in range(n):
        melhor_idx, melhor_dist = -1, float("inf")
        for i in range(n):
            if visitados[i]:
                continue
            d = _dist(atual, i, dp, db)
            if d < melhor_dist:
                melhor_dist, melhor_idx = d, i
        if melhor_idx == -1:
            break
        visitados[melhor_idx] = True
        ordem.append(melhor_idx)
        atual = melhor_idx

    return ordem


def _custo(ordem: list, dp, db, com_retorno: bool) -> float:
    if not ordem:
        return 0.0
    total = db[ordem[0]]
    for a, b in zip(ordem, ordem[1:]):
        total += dp[a][b]
    if com_retorno:
        total += db[ordem[-1]]
    return total


def _dois_opt(ordem: list, dp, db, com_retorno: bool, max_passes: int = 40) -> list:
    n = len(ordem)
    if n < 3:
        return ordem

    ordem = ordem[:]
    for _ in range(max_passes):
        melhorou = False

        for i in range(n):
            anterior = _BASE if i == 0 else ordem[i - 1]

            for j in range(i + 1, n):
                if j + 1 < n:
                    seguinte = ordem[j + 1]
                elif com_retorno:
                    seguinte = _BASE
                else:
                    seguinte = None

                antes = _dist(anterior, ordem[i], dp, db)
                depois = _dist(anterior, ordem[j], dp, db)
                if seguinte is not None:
                    antes += _dist(ordem[j], seguinte, dp, db)
                    depois += _dist(ordem[i], seguinte, dp, db)

                if depois < antes - 1e-9:
                    ordem[i:j + 1] = reversed(ordem[i:j + 1])
                    melhorou = True

        if not melhorou:
            break

    return ordem


def otimizar_rota(partida: dict, pontos: list) -> dict:
    vazio = {
        "ordem": [], "distancia_km": 0.0, "retorno_km": 0.0,
        "total_km": 0.0, "tempo_minutos": 0, "ganho_2opt_km": 0.0,
    }
    if not pontos or partida.get("lat") is None or partida.get("lng") is None:
        return vazio

    n = len(pontos)
    dp, db = _matrizes(partida, pontos)

    ordem_nn = _nearest_neighbor(n, dp, db)
    custo_nn = _custo(ordem_nn, dp, db, OTIMIZAR_COM_RETORNO)

    ordem = _dois_opt(ordem_nn, dp, db, OTIMIZAR_COM_RETORNO)
    custo_final = _custo(ordem, dp, db, OTIMIZAR_COM_RETORNO)

    dist_ida = _custo(ordem, dp, db, com_retorno=False) * FATOR_ROTA
    retorno = (db[ordem[-1]] * FATOR_ROTA) if ordem else 0.0
    ganho = max(0.0, (custo_nn - custo_final) * FATOR_ROTA)

    return {
        "ordem":          ordem,
        "distancia_km":   round(dist_ida, 2),
        "retorno_km":     round(retorno, 2),
        "total_km":       round(dist_ida + retorno, 2),
        "tempo_minutos":  calcular_tempo(dist_ida, n),
        "ganho_2opt_km":  round(ganho, 2),
    }


def calcular_tempo(dist_km_real: float, num_paradas: int) -> int:
    tempo_deslocamento = (dist_km_real / VELOCIDADE_KMH) * 60
    tempo_atendimento = num_paradas * MINUTOS_PARADA
    return int(round(tempo_deslocamento + tempo_atendimento))


def formatar_tempo(minutos: int) -> str:
    if minutos < 60:
        return f"{minutos}min"
    h, m = divmod(minutos, 60)
    return f"{h}h {m}min" if m else f"{h}h"