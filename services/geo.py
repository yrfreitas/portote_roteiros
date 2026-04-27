import urllib.request
import urllib.error
import json
import re
import logging
from dataclasses import dataclass
from typing import Optional
import os

from database import get_db

log = logging.getLogger("geo")
VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
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


def geocode_cep(cep: str) -> Optional[GeoResult]:
    try:
        cep_clean = _validate_cep(cep)
    except ValueError as e:
        log.error("%s", e)
        return None

    try:
        req = urllib.request.Request(
            VIACEP_URL.format(cep=cep_clean),
            headers={"User-Agent": "PortotecRoteiros/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        log.error("Erro ao buscar CEP %s: %s", cep_clean, e)
        return None

    if not data or "erro" in data:
        log.warning("CEP %s não encontrado", cep_clean)
        return None

    logr = data.get("logradouro", "")
    bairro = data.get("bairro", "")
    cidade = data.get("localidade", "")
    uf = data.get("uf", "")
    endereco = f"{logr}, {bairro}, {cidade} - {uf}".strip(", ")

    return GeoResult(cep=cep_clean, endereco=endereco, lat=0.0, lng=0.0)