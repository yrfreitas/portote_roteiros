import urllib.request
import urllib.error
import json
import re
import logging
import time
from dataclasses import dataclass
from typing import Optional
import os

from database import get_db

log = logging.getLogger("geo")

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
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
    """Busca CEP no cache do banco de dados."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            f"SELECT endereco, lat, lng FROM cache_geo WHERE cep = {PH}",
            (cep_clean,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return None

        # Tenta extrair bairro/cidade/uf do endereço salvo
        endereco = row[0] if PG else row["endereco"]
        return GeoResult(
            cep=cep_clean,
            endereco=endereco,
            bairro="",
            cidade="",
            uf="",
            lat=0.0,
            lng=0.0,
        )
    except Exception as e:
        log.warning("Erro ao buscar cache para CEP %s: %s", cep_clean, e)
        return None


def _cache_set(result: GeoResult) -> None:
    """Salva resultado no cache do banco de dados."""
    try:
        conn = get_db()
        cur = conn.cursor()
        if PG:
            cur.execute(
                """INSERT INTO cache_geo (cep, endereco, lat, lng)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (cep) DO UPDATE
                   SET endereco = EXCLUDED.endereco""",
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
        log.info("CEP %s salvo no cache", result.cep)
    except Exception as e:
        log.warning("Erro ao salvar cache para CEP %s: %s", result.cep, e)


def _fetch_viacep(cep_clean: str, tentativas: int = 3) -> Optional[dict]:
    """Busca dados do CEP na API ViaCEP com retry automático."""
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

            log.info("ViaCEP OK: %s - %s/%s",
                     cep_clean, data.get("localidade"), data.get("uf"))
            return data

        except urllib.error.HTTPError as e:
            log.warning("ViaCEP HTTP %d para CEP %s (tentativa %d/%d)",
                        e.code, cep_clean, tentativa, tentativas)
        except urllib.error.URLError as e:
            log.warning("ViaCEP indisponível para CEP %s: %s (tentativa %d/%d)",
                        cep_clean, e.reason, tentativa, tentativas)
        except Exception as e:
            log.warning("Erro inesperado ViaCEP CEP %s: %s (tentativa %d/%d)",
                        cep_clean, e, tentativa, tentativas)

        if tentativa < tentativas:
            time.sleep(1.5 * tentativa)  # backoff: 1.5s, 3s

    log.error("ViaCEP falhou após %d tentativas para CEP %s", tentativas, cep_clean)
    return None


def _formatar_endereco(data: dict) -> str:
    """Monta string de endereço limpa a partir dos dados do ViaCEP."""
    partes = []

    logr = data.get("logradouro", "").strip()
    bairro = data.get("bairro", "").strip()
    cidade = data.get("localidade", "").strip()
    uf = data.get("uf", "").strip()

    if logr:
        partes.append(logr)
    if bairro:
        partes.append(bairro)
    if cidade and uf:
        partes.append(f"{cidade} - {uf}")
    elif cidade:
        partes.append(cidade)

    return ", ".join(partes) if partes else "Endereço não encontrado"


def geocode_cep(cep: str) -> Optional[GeoResult]:
    """
    Busca endereço pelo CEP usando ViaCEP.
    Usa cache no banco para evitar requisições repetidas.
    Retorna GeoResult com lat/lng zerados (sem geocodificação).
    """
    try:
        cep_clean = _validate_cep(cep)
    except ValueError as e:
        log.error("%s", e)
        return None

    # Verifica cache primeiro
    cached = _cache_get(cep_clean)
    if cached:
        log.info("CEP %s retornado do cache", cep_clean)
        return cached

    # Busca no ViaCEP
    data = _fetch_viacep(cep_clean)
    if data is None:
        return None

    endereco = _formatar_endereco(data)
    bairro = data.get("bairro", "").strip()
    cidade = data.get("localidade", "").strip()
    uf = data.get("uf", "").strip()

    result = GeoResult(
        cep=cep_clean,
        endereco=endereco,
        bairro=bairro,
        cidade=cidade,
        uf=uf,
        lat=0.0,
        lng=0.0,
    )

    _cache_set(result)
    return result