import sqlite3
import psycopg2

SQLITE_PATH = r"C:\Coisas Kalebe\SiteRoteiro\portotec.db"
DATABASE_URL = "postgresql://postgres:cbwqaIvrVwwwuJRIdyiMEMHdpMVgeuHO@gondola.proxy.rlwy.net:16791/railway"

sqlite = sqlite3.connect(SQLITE_PATH)
sqlite.row_factory = sqlite3.Row

pg = psycopg2.connect(DATABASE_URL)
cur = pg.cursor()

print("Migrando tecnicos...")
tecnicos = sqlite.execute("SELECT * FROM tecnicos").fetchall()
for t in tecnicos:
    cur.execute(
        "INSERT INTO tecnicos (id, nome, cor, created_at) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (t["id"], t["nome"], t["cor"], t["created_at"])
    )
print(f"{len(tecnicos)} tecnicos migrados")

print("Migrando fichas...")
fichas = sqlite.execute("SELECT * FROM fichas").fetchall()
for f in fichas:
    cur.execute(
        "INSERT INTO fichas (id, tecnico_id, dia_semana, data_referencia, ponto_partida, ponto_partida_cep, ponto_partida_lat, ponto_partida_lng, distancia_total, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (f["id"], f["tecnico_id"], f["dia_semana"], f["data_referencia"], f["ponto_partida"], f["ponto_partida_cep"], f["ponto_partida_lat"], f["ponto_partida_lng"], f["distancia_total"], f["created_at"], f["updated_at"])
    )
print(f"{len(fichas)} fichas migradas")

print("Migrando servicos...")
servicos = sqlite.execute("SELECT * FROM servicos").fetchall()
for s in servicos:
    cur.execute(
        "INSERT INTO servicos (id, ficha_id, cep, numero, endereco_completo, lat, lng, cliente, descricao, ordem) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (s["id"], s["ficha_id"], s["cep"], s["numero"], s["endereco_completo"], s["lat"], s["lng"], s["cliente"], s["descricao"], s["ordem"])
    )
print(f"{len(servicos)} servicos migrados")

print("Migrando cache_geo...")
cache = sqlite.execute("SELECT * FROM cache_geo").fetchall()
for c in cache:
    cur.execute(
        "INSERT INTO cache_geo (cep, endereco, lat, lng) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (c["cep"], c["endereco"], c["lat"], c["lng"])
    )
print(f"{len(cache)} caches migrados")

pg.commit()
cur.close()
pg.close()
sqlite.close()
print("Migração concluída!")