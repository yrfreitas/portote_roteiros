# -*- coding: utf-8 -*-
"""Tempo de viagem REAL entre dois pontos.

POR QUE ESTE MÓDULO EXISTE
--------------------------
A previsão que o cliente via era calculada assim:

    minutos = (distancia_em_linha_reta * 1.3 / 40 km/h) * 60

Três chutes empilhados. `haversine` mede a reta entre dois pontos — em São
Paulo o caminho real é bem mais longo (rios, marginais, sentido único, quadras
fechadas), e o fator 1,3 não cobre isso. E 40 km/h médios é uma velocidade que
não existe em rua de cidade em horário comercial: com trânsito, semáforo e a
procura por vaga, a média fica bem abaixo.

O erro somava nas duas pontas e sempre para o mesmo lado — dizia ao cliente
que o técnico chegava MUITO antes do que chegava.

O QUE MUDOU
-----------
Passa a perguntar ao Google quanto tempo leva de carro AGORA, com o trânsito
do momento (`departure_time=now` devolve `duration_in_traffic`). É medida, não
estimativa.

CUSTO E CACHE
-------------
Cada consulta é uma requisição paga. O rastreio atualiza a posição a cada
poucos segundos, e perguntar a cada atualização gastaria cota à toa: em 30
segundos de trânsito o tempo de chegada não muda de forma perceptível para
quem espera em casa.

Por isso a origem é ARREDONDADA para ~100 m antes de virar chave de cache, e a
resposta vale por 90 segundos. O técnico andando meio quarteirão reaproveita a
mesma resposta; ao mudar de quadra, pergunta de novo.

SEM CHAVE, OU COM O GOOGLE FORA DO AR
-------------------------------------
Cai na estimativa local — que continua existindo como rede de segurança, mas
recalibrada (ver otimizador.py). Previsão pior é melhor que nenhuma; o que não
podia continuar era ela ser a única e estar sempre errada.
"""
import logging
import os
import threading
import time

import requests

log = logging.getLogger("portotec.rota_tempo")

URL_MATRIZ = "https://maps.googleapis.com/maps/api/distancematrix/json"

# OSRM: roteamento por ruas de verdade, gratuito e sem chave. É a fonte que
# funciona HOJE — a chave do Google do projeto só tem Geocoding liberado e a
# Distance Matrix responde REQUEST_DENIED (verificado em 2026-08-19).
#
# Ele devolve o tempo de VIA LIVRE, sem trânsito. Medido no trecho
# Av. Nordestina -> Av. Águia de Haia: 9,1 km por ruas contra 6,7 km em linha
# reta, 15 min livres. A distância é medida; o que falta é o congestionamento.
URL_OSRM = "https://router.project-osrm.org/route/v1/driving/{o_lng},{o_lat};{d_lng},{d_lat}"

# Table API: distância/tempo de RUA entre TODOS os pares de uma lista de
# pontos, numa chamada SÓ (não uma por par) -- é o que faltava pro
# otimizador de rota (services/otimizador.py) parar de ordenar as paradas
# por LINHA RETA (rio, marginal, sentido único e quadra fechada fazem a
# ordem "mais perto em linha reta" ser pior na rua de verdade, mesmo
# problema já documentado pra ETA individual, nunca corrigido na ORDEM).
# Pedido de 2026-09-04: "otimização de CEP" não ajudava de verdade.
URL_OSRM_TABLE = "https://router.project-osrm.org/table/v1/driving/{coords}"
TIMEOUT_OSRM_TABLE = 10

# Fator de trânsito aplicado sobre o tempo de via livre do OSRM.
#
# É calibração, não medida — e por isso fica configurável. 1.45 corresponde a
# uma via urbana em horário comercial em São Paulo. Quando a Distance Matrix
# for habilitada, este fator deixa de ser usado: o Google devolve o tempo com
# o trânsito real e não precisa de multiplicador.
FATOR_TRANSITO = float(os.environ.get("FATOR_TRANSITO", "1.45"))

TIMEOUT = 8
TIMEOUT_OSRM = 6

# 90s: acima disso a previsão fica velha durante um deslocamento; abaixo,
# gasta cota sem o número mudar de forma perceptível para quem espera.
VALIDADE_S = 90

