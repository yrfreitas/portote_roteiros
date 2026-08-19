import math

# Constantes da estimativa LOCAL — a rede de segurança de quando não há chave
# do Google ou o serviço de trânsito falha. Enquanto foram a única fonte, a
# previsão que o cliente recebia errava sempre para o mesmo lado: prometia
# chegada bem mais cedo do que a real.
#
# FATOR_ROTA 1.4 -> 1.55: haversine mede a reta entre dois pontos. Em cidade
# com rio, marginal, sentido único e quadra fechada, o caminho de carro passa
# de 1,5x a reta com folga. O 1.4 vinha de trecho aberto, não de zona leste.
#
# VELOCIDADE 40 -> 26 km/h: 40 km/h de média não existe em rua de cidade em
# horário comercial. Somando semáforo, trânsito e a procura por vaga, a média
# real de deslocamento urbano fica entre 20 e 30.
#
# Continua sendo estimativa: o número bom vem do services/rota_tempo.py, que
# pergunta o tempo real com o trânsito do momento. Estes valores só precisam
# não mentir quando ele não estiver disponível.
FATOR_ROTA     = 1.55
VELOCIDADE_KMH = 26
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


def calcular_rota_fixa(partida: dict, pontos_em_ordem: list) -> dict:
    """Calcula distância/tempo para uma sequência JÁ DEFINIDA manualmente —
    ao contrário de otimizar_rota, não reordena nada, só mede o trajeto
    na ordem em que os pontos foram passados. Usado quando o técnico
    reorganiza a rota à mão e queremos refletir a escolha dele, não a
    do otimizador."""
    vazio = {"distancia_km": 0.0, "retorno_km": 0.0, "total_km": 0.0, "tempo_minutos": 0}
    if not pontos_em_ordem or partida.get("lat") is None or partida.get("lng") is None:
        return vazio

    n = len(pontos_em_ordem)
    dp, db = _matrizes(partida, pontos_em_ordem)
    identidade = list(range(n))

    dist_ida = _custo(identidade, dp, db, com_retorno=False) * FATOR_ROTA
    retorno = (db[identidade[-1]] * FATOR_ROTA) if identidade else 0.0

    return {
        "distancia_km":  round(dist_ida, 2),
        "retorno_km":    round(retorno, 2),
        "total_km":      round(dist_ida + retorno, 2),
        "tempo_minutos": calcular_tempo(dist_ida, n),
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