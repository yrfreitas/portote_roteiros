import urllib.request
import urllib.error
import urllib.parse
import json
import re
import logging
import time
from dataclasses import dataclass
from typing import Optional
import os

from database import get_db

log = logging.getLogger("geo")

VIACEP_URL    = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

PG = bool(os.environ.get("DATABASE_URL"))
PH = "%s" if PG else "?"


@dataclass(frozen=True)
class GeoResult:
    cep:      str
    endereco: str
    bairro:   str
    cidade:   str
    uf:       str
    lat:      float
    lng:      float

    def to_dict(self):
        return {
            "cep":      self.cep,
            "endereco": self.endereco,
            "bairro":   self.bairro,
            "cidade":   self.cidade,
            "uf":       self.uf,
            "lat":      self.lat,
            "lng":      self.lng,
        }

    def __getitem__(self, key):
        return self.to_dict()[key]

    def __contains__(self, key):
        return key in self.to_dict()


def _validate_cep(cep: str) -> str:
    clean = re.sub(r"\D", "", cep)
    if len(clean) != 8:
        raise ValueError(f"CEP inválido: '{cep}'")
    return clean


def _cache_get(cep_clean: str) -> Optional[GeoResult]:
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            f"SELECT endereco, lat, lng FROM cache_geo WHERE cep = {PH}",
            (cep_clean,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return None

        endereco = row[0] if PG else row["endereco"]
        lat      = row[1] if PG else row["lat"]
        lng      = row[2] if PG else row["lng"]

        # Se estava no cache mas sem coordenadas, ignora e busca de novo
        if not lat or not lng or (lat == 0.0 and lng == 0.0):
            return None

        return GeoResult(
            cep=cep_clean,
            endereco=endereco,
            bairro="",
            cidade="",
            uf="",
            lat=float(lat),
            lng=float(lng),
        )
    except Exception as e:
        log.warning("Erro ao buscar cache para CEP %s: %s", cep_clean, e)
        return None


def _cache_set(result: GeoResult) -> None:
    try:
        conn = get_db()
        cur  = conn.cursor()
        if PG:
            cur.execute(
                """INSERT INTO cache_geo (cep, endereco, lat, lng)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (cep) DO UPDATE
                   SET endereco = EXCLUDED.endereco,
                       lat      = EXCLUDED.lat,
                       lng      = EXCLUDED.lng""",
                (result.cep, result.endereco, result.lat, result.lng)
            )
        else:
            cur.execute(
                "INSERT OR REPLACE INTO cache_geo (cep, endereco, lat, lng) VALUES (?, ?, ?, ?)",
                (result.cep, result.endereco, result.lat, result.lng)
            )
        conn.commit()
        cur.close()
        conn.close()
        log.info("CEP %s salvo no cache (lat=%.6f, lng=%.6f)", result.cep, result.lat, result.lng)
    except Exception as e:
        log.warning("Erro ao salvar cache para CEP %s: %s", result.cep, e)


def _fetch_viacep(cep_clean: str, tentativas: int = 3) -> Optional[dict]:
    url = VIACEP_URL.format(cep=cep_clean)

    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "PortotecRoteiros/2.0 (contato@portotec.com)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if not data or "erro" in data:
                log.warning("ViaCEP: CEP %s não encontrado", cep_clean)
                return None

            return data

        except urllib.error.HTTPError as e:
            log.warning("ViaCEP HTTP %d para CEP %s (tentativa %d/%d)",
                        e.code, cep_clean, tentativa, tentativas)
        except urllib.error.URLError as e:
            log.warning("ViaCEP indisponível: %s (tentativa %d/%d)",
                        e.reason, tentativa, tentativas)
        except Exception as e:
            log.warning("Erro ViaCEP: %s (tentativa %d/%d)", e, tentativa, tentativas)

        if tentativa < tentativas:
            time.sleep(1.5 * tentativa)

    return None


def _fetch_nominatim(endereco: str, cidade: str, uf: str) -> tuple[float, float]:
    """
    Chama o Nominatim para transformar endereço em lat/lng.
    Retorna (lat, lng) ou (0.0, 0.0) se não encontrar.
    """
    # Monta query: "Rua X, Bairro Y, Cidade - UF, Brasil"
    query = f"{endereco}, {cidade} - {uf}, Brasil"

    params = urllib.parse.urlencode({
        "q":              query,
        "format":         "json",
        "limit":          1,
        "countrycodes":   "br",
        "addressdetails": 0,
    })

    url = f"{NOMINATIM_URL}?{params}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                # Nominatim exige User-Agent identificando seu app
                "User-Agent": "PortotecRoteiros/2.0 (contato@portotec.com)"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read().decode())

        if results:
            lat = float(results[0]["lat"])
            lng = float(results[0]["lon"])
            log.info("Nominatim OK: %s → (%.6f, %.6f)", query, lat, lng)
            return lat, lng

        log.warning("Nominatim: nenhum resultado para '%s'", query)
        return 0.0, 0.0

    except Exception as e:
        log.warning("Erro Nominatim para '%s': %s", query, e)
        return 0.0, 0.0


def _formatar_endereco(data: dict) -> str:
    partes = []
    logr   = data.get("logradouro", "").strip()
    bairro = data.get("bairro",     "").strip()
    cidade = data.get("localidade", "").strip()
    uf     = data.get("uf",         "").strip()

    if logr:   partes.append(logr)
    if bairro: partes.append(bairro)
    if cidade and uf:
        partes.append(f"{cidade} - {uf}")
    elif cidade:
        partes.append(cidade)

    return ", ".join(partes) if partes else "Endereço não encontrado"


def geocode_cep(cep: str) -> Optional[GeoResult]:
    """
    1. Valida o CEP
    2. Checa cache (com lat/lng válidos)
    3. Busca endereço no ViaCEP
    4. Geocodifica com Nominatim → lat/lng reais
    5. Salva no cache e retorna
    """
    try:
        cep_clean = _validate_cep(cep)
    except ValueError as e:
        log.error("%s", e)
        return None

    cached = _cache_get(cep_clean)
    if cached:
        log.info("CEP %s retornado do cache", cep_clean)
        return cached

    # Passo 1: pega endereço
    data = _fetch_viacep(cep_clean)
    if data is None:
        return None

    endereco = _formatar_endereco(data)
    bairro   = data.get("bairro",     "").strip()
    cidade   = data.get("localidade", "").strip()
    uf       = data.get("uf",         "").strip()

    # Passo 2: geocodifica — espera 1s para respeitar o limite do Nominatim
    time.sleep(1)
    lat, lng = _fetch_nominatim(endereco, cidade, uf)

    result = GeoResult(
        cep=cep_clean,
        endereco=endereco,
        bairro=bairro,
        cidade=cidade,
        uf=uf,
        lat=lat,
        lng=lng,
    )

    _cache_set(result)
    return result