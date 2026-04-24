import sqlite3

DB_PATH = "portotec.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS fichas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_semana TEXT NOT NULL,
            data_referencia TEXT,
            ponto_partida TEXT,
            ponto_partida_cep TEXT,
            ponto_partida_lat REAL,
            ponto_partida_lng REAL,
            distancia_total REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ficha_id INTEGER NOT NULL,
            cep TEXT NOT NULL,
            endereco_completo TEXT,
            lat REAL,
            lng REAL,
            cliente TEXT,
            descricao TEXT,
            ordem INTEGER DEFAULT 0,
            FOREIGN KEY (ficha_id) REFERENCES fichas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cache_geo (
            cep TEXT PRIMARY KEY,
            endereco TEXT,
            lat REAL,
            lng REAL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()