# ~100 m. Arredondar a origem faz o técnico parado no semáforo, ou andando
# meia quadra, reaproveitar a resposta em vez de gerar consulta nova.
CASAS_DECIMAIS = 3

_sessao = requests.Session()
_cache = {}
_trava = threading.Lock()

# Desliga o Google depois que ele recusa.
#
# A chave do projeto só tem Geocoding liberado, e a Distance Matrix responde
# REQUEST_DENIED. Sem esta trava, TODA previsão de chegada gastava uma ida à
# rede para receber a mesma recusa e escrever a mesma linha de aviso no log —
# num rastreio que atualiza a cada poucos segundos, isso é ruído constante e
# latência somada à toa.
#
# NÃO é permanente, e a primeira versão errou nisso. Ao habilitar a Distance
# Matrix numa chave, a liberação se propaga aos poucos pelos servidores do
# Google: medido em 2026-08-19, 5 de 6 chamadas passavam e 1 ainda recusava.
# Com trava na primeira recusa, essa única falha desligaria o trânsito real
# pelo resto do dia — e ninguém saberia por quê.
#
# Por isso: só desliga após 3 recusas SEGUIDAS (uma passagem zera a contagem),
# e volta a tentar sozinho depois de 15 minutos. Falha passageira não pode
# virar decisão permanente.
_recusas_seguidas = 0
_google_bloqueado_ate = 0.0
RECUSAS_PARA_DESLIGAR = 3
ESPERA_APOS_BLOQUEIO_S = 15 * 60


def configurado() -> bool:
    return bool(os.environ.get("GOOGLE_MAPS_KEY", "").strip())


def _chave(o_lat, o_lng, d_lat, d_lng):
    return (round(o_lat, CASAS_DECIMAIS), round(o_lng, CASAS_DECIMAIS),
            round(d_lat, 5), round(d_lng, 5))


