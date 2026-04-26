import os
import sqlite3
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        conn = sqlite3.connect("portotec.db")
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    if DATABASE_URL:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tecnicos (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cor TEXT DEFAULT '#1a6fd4',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fichas (
                id SERIAL PRIMARY KEY,
                tecnico_id INTEGER,
                dia_semana TEXT NOT NULL,
                data_referencia TEXT,
                ponto_partida TEXT,
                ponto_partida_cep TEXT,
                ponto_partida_lat REAL,
                ponto_partida_lng REAL,
                distancia_total REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS servicos (
                id SERIAL PRIMARY KEY,
                ficha_id INTEGER NOT NULL,
                cep TEXT NOT NULL,
                numero TEXT DEFAULT '',
                endereco_completo TEXT,
                lat REAL,
                lng REAL,
                cliente TEXT,
                descricao TEXT,
                ordem INTEGER DEFAULT 0,
                FOREIGN KEY (ficha_id) REFERENCES fichas(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cache_geo (
                cep TEXT PRIMARY KEY,
                endereco TEXT,
                lat REAL,
                lng REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    else:
        conn = sqlite3.connect("portotec.db")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tecnicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cor TEXT DEFAULT '#1a6fd4',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS fichas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tecnico_id INTEGER,
                dia_semana TEXT NOT NULL,
                data_referencia TEXT,
                ponto_partida TEXT,
                ponto_partida_cep TEXT,
                ponto_partida_lat REAL,
                ponto_partida_lng REAL,
                distancia_total REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ficha_id INTEGER NOT NULL,
                cep TEXT NOT NULL,
                numero TEXT DEFAULT '',
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