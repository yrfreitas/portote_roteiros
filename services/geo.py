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

from database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("geo")

VIACEP_URL      = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL   = "https://nominatim.openstreetmap.org/search"
USER_AGENT      = "PortotecRoteiros/2.0 (contato@portotec.com)"
NOMINATIM_DELAY = 1.1
HTTP_TIMEOUT    = 8

@dataclass(frozen=True)
class GeoResult:
    cep:      str
    endereco: str
    lat:      float
    lng:      float

    def to_dict(self) -> dict:
        return {"cep": self.cep, "endereco": self.endereco,
                "lat": self.lat, "lng": self.lng}


def _validate_cep(cep: str) -> str:
    clean = re.sub(r"\D", "", cep)
    if len(clean) != 8:
        raise ValueError(f"CEP inválido: '{cep}' → '{clean}' ({len(clean)} dígitos)")
    return clean


@contextmanager
def _db():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def _get_json(url: str) -> Optional[dict | list]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            log.warning("HTTP %s em %s (tentativa %d/3)", e.code, url, attempt)
        except urllib.error.URLError as e:
            log.warning("Erro de rede em %s (tentativa %d/3): %s", url, attempt, e.reason)
        except Exception as e:
            log.warning("Erro inesperado em %s (tentativa %d/3): %s", url, attempt, e)

        if attempt < 3:
            time.sleep(2 ** attempt)

    return None


def _cache_get(cep_clean: str) -> Optional[GeoResult]:
    with _db() as conn:
        row = conn.execute(
            "SELECT endereco, lat, lng FROM cache_geo WHERE cep = ?", (cep_clean,)
        ).fetchone()

    if row:
        log.info("CEP %s encontrado no cache", cep_clean)
        return GeoResult(cep=cep_clean, endereco=row["endereco"],
                         lat=row["lat"], lng=row["lng"])
    return None


def _cache_set(result: GeoResult) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache_geo (cep, endereco, lat, lng) VALUES (?, ?, ?, ?)",
            (result.cep, result.endereco, result.lat, result.lng),
        )
        conn.commit()
    log.info("CEP %s salvo no cache", result.cep)


def _fetch_viacep(cep_clean: str) -> Optional[dict]:
    log.info("Consultando ViaCEP para %s…", cep_clean)
    data = _get_json(VIACEP_URL.format(cep=cep_clean))

    if not data or "erro" in data:
        log.error("CEP %s não encontrado no ViaCEP", cep_clean)
        return None

    log.info("ViaCEP OK → %s, %s, %s/%s",
             data.get("logradouro"), data.get("bairro"),
             data.get("localidade"), data.get("uf"))
    return data


def _build_queries(via: dict) -> list[str]:
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


def _geocode_nominatim(queries: list[str]) -> Optional[tuple[float, float, str]]:
    for i, q in enumerate(queries, 1):
        log.info("Nominatim tentativa %d/%d: %s", i, len(queries), q)

        params = urllib.parse.urlencode({
            "q": q,
            "format": "json",
            "limit": 1,
            "countrycodes": "br"
        })
        url  = f"{NOMINATIM_URL}?{params}"
        data = _get_json(url)

        if i < len(queries):
            time.sleep(NOMINATIM_DELAY)

        if data:
            item = data[0]
            lat  = float(item["lat"])
            lng  = float(item["lon"])
            end  = item.get("display_name", q)
            log.info("Nominatim encontrou: %.6f, %.6f", lat, lng)
            return lat, lng, end

        log.debug("Nominatim tentativa %d sem resultado", i)

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

    queries = _build_queries(via)
    coords  = _geocode_nominatim(queries)

    if coords is None:
        log.error("Nenhuma tentativa funcionou para CEP %s", cep_clean)
        return None

    lat, lng, endereco = coords
    result = GeoResult(cep=cep_clean, endereco=endereco, lat=lat, lng=lng)
    _cache_set(result)
    return result