def _google(origem_lat, origem_lng, destino_lat, destino_lng):
    """Minutos de carro até o destino, com o trânsito de agora.

    Devolve None quando não há chave, a chamada falha ou o Google não encontra
    caminho — nesses casos quem chama decide o que fazer (hoje: cair na
    estimativa local). Nunca levanta exceção: previsão de chegada não pode
    derrubar o rastreio.
    """
    global _recusas_seguidas, _google_bloqueado_ate
    if time.monotonic() < _google_bloqueado_ate:
        return None

    chave_api = os.environ.get("GOOGLE_MAPS_KEY", "").strip()
    if not chave_api:
        return None
    if None in (origem_lat, origem_lng, destino_lat, destino_lng):
        return None

    try:
        r = _sessao.get(URL_MATRIZ, timeout=TIMEOUT, params={
            "origins": f"{origem_lat},{origem_lng}",
            "destinations": f"{destino_lat},{destino_lng}",
            "mode": "driving",
            # departure_time=now é o que faz a resposta trazer
            # duration_in_traffic. Sem ele vem o tempo "de rua vazia", que é
            # justamente o número irreal que estávamos mostrando.
            "departure_time": "now",
            "language": "pt-BR",
            "key": chave_api,
        })
        r.raise_for_status()
        dados = r.json()

        if dados.get("status") != "OK":
            if dados.get("status") in ("REQUEST_DENIED", "OVER_QUERY_LIMIT"):
                _recusas_seguidas += 1
                if _recusas_seguidas >= RECUSAS_PARA_DESLIGAR:
                    _google_bloqueado_ate = time.monotonic() + ESPERA_APOS_BLOQUEIO_S
                    log.warning(
                        "Distance Matrix recusou %d vezes seguidas (%s) — usando "
                        "OSRM e tentando de novo em %d min. Se persistir, "
                        "confira se a Distance Matrix API esta habilitada E "
                        "liberada nas restricoes da GOOGLE_MAPS_KEY.",
                        _recusas_seguidas, dados.get("status"),
                        ESPERA_APOS_BLOQUEIO_S // 60)
            else:
                log.warning("Distance Matrix devolveu status %s", dados.get("status"))
            return None

        elemento = dados["rows"][0]["elements"][0]
        if elemento.get("status") != "OK":
            # ZERO_RESULTS acontece com ponto em local sem via de acesso.
            log.info("Sem rota entre os pontos: %s", elemento.get("status"))
            return None

        # duration_in_traffic quando existe; duration é o plano B (o Google
        # omite o primeiro em alguns casos, como trajeto muito curto).
        seg = (elemento.get("duration_in_traffic")
               or elemento.get("duration") or {}).get("value")
        if not seg:
            return None

        _recusas_seguidas = 0   # passou: a sequência de recusas se rompeu
        return max(1, int(round(seg / 60)))
    except Exception as exc:
        log.warning("Falha ao consultar tempo de viagem: %s", exc)
        return None


def _osrm(origem_lat, origem_lng, destino_lat, destino_lng):
    """Tempo por RUAS de verdade, sem trânsito, multiplicado pelo fator urbano.

    Sem chave e sem custo. Note a ordem das coordenadas: o OSRM espera
    longitude ANTES da latitude, o contrário do Google — trocar as duas
    devolve uma rota do outro lado do mundo, silenciosamente.
    """
    try:
        r = _sessao.get(
            URL_OSRM.format(o_lat=origem_lat, o_lng=origem_lng,
                            d_lat=destino_lat, d_lng=destino_lng),
            params={"overview": "false"}, timeout=TIMEOUT_OSRM)
        r.raise_for_status()
        dados = r.json()
        if dados.get("code") != "Ok" or not dados.get("routes"):
            return None
        livre_s = dados["routes"][0]["duration"]
        return max(1, int(round(livre_s * FATOR_TRANSITO / 60)))
    except Exception as exc:
        log.warning("Falha no OSRM: %s", exc)
        return None


def matriz_osrm(pontos):
    """Distância (km) e duração (min) por RUA entre TODOS os pares de
    `pontos` ([{lat, lng}, ...]), numa chamada só via OSRM Table API.

    Devolve (matriz_km, matriz_min) -- listas NxN -- ou (None, None) se o
    OSRM falhar ou algum ponto não tiver lat/lng (aí quem chama cai na
    estimativa por linha reta, mesma rede de segurança do resto do
    módulo). Sem trânsito (é "via livre" do OSRM): o fator urbano
    (FATOR_TRANSITO) é aplicado por cima, igual _osrm() já faz par a par.
    """
    if not pontos or any(p.get("lat") is None or p.get("lng") is None for p in pontos):
        return None, None
    if len(pontos) < 2:
        return None, None

    coords = ";".join(f"{p['lng']},{p['lat']}" for p in pontos)
    try:
        r = _sessao.get(
            URL_OSRM_TABLE.format(coords=coords),
            params={"annotations": "distance,duration"},
            timeout=TIMEOUT_OSRM_TABLE)
        r.raise_for_status()
        dados = r.json()
        if dados.get("code") != "Ok" or not dados.get("distances") or not dados.get("durations"):
            return None, None

        matriz_km = [[(d / 1000.0 if d is not None else None) for d in linha]
                     for linha in dados["distances"]]
        matriz_min = [[(round(d * FATOR_TRANSITO / 60, 1) if d is not None else None) for d in linha]
                      for linha in dados["durations"]]
        return matriz_km, matriz_min
    except Exception as exc:
        log.warning("Falha na tabela OSRM (%d pontos): %s", len(pontos), exc)
        return None, None


def minutos_ate(origem_lat, origem_lng, destino_lat, destino_lng):
    """Minutos até o destino, da melhor fonte disponível.

    Ordem: Google com trânsito (medido) -> OSRM por ruas mais fator urbano
    (distância medida, trânsito calibrado) -> None, e aí quem chama cai na
    estimativa local por linha reta.

    O cache é compartilhado pelas duas fontes: o que importa para quem espera
    é o número, não de onde veio.
    """
    if None in (origem_lat, origem_lng, destino_lat, destino_lng):
        return None

    k = _chave(origem_lat, origem_lng, destino_lat, destino_lng)
    agora = time.monotonic()
    with _trava:
        guardado = _cache.get(k)
        if guardado and agora - guardado[0] < VALIDADE_S:
            return guardado[1]

    minutos = (_google(origem_lat, origem_lng, destino_lat, destino_lng)
               or _osrm(origem_lat, origem_lng, destino_lat, destino_lng))
    if minutos is None:
        return None

    with _trava:
        _cache[k] = (agora, minutos)
        if len(_cache) > 500:
            limite = agora - VALIDADE_S
            for chave in [c for c, v in _cache.items() if v[0] < limite]:
                _cache.pop(chave, None)
    return minutos
