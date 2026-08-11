import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests

log = logging.getLogger("portotec.geo")

VIACEP_URL         = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL      = "https://nominatim.openstreetmap.org/search"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

HEADERS = {
    "User-Agent": "PortoTec/2.1 (roteiro de tecnicos; contato@portotec.com.br)"
}

TIMEOUT_VIACEP    = 6
TIMEOUT_GOOGLE    = 8
TIMEOUT_NOMINATIM = 8
TEMPO_MAXIMO_S    = 20

_sessao = requests.Session()
_sessao.headers.update(HEADERS)

_lock_nominatim = threading.Lock()
_ultima_chamada_nominatim = 0.0


@dataclass
class GeoResult:
    lat: float
    lng: float
    endereco: str
    preciso: bool = True
    cep: str = ""  # só preenchido quando a busca já revela o CEP (endereço livre)


def geocode_cep(cep: str, numero: str = "") -> Optional[GeoResult]:
    cep = "".join(c for c in str(cep or "") if c.isdigit())
    if len(cep) != 8:
        return None

    cache_key = f"{cep}_{numero}" if numero else cep

    cached = _get_cache(cache_key)
    if cached:
        return cached

    prazo = time.monotonic() + TEMPO_MAXIMO_S

    dados_cep = _viacep(cep)
    if not dados_cep:
        return None

    google_key = os.environ.get("GOOGLE_MAPS_KEY", "").strip()

    tentativas = []
    if google_key:
        tentativas.append(lambda: _google_geocode(dados_cep, numero, google_key))
    tentativas.append(lambda: _nominatim_full(dados_cep, numero))
    if numero:
        tentativas.append(lambda: _marcar_impreciso(_nominatim_full(dados_cep, "")))
    tentativas.append(lambda: _marcar_impreciso(_nominatim_cep(cep, dados_cep)))

    for tentativa in tentativas:
        if time.monotonic() > prazo:
            log.warning("Orçamento de tempo estourado ao geocodificar %s", cep)
            break
        resultado = tentativa()
        if resultado:
            _save_cache(cache_key, resultado)
            return resultado

    return None


def _marcar_impreciso(resultado: Optional[GeoResult]) -> Optional[GeoResult]:
    if resultado:
        resultado.preciso = False
    return resultado


def geocode_endereco_livre(texto: str) -> Optional[GeoResult]:
    """Geocodifica um endereço digitado por extenso (sem CEP conhecido),
    ex: "Rua Augusta 500, Consolação, São Paulo". Diferente de geocode_cep,
    não passa pelo ViaCEP — vai direto no Nominatim com o texto livre, e
    tenta extrair o CEP da resposta (nem sempre vem)."""
    texto = (texto or "").strip()
    if len(texto) < 6:
        return None

    texto_lower = texto.lower()
    consulta = texto if ("brasil" in texto_lower or "brazil" in texto_lower) else f"{texto}, Brasil"

    _throttle_nominatim()
    params = {
        "q": consulta, "format": "json", "limit": 1,
        "countrycodes": "br", "addressdetails": 1,
    }

    try:
        r = _sessao.get(NOMINATIM_URL, params=params, timeout=TIMEOUT_NOMINATIM)
        resultados = r.json()
        if not resultados:
            return None

        item = resultados[0]
        addr = item.get("address") or {}

        logradouro = addr.get("road") or ""
        numero     = addr.get("house_number") or ""
        bairro     = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter") or ""
        cidade     = addr.get("city") or addr.get("town") or addr.get("municipality") or ""
        estado     = addr.get("state") or ""
        cep        = "".join(c for c in (addr.get("postcode") or "") if c.isdigit())

        endereco_fmt = (
            _formatar_endereco(logradouro, numero, bairro, cidade, estado)
            if logradouro else (item.get("display_name") or texto)
        )

        return GeoResult(
            lat=float(item["lat"]),
            lng=float(item["lon"]),
            endereco=endereco_fmt,
            preciso=bool(numero),
            cep=cep,
        )
    except Exception as exc:
        log.warning("Geocodificação de endereço livre falhou (%r): %s", texto, exc)
        return None


