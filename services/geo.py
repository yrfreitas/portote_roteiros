"""
services/geo.py  —  PortoTec
─────────────────────────────────────────────────────────────────────
Geocodificação robusta em 3 camadas:

  1. Cache local (tabela cache_geo) — evita rechamadas desnecessárias
  2. Nominatim (OpenStreetMap) com endereço completo (rua + número)
  3. ViaCEP como fallback de dados do endereço

CORREÇÕES aplicadas:
  ✅ Usa número da casa no geocoding → coordenadas precisas
  ✅ Monta query "Rua X, 307, Cidade, Estado, Brasil"
  ✅ Fallback: tenta só rua sem número se não achar com número
  ✅ Fallback 2: centroide do CEP como último recurso (marcado como impreciso)
  ✅ Salva endereco_completo com número no banco
"""

import requests
import time
import os
from dataclasses import dataclass
from typing import Optional

VIACEP_URL    = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

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
    
    Args:
        cep:    CEP sem hífen (8 dígitos)
        numero: Número da casa/estabelecimento (ex: "307")
    
    Returns:
        GeoResult com lat, lng, endereco | None se não encontrado
    """
    cep = cep.replace("-", "").strip()
    if len(cep) != 8 or not cep.isdigit():
        return None

    # Chave de cache: inclui número para coordenadas por endereço exato
    cache_key = f"{cep}_{numero}" if numero else cep

    # 1. Verifica cache
    cached = _get_cache(cache_key)
    if cached:
        return cached

    # 2. Busca dados do endereço no ViaCEP
    dados_cep = _viacep(cep)
    if not dados_cep:
        return None

    # 3. Tenta geocodificar com endereço completo (com número)
    resultado = _nominatim_full(dados_cep, numero)

    if resultado:
        _save_cache(cache_key, resultado)
        return resultado

    # 4. Fallback: geocodifica só a rua sem número
    resultado = _nominatim_full(dados_cep, numero="")
    if resultado:
        resultado.preciso = False  # marca como impreciso
        _save_cache(cache_key, resultado)
        return resultado

    # 5. Último fallback: centroide do CEP via Nominatim simples
    resultado = _nominatim_cep(cep, dados_cep)
    if resultado:
        resultado.preciso = False
        _save_cache(cache_key, resultado)
        return resultado

    return None


# ─── Internos ──────────────────────────────────────────────────────────

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


def _nominatim_full(dados_cep: dict, numero: str) -> Optional[GeoResult]:
    """
    Geocodifica usando endereço completo montado a partir dos dados do ViaCEP.
    Tenta formato estruturado (mais preciso) primeiro, depois free-form.
    """
    logradouro = dados_cep.get("logradouro", "").strip()
    bairro     = dados_cep.get("bairro", "").strip()
    cidade     = dados_cep.get("localidade", "").strip()
    estado     = dados_cep.get("uf", "").strip()

    if not logradouro or not cidade:
        return None

    _throttle_nominatim()

    # Monta a query com número se disponível
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
            display = results[0].get("display_name", query)
            # Monta endereço legível com número
            end_formatado = _formatar_endereco(logradouro, numero, bairro, cidade, estado)
            return GeoResult(lat=lat, lng=lon, endereco=end_formatado)
    except Exception:
        pass

    return None


def _nominatim_cep(cep: str, dados_cep: dict) -> Optional[GeoResult]:
    """Geocodifica pelo CEP diretamente (centroide — impreciso)."""
    _throttle_nominatim()

    cidade = dados_cep.get("localidade", "")
    estado = dados_cep.get("uf", "")
    logradouro = dados_cep.get("logradouro", "")
    bairro = dados_cep.get("bairro", "")

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


def _formatar_endereco(logradouro: str, numero: str, bairro: str,
                        cidade: str, estado: str) -> str:
    """Monta string de endereço legível para salvar no banco."""
    partes = []
    if logradouro:
        partes.append(logradouro)
        if numero:
            partes[-1] += f", {numero}"
    if bairro:
        partes.append(bairro)
    if cidade and estado:
        partes.append(f"{cidade} - {estado}")
    elif cidade:
        partes.append(cidade)
    return " · ".join(partes) if partes else logradouro or "Endereço desconhecido"


def _throttle_nominatim():
    """Garante no mínimo 1.1s entre chamadas ao Nominatim (política de uso)."""
    global _last_nominatim_call
    elapsed = time.time() - _last_nominatim_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _last_nominatim_call = time.time()


# ─── Cache ──────────────────────────────────────────────────────────────

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
                preciso=True  # se está em cache, aceita como válido
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
                   SET endereco = EXCLUDED.endereco,
                       lat      = EXCLUDED.lat,
                       lng      = EXCLUDED.lng,
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