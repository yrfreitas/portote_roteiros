import urllib.request
import urllib.parse
import urllib.error
import json
import time
import re
import logging
from dataclasses import dataclass
from contextlib import contextmanager
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import os

from database import get_db

log = logging.getLogger("geo")

VIACEP_URL      = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL   = "https://nominatim.openstreetmap.org/search"
USER_AGENT      = "PortotecRoteiros/2.0 (contato@portotec.com)"
NOMINATIM_DELAY = 1.1
HTTP_TIMEOUT    = 5
MAX_TOTAL_TIME  = 20  # segundos máximos no total antes de desistir
PG = bool(os.environ.get("DATABASE_URL"))


@dataclass(frozen=True)
class GeoResult:
    cep:      str
    endereco: str
    lat:      float
    lng:      float

    def to_dict(self):
        return {"cep": self.cep, "endereco": self.endereco,
                "lat": self.lat, "lng": self.lng}

    def __getitem__(self, key):
        return self.to_dict()[key]

    def __contains__(self, key):
        return key in self.to_dict()


def _validate_cep(cep: str) -> str:
    clean = re.sub(r"\D", "", cep)
    if len(clean) != 8:
        raise ValueError(f"CEP inválido: '{cep}'")
    return clean


@contextmanager
def _db():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def _get_json(url: str, timeout: int = HTTP_TIMEOUT) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        log.warning("HTTP %d em %s", e.code, url)
    except urllib.error.URLError as e:
        log.warning("URL error em %s: %s", url, e.reason)
    except Exception as e:
        log.warning("Erro inesperado em %s: %s", url, e)
    return None


def _cache_get(cep_clean: str) -> Optional[GeoResult]:
    with _db() as conn:
        if PG:
            row = conn.execute(
                "SELECT endereco, lat, lng FROM cache_geo WHERE cep = %s",
                (cep_clean,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT endereco, lat, lng FROM cache_geo WHERE cep = ?",
                (cep_clean,)
            ).fetchone()

    if not row:
        return None

    return GeoResult(
        cep=cep_clean,
        endereco=row["endereco"] if PG else row[0],
        lat=row["lat"] if PG else row[1],
        lng=row["lng"] if PG else row[2]
    )


def _cache_set(result: GeoResult) -> None:
    with _db() as conn:
        if PG:
            conn.execute(
                """INSERT INTO cache_geo (cep, endereco, lat, lng)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (cep) DO UPDATE
                   SET endereco=%s, lat=%s, lng=%s""",
                (result.cep, result.endereco, result.lat, result.lng,
                 result.endereco, result.lat, result.lng)
            )
        else:
            conn.execute(
                "INSERT OR REPLACE INTO cache_geo (cep, endereco, lat, lng) VALUES (?, ?, ?, ?)",
                (result.cep, result.endereco, result.lat, result.lng)
            )
        conn.commit()


def _fetch_viacep(cep_clean: str) -> Optional[dict]:
    data = _get_json(VIACEP_URL.format(cep=cep_clean))
    if not data or "erro" in data:
        log.warning("ViaCEP não encontrou CEP %s", cep_clean)
        return None
    log.info("ViaCEP OK: %s - %s/%s", cep_clean,
             data.get("localidade"), data.get("uf"))
    return data


def _build_queries(via: dict) -> list:
    logr = via.get("logradouro", "").strip()
    bai  = via.get("bairro", "").strip()
    cid  = via.get("localidade", "").strip()
    uf   = via.get("uf", "").strip()

    candidates = []
    if logr and bai and cid:
        candidates.append(f"{logr}, {bai}, {cid}, {uf}, Brasil")
    if logr and cid:
        candidates.append(f"{logr}, {cid}, {uf}, Brasil")
    if bai and cid:
        candidates.append(f"{bai}, {cid}, {uf}, Brasil")
    if cid:
        candidates.append(f"{cid}, {uf}, Brasil")

    # Remove duplicatas mantendo ordem
    return list(dict.fromkeys(candidates))


def _geocode_nominatim(queries: list) -> Optional[tuple]:
    for i, q in enumerate(queries):
        params = urllib.parse.urlencode({
            "q": q,
            "format": "json",
            "limit": 1,
            "countrycodes": "br",
            "addressdetails": 1
        })
        data = _get_json(f"{NOMINATIM_URL}?{params}")

        if data:
            log.info("Nominatim achou na tentativa %d: %s", i + 1, q)
            return (
                float(data[0]["lat"]),
                float(data[0]["lon"]),
                data[0].get("display_name", q)
            )

        log.info("Nominatim tentativa %d sem resultado: %s", i + 1, q)

        # Só dorme entre tentativas, não após a última
        if i < len(queries) - 1:
            time.sleep(NOMINATIM_DELAY)

    return None


def _geocode_completo(cep_clean: str, via: dict) -> Optional[GeoResult]:
    queries = _build_queries(via)
    coords = _geocode_nominatim(queries)

    if not coords:
        log.error("Nominatim falhou para CEP %s após %d tentativas",
                  cep_clean, len(queries))
        return None

    lat, lng, endereco = coords
    result = GeoResult(cep=cep_clean, endereco=endereco, lat=lat, lng=lng)
    _cache_set(result)
    log.info("CEP %s geocodificado: %.6f, %.6f", cep_clean, lat, lng)
    return result


def geocode_cep(cep: str) -> Optional[GeoResult]:
    # 1. Valida
    try:
        cep_clean = _validate_cep(cep)
    except ValueError as e:
        log.error("%s", e)
        return None

    # 2. Cache
    cached = _cache_get(cep_clean)
    if cached:
        log.info("CEP %s retornado do cache", cep_clean)
        return cached

    # 3. ViaCEP
    via = _fetch_viacep(cep_clean)
    if via is None:
        return None

    # 4. Geocodifica com timeout total para não travar o servidor
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_geocode_completo, cep_clean, via)
            return future.result(timeout=MAX_TOTAL_TIME)
    except FuturesTimeout:
        log.error("Timeout total atingido para CEP %s", cep_clean)
        return None
    except Exception as e:
        log.error("Erro inesperado geocodificando CEP %s: %s", cep_clean, e)
        return None