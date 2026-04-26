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
import os

from database import get_db

log = logging.getLogger("geo")

VIACEP_URL      = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL   = "https://nominatim.openstreetmap.org/search"
USER_AGENT      = "PortotecRoteiros/2.0 (contato@portotec.com)"
NOMINATIM_DELAY = 1.1
HTTP_TIMEOUT    = 8
PG = bool(os.environ.get("DATABASE_URL"))


@dataclass(frozen=True)
class GeoResult:
    cep:      str
    endereco: str
    lat:      float
    lng:      float

    def to_dict(self):
        return {"cep": self.cep, "endereco": self.endereco, "lat": self.lat, "lng": self.lng}

    def __getitem__(self, key):
        return self.to_dict()[key]


def _validate_cep(cep):
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


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            log.warning("Erro em %s (tentativa %d/3): %s", url, attempt, e)
        if attempt < 3:
            time.sleep(2 ** attempt)
    return None


def _cache_get(cep_clean):
    with _db() as conn:
        cur = conn.cursor()
        if PG:
            cur.execute("SELECT endereco, lat, lng FROM cache_geo WHERE cep = %s", (cep_clean,))
        else:
            cur.execute("SELECT endereco, lat, lng FROM cache_geo WHERE cep = ?", (cep_clean,))
        row = cur.fetchone()
        cur.close()

    if row:
        if PG:
            return GeoResult(cep=cep_clean, endereco=row["endereco"], lat=row["lat"], lng=row["lng"])
        return GeoResult(cep=cep_clean, endereco=row[0], lat=row[1], lng=row[2])
    return None


def _cache_set(result):
    with _db() as conn:
        cur = conn.cursor()
        if PG:
            cur.execute(
                "INSERT INTO cache_geo (cep, endereco, lat, lng) VALUES (%s, %s, %s, %s) ON CONFLICT (cep) DO UPDATE SET endereco=%s, lat=%s, lng=%s",
                (result.cep, result.endereco, result.lat, result.lng, result.endereco, result.lat, result.lng)
            )
        else:
            cur.execute(
                "INSERT OR REPLACE INTO cache_geo (cep, endereco, lat, lng) VALUES (?, ?, ?, ?)",
                (result.cep, result.endereco, result.lat, result.lng)
            )
        conn.commit()
        cur.close()


def _fetch_viacep(cep_clean):
    data = _get_json(VIACEP_URL.format(cep=cep_clean))
    if not data or "erro" in data:
        return None
    return data


def _build_queries(via):
    logr = via.get("logradouro", "").strip()
    bai  = via.get("bairro", "").strip()
    cid  = via.get("localidade", "").strip()
    uf   = via.get("uf", "").strip()
    candidates = []
    if logr:
        candidates.append(f"{logr}, {bai}, {cid}, {uf}, Brasil")
        candidates.append(f"{logr}, {cid}, {uf}, Brasil")
    if bai:
        candidates.append(f"{bai}, {cid}, {uf}, Brasil")
    candidates.append(f"{cid}, {uf}, Brasil")
    return list(dict.fromkeys(candidates))


def _geocode_nominatim(queries):
    for i, q in enumerate(queries, 1):
        params = urllib.parse.urlencode({"q": q, "format": "json", "limit": 1, "countrycodes": "br"})
        data = _get_json(f"{NOMINATIM_URL}?{params}")
        if i < len(queries):
            time.sleep(NOMINATIM_DELAY)
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", q)
    return None


def geocode_cep(cep: str) -> Optional[GeoResult]:
    try:
        cep_clean = _validate_cep(cep)
    except ValueError as e:
        log.error("%s", e)
        return None

    cached = _cache_get(cep_clean)
    if cached:
        return cached

    via = _fetch_viacep(cep_clean)
    if via is None:
        return None

    coords = _geocode_nominatim(_build_queries(via))
    if coords is None:
        return None

    lat, lng, endereco = coords
    result = GeoResult(cep=cep_clean, endereco=endereco, lat=lat, lng=lng)
    _cache_set(result)
    return result