def _google_geocode(dados_cep: dict, numero: str, api_key: str) -> Optional[GeoResult]:
    logradouro = (dados_cep.get("logradouro") or "").strip()
    bairro     = (dados_cep.get("bairro") or "").strip()
    cidade     = (dados_cep.get("localidade") or "").strip()
    estado     = (dados_cep.get("uf") or "").strip()
    cep        = "".join(c for c in (dados_cep.get("cep") or "") if c.isdigit())

    if not logradouro or not cidade:
        return None

    def _tentar(components: str) -> Optional[dict]:
        params = {
            "address":    _montar_query(logradouro, numero, bairro, cidade, estado),
            "components": components,
            "key":        api_key,
            "language":   "pt-BR",
            "region":     "br",
        }
        r = _sessao.get(GOOGLE_GEOCODE_URL, params=params, timeout=TIMEOUT_GOOGLE)
        return r.json()

    try:
        # Primeiro tenta restringindo pelo CEP exato (mais preciso quando bate).
        # O CEP dos Correios é MUITO mais granular que o postal_code que o
        # Google guarda pra cada rua — é comum uma rua toda ter um CEP
        # "genérico" no Google (ex: 08270-000) enquanto o ViaCEP devolve um
        # CEP específico daquele trecho (ex: 08270-580). Com a restrição
        # ligada, isso vira ZERO_RESULTS mesmo a rua existindo no Google —
        # então se der zero resultado, tenta de novo só com country:BR.
        data = _tentar(f"country:BR|postal_code:{cep}")
        status = data.get("status")

        if status == "REQUEST_DENIED":
            log.warning("Google Geocoding negou: %s",
                        data.get("error_message", "REQUEST_DENIED"))
            return None
        if status == "OVER_QUERY_LIMIT":
            log.warning("Google Geocoding: cota estourada")
            return None

        results = data.get("results") or []
        if not results and status == "ZERO_RESULTS":
            data = _tentar("country:BR")
            results = data.get("results") or []
        if not results:
            return None

        melhor = results[0]
        loc = melhor["geometry"]["location"]
        tipo = melhor["geometry"].get("location_type", "")

        return GeoResult(
            lat=float(loc["lat"]),
            lng=float(loc["lng"]),
            endereco=_formatar_endereco(logradouro, numero, bairro, cidade, estado),
            preciso=tipo in ("ROOFTOP", "RANGE_INTERPOLATED"),
        )
    except Exception as exc:
        log.warning("Google Geocoding falhou: %s", exc)
        return None


def _nominatim_full(dados_cep: dict, numero: str) -> Optional[GeoResult]:
    logradouro = (dados_cep.get("logradouro") or "").strip()
    bairro     = (dados_cep.get("bairro") or "").strip()
    cidade     = (dados_cep.get("localidade") or "").strip()
    estado     = (dados_cep.get("uf") or "").strip()

    if not logradouro or not cidade:
        return None

    _throttle_nominatim()

    params = {
        "q":              _montar_query(logradouro, numero, bairro, cidade, estado),
        "format":         "json",
        "limit":          1,
        "countrycodes":   "br",
        "addressdetails": 1,
    }

    try:
        r = _sessao.get(NOMINATIM_URL, params=params, timeout=TIMEOUT_NOMINATIM)
        results = r.json()
        if results:
            return GeoResult(
                lat=float(results[0]["lat"]),
                lng=float(results[0]["lon"]),
                endereco=_formatar_endereco(logradouro, numero, bairro, cidade, estado),
            )
    except Exception as exc:
        log.debug("Nominatim falhou: %s", exc)

    return None


