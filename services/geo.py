"""
services/geo.py  —  PortoTec
─────────────────────────────────────────────────────────────────────
Geocodificação robusta em 4 camadas:

  1. Cache local (tabela cache_geo) — evita rechamadas desnecessárias
  2. Google Maps Geocoding API — fonte principal, alta precisão para BR
  3. Nominatim (OpenStreetMap) — fallback se Google falhar ou key ausente
  4. ViaCEP como provedor de dados do endereço (CEP → rua, bairro, cidade)

Variável de ambiente necessária:
  GOOGLE_MAPS_KEY  — chave da Google Maps Geocoding API
  DATABASE_URL     — se presente, usa PostgreSQL; caso contrário, SQLite
"""

import requests
import time
import os
from dataclasses import dataclass
from typing import Optional

VIACEP_URL        = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL     = "https://nominatim.openstreetmap.org/search"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

HEADERS = {
    "User-Agent": "PortoTec/2.0 (roteiro de tecnicos; contato@portotec.com.br)"
}

# Intervalo mínimo entre chamadas ao Nominatim (respeita política de uso)
_last_nominatim_call = 0.0


@dataclass
class GeoResult:
    lat: float
    lng: float
    endereco: str          # endereço formatado completo
    preciso: bool = True   # False = centroide do CEP (impreciso)


# ─── API pública ──────────────────────────────────────────────────────

def geocode_cep(cep: str, numero: str = "") -> Optional[GeoResult]:
    """
    Geocodifica um CEP, usando o número da casa quando disponível.
    Salva/lê do cache automático.

    Ordem de tentativas:
      1. Cache local
      2. Google Maps Geocoding API  (requer GOOGLE_MAPS_KEY)
      3. Nominatim com endereço completo (com número)
      4. Nominatim só com a rua (sem número) — marcado como impreciso
      5. Nominatim pelo CEP diretamente — marcado como impreciso

    Args:
        cep:    CEP sem hífen (8 dígitos)
        numero: Número da casa/estabelecimento (ex: "307")

    Returns:
        GeoResult com lat, lng, endereco, preciso | None se não encontrado
    """
    cep = cep.replace("-", "").strip()
    if len(cep) != 8 or not cep.isdigit():
        return None

    # Chave de cache inclui número para diferenciar endereços na mesma rua
    cache_key = f"{cep}_{numero}" if numero else cep

    # 1. Cache
    cached = _get_cache(cache_key)
    if cached:
        return cached

    # 2. Dados do endereço via ViaCEP (necessário para todas as camadas)
    dados_cep = _viacep(cep)
    if not dados_cep:
        return None

    # 3. Google Maps — fonte principal
    google_key = os.environ.get("GOOGLE_MAPS_KEY", "").strip()
    if google_key:
        resultado = _google_geocode(dados_cep, numero, google_key)
        if resultado:
            _save_cache(cache_key, resultado)
            return resultado

    # 4. Nominatim com endereço completo (com número)
    resultado = _nominatim_full(dados_cep, numero)
    if resultado:
        _save_cache(cache_key, resultado)
        return resultado

    # 5. Nominatim só com a rua (sem número) — impreciso
    resultado = _nominatim_full(dados_cep, numero="")
    if resultado:
        resultado.preciso = False
        _save_cache(cache_key, resultado)
        return resultado

    # 6. Último recurso: centroide do CEP via Nominatim — impreciso
    resultado = _nominatim_cep(cep, dados_cep)
    if resultado:
        resultado.preciso = False
        _save_cache(cache_key, resultado)
        return resultado

    return None


# ─── Google Maps ──────────────────────────────────────────────────────

def _google_geocode(dados_cep: dict, numero: str, api_key: str) -> Optional[GeoResult]:
    """
    Geocodifica via Google Maps Geocoding API.

    Monta o endereço completo e envia como `address` + `components`
    para restringir ao Brasil sem perder precisão do número.

    Retorna GeoResult com preciso=True se encontrou geometry.location_type
    igual a ROOFTOP ou RANGE_INTERPOLATED; False para os demais.
    """
    logradouro = dados_cep.get("logradouro", "").strip()
    bairro     = dados_cep.get("bairro", "").strip()
    cidade     = dados_cep.get("localidade", "").strip()
    estado     = dados_cep.get("uf", "").strip()
    cep        = dados_cep.get("cep", "").replace("-", "").strip()

    if not logradouro or not cidade:
        return None

    # Monta endereço legível para a query
    partes = [logradouro]
    if numero:
        partes.append(numero)
    if bairro:
        partes.append(bairro)
    partes += [cidade, estado, "Brasil"]
    address_query = ", ".join(partes)

    params = {
        "address":    address_query,
        "components": f"country:BR|postal_code:{cep}",
        "key":        api_key,
        "language":   "pt-BR",
        "region":     "br",
    }

    try:
        r = requests.get(GOOGLE_GEOCODE_URL, params=params, timeout=10)
        data = r.json()

        status = data.get("status")
        if status == "REQUEST_DENIED":
            # Chave inválida ou API não habilitada — loga e cai no fallback
            _log_google_error(data.get("error_message", "REQUEST_DENIED"))
            return None
        if status != "OK":
            return None

        results = data.get("results", [])
        if not results:
            return None

        best = results[0]
        location      = best["geometry"]["location"]
        location_type = best["geometry"].get("location_type", "")

        lat = float(location["lat"])
        lng = float(location["lng"])

        # ROOFTOP = ponto exato da edificação; RANGE_INTERPOLATED = interpolado no logradouro
        # Ambos são considerados precisos para roteamento de técnicos
        preciso = location_type in ("ROOFTOP", "RANGE_INTERPOLATED")

        end_formatado = _formatar_endereco(logradouro, numero, bairro, cidade, estado)
        return GeoResult(lat=lat, lng=lng, endereco=end_formatado, preciso=preciso)

    except Exception as exc:
        _log_google_error(str(exc))
        return None


