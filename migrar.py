import os
import sqlite3
import sys

import psycopg2

SQLITE_PATH  = os.environ.get("SQLITE_PATH", "portotec.db")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    sys.exit("ERRO: defina a variável de ambiente DATABASE_URL antes de rodar.")
if not os.path.exists(SQLITE_PATH):
    sys.exit(f"ERRO: banco SQLite não encontrado em {SQLITE_PATH}")

TABELAS = [
    ("tecnicos", ["id", "nome", "cor", "created_at"]),
    ("fichas", ["id", "tecnico_id", "dia_semana", "data_referencia",
                "ponto_partida", "ponto_partida_cep", "ponto_partida_lat",
                "ponto_partida_lng", "distancia_total", "created_at", "updated_at"]),
    ("servicos", ["id", "ficha_id", "cep", "numero", "endereco_completo",
                  "lat", "lng", "cliente", "descricao", "ordem"]),
    ("cache_geo", ["cep", "endereco", "lat", "lng"]),
]


def main():
    sqlite = sqlite3.connect(SQLITE_PATH)
    sqlite.row_factory = sqlite3.Row

    pg = psycopg2.connect(DATABASE_URL)
    cur = pg.cursor()

    try:
        for tabela, colunas in TABELAS:
            print(f"Migrando {tabela}...")
            linhas = sqlite.execute(f"SELECT * FROM {tabela}").fetchall()

            campos = ", ".join(colunas)
            marcadores = ", ".join(["%s"] * len(colunas))
            sql = f"INSERT INTO {tabela} ({campos}) VALUES ({marcadores}) ON CONFLICT DO NOTHING"

            for linha in linhas:
                cur.execute(sql, tuple(linha[c] for c in colunas))

            print(f"  {len(linhas)} registros")

        print("Sincronizando sequences...")
        for tabela in ("tecnicos", "fichas", "servicos"):
            cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{tabela}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {tabela}), 0) + 1,
                    false
                )
            """)
            print(f"  {tabela}: OK")

        pg.commit()
        print("\nMigração concluída com sucesso.")

    except Exception as exc:
        pg.rollback()
        print(f"\nERRO — nada foi gravado: {exc}")
        raise
    finally:
        cur.close()
        pg.close()
        sqlite.close()


if __name__ == "__main__":
    main()