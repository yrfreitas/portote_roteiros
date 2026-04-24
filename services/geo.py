import urllib.request
import urllib.parse
import urllib.error
import json
import time
from database import get_db

def geocode_cep(cep: str):
    cep_clean = cep.replace("-", "").strip()

    conn = get_db()
    cached = conn.execute(
        "SELECT * FROM cache_geo WHERE cep = ?", (cep_clean,)
    ).fetchone()
    conn.close()

    if cached:
        print(f"[GEO] CEP {cep_clean} encontrado no cache")
        return {
            "cep": cep_clean,
            "endereco": cached["endereco"],
            "lat": cached["lat"],
            "lng": cached["lng"]
        }

    try:
        # PASSO 1: ViaCEP
        print(f"[GEO] Buscando CEP {cep_clean} no ViaCEP...")
        viacep_url = f"https://viacep.com.br/ws/{cep_clean}/json/"
        req_via = urllib.request.Request(
            viacep_url,
            headers={"User-Agent": "PortotecRoteiros/1.0"}
        )
        with urllib.request.urlopen(req_via, timeout=5) as resp:
            via_data = json.loads(resp.read().decode())

        if "erro" in via_data:
            print(f"[ERRO GEO] CEP {cep_clean} não encontrado no ViaCEP")
            return None

        cidade     = via_data.get("localidade", "")
        uf         = via_data.get("uf", "")
        logradouro = via_data.get("logradouro", "")
        bairro     = via_data.get("bairro", "")

        print(f"[GEO] ViaCEP OK: {logradouro}, {bairro}, {cidade}, {uf}")

        # PASSO 2: Nominatim com tentativas
        tentativas = []
        if logradouro:
            tentativas.append(f"{logradouro}, {bairro}, {cidade}, {uf}, Brasil")
            tentativas.append(f"{logradouro}, {cidade}, {uf}, Brasil")
        if bairro:
            tentativas.append(f"{bairro}, {cidade}, {uf}, Brasil")
        tentativas.append(f"{cidade}, {uf}, Brasil")

        lat, lng, endereco = None, None, None

        for i, query_str in enumerate(tentativas):
            print(f"[GEO] Tentativa {i+1}: {query_str}")
            query = urllib.parse.quote(query_str)
            url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1&countrycodes=br"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "PortotecRoteiros/1.0"}
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                time.sleep(1.1)

                if data:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    endereco = data[0].get("display_name", query_str)
                    print(f"[GEO] Encontrado: {lat}, {lng}")
                    break
                else:
                    print(f"[GEO] Tentativa {i+1} sem resultado")
            except Exception as e:
                print(f"[GEO] Tentativa {i+1} falhou: {e}")
                continue

        if lat is None:
            print(f"[ERRO GEO] Nenhuma tentativa funcionou para CEP {cep_clean}")
            return None

        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO cache_geo (cep, endereco, lat, lng) VALUES (?, ?, ?, ?)",
            (cep_clean, endereco, lat, lng)
        )
        conn.commit()
        conn.close()

        return {"cep": cep_clean, "endereco": endereco, "lat": lat, "lng": lng}

    except Exception as e:
        print(f"[ERRO GEO] CEP {cep_clean}: {e}")
        return None