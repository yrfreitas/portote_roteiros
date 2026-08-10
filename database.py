import os
import sqlite3
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_PG = bool(DATABASE_URL)

SQLITE_PATH = os.environ.get(
    "SQLITE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "portotec.db"),
)


def _connect():
    if IS_PG:
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=10,
        )

    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db():
    return _connect()


@contextmanager
def db_conn(commit: bool = False):
    conn = _connect()
    try:
        yield conn
        if commit:
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def sql(query: str) -> str:
    return query.replace("?", "%s") if IS_PG else query


def fetch_all(conn, query: str, params=()) -> list:
    cur = conn.cursor()
    try:
        cur.execute(sql(query), params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()


def fetch_one(conn, query: str, params=()):
    cur = conn.cursor()
    try:
        cur.execute(sql(query), params)
        row = cur.fetchone()
        return dict(row) if row is not None else None
    finally:
        cur.close()


def execute(conn, query: str, params=()) -> int:
    cur = conn.cursor()
    try:
        cur.execute(sql(query), params)
        return cur.rowcount
    finally:
        cur.close()


def insert_returning_id(conn, query: str, params=()):
    cur = conn.cursor()
    try:
        if IS_PG:
            cur.execute(sql(query) + " RETURNING id", params)
            return cur.fetchone()["id"]
        cur.execute(sql(query), params)
        return cur.lastrowid
    finally:
        cur.close()


_SCHEMA_PG = [
    """CREATE TABLE IF NOT EXISTS tecnicos (
        id          SERIAL PRIMARY KEY,
        nome        TEXT NOT NULL,
        cor         TEXT DEFAULT '#1a6fd4',
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS fichas (
        id                 SERIAL PRIMARY KEY,
        tecnico_id         INTEGER REFERENCES tecnicos(id) ON DELETE CASCADE,
        dia_semana         TEXT NOT NULL,
        data_referencia    TEXT,
        ponto_partida      TEXT,
        ponto_partida_cep  TEXT,
        ponto_partida_lat  DOUBLE PRECISION,
        ponto_partida_lng  DOUBLE PRECISION,
        distancia_total    DOUBLE PRECISION DEFAULT 0,
        created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at         TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS servicos (
        id                 SERIAL PRIMARY KEY,
        ficha_id           INTEGER NOT NULL REFERENCES fichas(id) ON DELETE CASCADE,
        cep                TEXT NOT NULL,
        numero             TEXT DEFAULT '',
        endereco_completo  TEXT,
        lat                DOUBLE PRECISION,
        lng                DOUBLE PRECISION,
        cliente            TEXT,
        descricao          TEXT,
        ordem              INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS cache_geo (
        cep         TEXT PRIMARY KEY,
        endereco    TEXT,
        lat         DOUBLE PRECISION,
        lng         DOUBLE PRECISION,
        preciso     BOOLEAN DEFAULT TRUE,
        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
]

_SCHEMA_SQLITE = """
    CREATE TABLE IF NOT EXISTS tecnicos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nome        TEXT NOT NULL,
        cor         TEXT DEFAULT '#1a6fd4',
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS fichas (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        tecnico_id         INTEGER,
        dia_semana         TEXT NOT NULL,
        data_referencia    TEXT,
        ponto_partida      TEXT,
        ponto_partida_cep  TEXT,
        ponto_partida_lat  REAL,
        ponto_partida_lng  REAL,
        distancia_total    REAL DEFAULT 0,
        created_at         TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at         TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS servicos (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        ficha_id           INTEGER NOT NULL,
        cep                TEXT NOT NULL,
        numero             TEXT DEFAULT '',
        endereco_completo  TEXT,
        lat                REAL,
        lng                REAL,
        cliente            TEXT,
        descricao          TEXT,
        ordem              INTEGER DEFAULT 0,
        FOREIGN KEY (ficha_id) REFERENCES fichas(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS cache_geo (
        cep         TEXT PRIMARY KEY,
        endereco    TEXT,
        lat         REAL,
        lng         REAL,
        preciso     INTEGER DEFAULT 1,
        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );
"""

_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_servicos_ficha   ON servicos(ficha_id)",
    "CREATE INDEX IF NOT EXISTS idx_servicos_ordem   ON servicos(ficha_id, ordem)",
    "CREATE INDEX IF NOT EXISTS idx_fichas_tecnico   ON fichas(tecnico_id)",
]

_MIGRACOES_PG = [
    "ALTER TABLE fichas   ALTER COLUMN ponto_partida_lat TYPE DOUBLE PRECISION",
    "ALTER TABLE fichas   ALTER COLUMN ponto_partida_lng TYPE DOUBLE PRECISION",
    "ALTER TABLE fichas   ALTER COLUMN distancia_total   TYPE DOUBLE PRECISION",
    "ALTER TABLE servicos ALTER COLUMN lat TYPE DOUBLE PRECISION",
    "ALTER TABLE servicos ALTER COLUMN lng TYPE DOUBLE PRECISION",
    "ALTER TABLE cache_geo ALTER COLUMN lat TYPE DOUBLE PRECISION",
    "ALTER TABLE cache_geo ALTER COLUMN lng TYPE DOUBLE PRECISION",
    "ALTER TABLE cache_geo ADD COLUMN IF NOT EXISTS preciso BOOLEAN DEFAULT TRUE",
    "ALTER TABLE servicos ADD COLUMN IF NOT EXISTS tipo_aparelho TEXT",
    "ALTER TABLE servicos ADD COLUMN IF NOT EXISTS modelo TEXT",
]

_MIGRACOES_SQLITE = [
    "ALTER TABLE cache_geo ADD COLUMN preciso INTEGER DEFAULT 1",
    "ALTER TABLE servicos ADD COLUMN tipo_aparelho TEXT",
    "ALTER TABLE servicos ADD COLUMN modelo TEXT",
]


def sincronizar_sequences(conn):
    if not IS_PG:
        return

    for tabela in ("tecnicos", "fichas", "servicos"):
        try:
            execute(conn, f"""
                SELECT setval(
                    pg_get_serial_sequence('{tabela}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {tabela}), 0) + 1,
                    false
                )
            """)
        except Exception:
            conn.rollback()


def init_db():
    with db_conn(commit=True) as conn:
        if IS_PG:
            for ddl in _SCHEMA_PG:
                execute(conn, ddl)
            conn.commit()

            for ddl in _MIGRACOES_PG:
                try:
                    execute(conn, ddl)
                    conn.commit()
                except Exception:
                    conn.rollback()
        else:
            conn.executescript(_SCHEMA_SQLITE)
            for ddl in _MIGRACOES_SQLITE:
                try:
                    conn.execute(ddl)
                except Exception:
                    pass

        for ddl in _INDICES:
            try:
                execute(conn, ddl)
                conn.commit()
            except Exception:
                conn.rollback()

        sincronizar_sequences(conn)