def _nominatim_cep(cep: str, dados_cep: dict) -> Optional[GeoResult]:
    _throttle_nominatim()

    params = {
        "q":            f"{cep}, Brasil",
        "format":       "json",
        "limit":        1,
        "countrycodes": "br",
    }

    try:
        r = _sessao.get(NOMINATIM_URL, params=params, timeout=TIMEOUT_NOMINATIM)
        results = r.json()
        if results:
            return GeoResult(
                lat=float(results[0]["lat"]),
                lng=float(results[0]["lon"]),
                endereco=_formatar_endereco(
                    dados_cep.get("logradouro", ""), "",
                    dados_cep.get("bairro", ""),
                    dados_cep.get("localidade", ""),
                    dados_cep.get("uf", ""),
                ),
                preciso=False,
            )
    except Exception as exc:
        log.debug("Nominatim (CEP) falhou: %s", exc)

    return None


def _viacep(cep: str) -> Optional[dict]:
    try:
        r = _sessao.get(VIACEP_URL.format(cep=cep), timeout=TIMEOUT_VIACEP)
        if r.status_code != 200:
            return None
        data = r.json()
        return None if data.get("erro") else data
    except Exception as exc:
        log.warning("ViaCEP falhou para %s: %s", cep, exc)
        return None


def _montar_query(logradouro, numero, bairro, cidade, estado) -> str:
    partes = [logradouro]
    if numero:
        partes.append(numero)
    if bairro:
        partes.append(bairro)
    partes += [cidade, estado, "Brasil"]
    return ", ".join(p for p in partes if p)


def _formatar_endereco(logradouro: str, numero: str, bairro: str,
                       cidade: str, estado: str) -> str:
    partes = []
    if logradouro:
        partes.append(logradouro + (f", {numero}" if numero else ""))
    if bairro:
        partes.append(bairro)
    if cidade and estado:
        partes.append(f"{cidade} - {estado}")
    elif cidade:
        partes.append(cidade)
    return " · ".join(partes) if partes else (logradouro or "Endereço desconhecido")


def _throttle_nominatim():
    global _ultima_chamada_nominatim
    with _lock_nominatim:
        espera = 1.1 - (time.time() - _ultima_chamada_nominatim)
        if espera > 0:
            time.sleep(espera)
        _ultima_chamada_nominatim = time.time()


def _get_cache(chave: str) -> Optional[GeoResult]:
    try:
        from database import db_conn, fetch_one
        with db_conn() as conn:
            r = fetch_one(conn, "SELECT * FROM cache_geo WHERE cep = ?", (chave,))
        if r and r.get("lat") is not None:
            return GeoResult(
                lat=r["lat"],
                lng=r["lng"],
                endereco=r.get("endereco") or "",
                preciso=bool(r.get("preciso", True)),
            )
    except Exception as exc:
        log.debug("Leitura de cache_geo falhou: %s", exc)
    return None


def _save_cache(chave: str, geo: GeoResult):
    try:
        from database import IS_PG, db_conn, execute
        with db_conn(commit=True) as conn:
            if IS_PG:
                execute(conn, """
                    INSERT INTO cache_geo (cep, endereco, lat, lng, preciso)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (cep) DO UPDATE
                    SET endereco   = EXCLUDED.endereco,
                        lat        = EXCLUDED.lat,
                        lng        = EXCLUDED.lng,
                        preciso    = EXCLUDED.preciso,
                        updated_at = CURRENT_TIMESTAMP
                """, (chave, geo.endereco, geo.lat, geo.lng, geo.preciso))
            else:
                execute(conn, """
                    INSERT OR REPLACE INTO cache_geo (cep, endereco, lat, lng, preciso)
                    VALUES (?, ?, ?, ?, ?)
                """, (chave, geo.endereco, geo.lat, geo.lng, 1 if geo.preciso else 0))
    except Exception as exc:
        log.warning("Gravação de cache_geo falhou: %s", exc)


def limpar_cache(cep: str = None) -> int:
    from database import db_conn, execute
    with db_conn(commit=True) as conn:
        if cep:
            digitos = "".join(c for c in str(cep) if c.isdigit())
            return execute(conn, "DELETE FROM cache_geo WHERE cep LIKE ?", (f"{digitos}%",))
        return execute(conn, "DELETE FROM cache_geo")