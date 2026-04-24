from database import get_db

conn = get_db()
try:
    conn.execute("ALTER TABLE servicos ADD COLUMN numero TEXT DEFAULT ''")
    conn.commit()
    print("Coluna adicionada com sucesso!")
except Exception as e:
    print("Erro:", e)
conn.close()