def _log_google_error(msg: str):
    """Log simples para erros da Google API (não quebra o fluxo)."""
    import logging
    logging.getLogger("portotec.geo").warning("Google Geocoding falhou: %s", msg)


# ─── Nominatim (fallback) ─────────────────────────────────────────────

def _nominatim_full(dados_cep: dict, numero: str) -> Optional[GeoResult]:
    """
    Geocodifica usando endereço completo montado a partir dos dados do ViaCEP.
    Tenta formato free-form compatível com o Nominatim.
    """
    logradouro = dados_cep.get("logradouro", "").strip()
    bairro     = dados_cep.get("bairro", "").strip()
    cidade     = dados_cep.get("localidade", "").strip()
    estado     = dados_cep.get("uf", "").strip()

    if not logradouro or not cidade:
        return None

    _throttle_nominatim()

    partes = [logradouro]
    if numero:
        partes.append(numero)
    if bairro:
        partes.append(bairro)
    partes += [cidade, estado, "Brasil"]
    query = ", ".join(partes)

    params = {
        "q":              query,
        "format":         "json",
        "limit":          1,
        "countrycodes":   "br",
        "addressdetails": 1,
    }

    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        results = r.json()
        if results:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            end_formatado = _formatar_endereco(logradouro, numero, bairro, cidade, estado)
            return GeoResult(lat=lat, lng=lon, endereco=end_formatado)
    except Exception:
        pass

    return None


def _nominatim_cep(cep: str, dados_cep: dict) -> Optional[GeoResult]:
    """Geocodifica pelo CEP diretamente (centroide — impreciso)."""
    _throttle_nominatim()

    cidade     = dados_cep.get("localidade", "")
    estado     = dados_cep.get("uf", "")
    logradouro = dados_cep.get("logradouro", "")
    bairro     = dados_cep.get("bairro", "")

    params = {
        "q":            f"{cep}, Brasil",
        "format":       "json",
        "limit":        1,
        "countrycodes": "br",
    }

    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        results = r.json()
        if results:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            end_formatado = _formatar_endereco(logradouro, "", bairro, cidade, estado)
            return GeoResult(lat=lat, lng=lon, endereco=end_formatado, preciso=False)
    except Exception:
        pass

    return None


# ─── ViaCEP ───────────────────────────────────────────────────────────

def _viacep(cep: str) -> Optional[dict]:
    """Busca dados do endereço no ViaCEP."""
    try:
        r = requests.get(VIACEP_URL.format(cep=cep), timeout=8, headers=HEADERS)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("erro"):
            return None
        return data
    except Exception:
        return None


# ─── Utilitários ──────────────────────────────────────────────────────

def _formatar_endereco(logradouro: str, numero: str, bairro: str,
                        cidade: str, estado: str) -> str:
    """Monta string de endereço legível para salvar no banco."""
    partes = []
    if logradouro:
        partes.append(logradouro + (f", {numero}" if numero else ""))
    if bairro:
        partes.append(bairro)
    if cidade and estado:
        partes.append(f"{cidade} - {estado}")
    elif cidade:
        partes.append(cidade)
    return " · ".join(partes) if partes else logradouro or "Endereço desconhecido"


def _throttle_nominatim():
    """Garante no mínimo 1.1 s entre chamadas ao Nominatim (política de uso)."""
    global _last_nominatim_call
    elapsed = time.time() - _last_nominatim_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _last_nominatim_call = time.time()


# ─── Cache ────────────────────────────────────────────────────────────

def _get_cache(key: str) -> Optional[GeoResult]:
    try:
        from database import get_db
        conn = get_db()
        cur  = conn.cursor()
        PG   = bool(os.environ.get("DATABASE_URL"))
        PH   = "%s" if PG else "?"
        cur.execute(f"SELECT * FROM cache_geo WHERE cep = {PH}", (key,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            r = dict(row)
            return GeoResult(
                lat=r["lat"],
                lng=r["lng"],
                endereco=r["endereco"] or "",
                preciso=True  # dado em cache já foi validado anteriormente
            )
    except Exception:
        pass
    return None


def _save_cache(key: str, geo: GeoResult):
    try:
        from database import get_db
        conn = get_db()
        cur  = conn.cursor()
        PG   = bool(os.environ.get("DATABASE_URL"))
        if PG:
            cur.execute(
                """INSERT INTO cache_geo (cep, endereco, lat, lng)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (cep) DO UPDATE
                   SET endereco   = EXCLUDED.endereco,
                       lat        = EXCLUDED.lat,
                       lng        = EXCLUDED.lng,
                       updated_at = CURRENT_TIMESTAMP""",
                (key, geo.endereco, geo.lat, geo.lng)
            )
        else:
            cur.execute(
                """INSERT OR REPLACE INTO cache_geo (cep, endereco, lat, lng)
                   VALUES (?, ?, ?, ?)""",
                (key, geo.endereco, geo.lat, geo.lng)
            )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass