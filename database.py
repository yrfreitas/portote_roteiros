import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import psycopg2.pool

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_PG = bool(DATABASE_URL)

SQLITE_PATH = os.environ.get(
    "SQLITE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "portotec.db"),
)


# POOL DE CONEXÕES.
#
# Antes, cada requisição abria uma conexão nova com o Postgres do Railway —
# e abrir conexão com banco remoto custa MAIS que a consulta em si (handshake
# TCP + TLS + autenticação). Com o painel pedindo de 10 em 10 segundos, dois
# técnicos em campo e o rastreador enviando posição, isso virou a maior parte
# do tempo de resposta: em 2026-08-17 o /api/versao, que lê UMA linha e
# devolve 0,1 KB, levava 5 segundos.
#
# maxconn=10 casa com o Procfile (`--threads 8`) e sobra folga para as duas
# conexões que algumas rotas abrem em sequência. Mais que isso só ocuparia
# slot no servidor de banco sem ninguém para usar.
_pool = None

if IS_PG:
    try:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10, DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=10,
        )
    except Exception:
        # Sem pool o sistema continua funcionando, só mais devagar. Preferível
        # a não subir de jeito nenhum por causa de uma otimização.
        _pool = None


def _connect():
    if IS_PG:
        if _pool is not None:
            conn = _pool.getconn()
            # Conexão reaproveitada pode voltar suja de uma transação abortada.
            # O rollback aqui garante que quem pega recebe folha limpa.
            try:
                conn.rollback()
            except Exception:
                pass
            return conn
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
        # Com pool, "fechar" é DEVOLVER: fechar de verdade jogaria fora a
        # conexão que acabamos de pagar para abrir, e o pool ficaria inútil.
        try:
            if IS_PG and _pool is not None:
                _pool.putconn(conn)
            else:
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
    """CREATE TABLE IF NOT EXISTS setores (
        id         SERIAL PRIMARY KEY,
        nome       TEXT NOT NULL,
        cor        TEXT DEFAULT '#4f8dfb',
        ativo      BOOLEAN DEFAULT TRUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS tecnicos (
        id          SERIAL PRIMARY KEY,
        nome        TEXT NOT NULL,
        cor         TEXT DEFAULT '#1a6fd4',
        token       TEXT,
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
        status             TEXT DEFAULT 'pendente',
        concluida_em       TEXT,
        conciliada_em      TEXT,
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
        ordem              INTEGER DEFAULT 0,
        status             TEXT DEFAULT 'pendente',
        concluido_em       TEXT,
        numero_os          TEXT,
        setor_id           INTEGER REFERENCES setores(id) ON DELETE SET NULL
    )""",
    """CREATE TABLE IF NOT EXISTS cache_geo (
        cep         TEXT PRIMARY KEY,
        endereco    TEXT,
        lat         DOUBLE PRECISION,
        lng         DOUBLE PRECISION,
        preciso     BOOLEAN DEFAULT TRUE,
        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS push_subscriptions (
        id          SERIAL PRIMARY KEY,
        tecnico_id  INTEGER NOT NULL REFERENCES tecnicos(id) ON DELETE CASCADE,
        endpoint    TEXT NOT NULL,
        p256dh      TEXT NOT NULL,
        auth        TEXT NOT NULL,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    # Contador único que serve ao auto-refresh: uma linha só, incrementada a
    # cada escrita bem-sucedida na API. O front pergunta "mudou alguma coisa?"
    # comparando um inteiro, em vez de rebaixar dados inteiros a cada 10s.
    # O CHECK(id=1) é a trava que garante que existe uma linha e só uma.
    """CREATE TABLE IF NOT EXISTS meta_revisao (
        id            INTEGER PRIMARY KEY CHECK (id = 1),
        revisao       BIGINT NOT NULL DEFAULT 0,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    # Rastreio ao vivo: o cliente acompanha o técnico a caminho.
    # Guarda só a ÚLTIMA posição, não o histórico. Duas razões: o cliente quer
    # saber onde ele está agora, não por onde passou; e guardar trajeto de
    # funcionário é dado sensível que ninguém pediu para ter.
    """CREATE TABLE IF NOT EXISTS rastreios (
        id            SERIAL PRIMARY KEY,
        token         TEXT NOT NULL UNIQUE,
        servico_id    INTEGER NOT NULL REFERENCES servicos(id) ON DELETE CASCADE,
        tecnico_id    INTEGER NOT NULL REFERENCES tecnicos(id) ON DELETE CASCADE,
        lat           DOUBLE PRECISION,
        lng           DOUBLE PRECISION,
        ativo         BOOLEAN DEFAULT TRUE,
        criado_em     TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT,
        encerrado_em  TEXT,
        eta_minutos   INTEGER
    )""",
    # Peças lançadas na OS do AgoraOS. Existe por dois motivos, ambos sérios:
    #
    # 1. IDEMPOTÊNCIA. A API do AgoraOS não tem DELETE de item de OS — só POST
    #    e PUT. Um duplo clique ou um retry lançaria a mesma placa duas vezes
    #    e ninguém conseguiria desfazer pelo sistema. A UNIQUE em
    #    linha_planilha é a trava: a mesma linha da planilha só vai uma vez.
    # 2. AUDITORIA. Como não dá pra apagar pela API, quem precisar corrigir vai
    #    ter que abrir a OS no AgoraOS e remover na mão — e pra isso precisa
    #    saber exatamente qual item foi criado (id_item) e em qual OS.
    # O que o celular do técnico está REALMENTE rodando.
    #
    # Existe porque em 2026-08-14 eu passei três rodadas de deploy diagnosticando
    # por dedução: o app do Pedro parecia funcionar, o servidor tinha o código
    # certo, e nada indicava que o celular dele estava três versões atrás com o
    # GPS possivelmente negado. Sem enxergar o aparelho, todo diagnóstico vira
    # chute — e chute custou tempo do Kalebe e de um técnico em campo.
    #
    # Alimentado pelo ping de versão que o app já faz a cada 20s: zero
    # requisição nova. Uma linha por técnico, sobrescrita — é estado atual,
    # não histórico.
    """CREATE TABLE IF NOT EXISTS tecnico_status (
        tecnico_id   INTEGER PRIMARY KEY REFERENCES tecnicos(id) ON DELETE CASCADE,
        app_versao   TEXT,
        gps_estado   TEXT,
        gps_erro     TEXT,
        visto_em     TEXT
    )""",
    # Pessoas que entram no sistema, com o papel de cada uma.
    #
    # Até 2026-08-17 havia UMA senha de admin para todo mundo: o sistema sabia
    # que "alguém logado" agiu, nunca QUEM. Com dois técnicos em campo isso
    # deixou de servir — e o Kalebe pediu que o técnico não veja o diagnóstico
    # nem o resto do que é de desenvolvedor.
    #
    # `tecnico_id` liga a pessoa ao técnico das rotas, para o painel dele já
    # abrir no que é dele.
    """CREATE TABLE IF NOT EXISTS usuarios (
        id          SERIAL PRIMARY KEY,
        nome        TEXT NOT NULL,
        login       TEXT NOT NULL UNIQUE,
        senha_hash  TEXT NOT NULL,
        papel       TEXT NOT NULL DEFAULT 'tecnico',
        tecnico_id  INTEGER REFERENCES tecnicos(id) ON DELETE SET NULL,
        ativo       BOOLEAN DEFAULT TRUE,
        criado_em   TEXT DEFAULT CURRENT_TIMESTAMP,
        ultimo_acesso TEXT
    )""",
    # Mensagens do chat. Uma SALA por conversa: o token do rastreio quando é
    # com o cliente daquele atendimento, e 'equipe' para a conversa interna.
    # Assim o cliente só enxerga a própria conversa, sem precisar de conta.
    """CREATE TABLE IF NOT EXISTS mensagens (
        id         SERIAL PRIMARY KEY,
        sala       TEXT NOT NULL,
        autor_tipo TEXT NOT NULL,
        autor_nome TEXT,
        texto      TEXT NOT NULL,
        criado_em  TEXT,
        lida       BOOLEAN DEFAULT FALSE
    )""",
    # Erros que acontecem no NAVEGADOR de quem usa o sistema.
    #
    # Existe porque "o site fica dando erro toda hora" é impossível de
    # investigar do servidor: as rotas respondem 200 em 0,2s e o defeito mora
    # na tela de outra pessoa. Sem isto, todo diagnóstico de front vira
    # dedução — que neste projeto já custou várias rodadas de deploy.
    #
    # Guarda pouco e por pouco tempo: mensagem, origem e versão. Nada de dado
    # de cliente.
    """CREATE TABLE IF NOT EXISTS erros_cliente (
        id        SERIAL PRIMARY KEY,
        quando    TEXT,
        origem    TEXT,
        versao    TEXT,
        url       TEXT,
        mensagem  TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS pecas_agoraos (
        id                   SERIAL PRIMARY KEY,
        linha_planilha       INTEGER NOT NULL UNIQUE,
        id_os                INTEGER NOT NULL,
        id_produto_extensao  INTEGER NOT NULL,
        id_item              TEXT,
        cliente              TEXT,
        peca                 TEXT,
        qtd                  DOUBLE PRECISION DEFAULT 1,
        forca                TEXT,
        criado_em            TEXT DEFAULT CURRENT_TIMESTAMP
    )""",

    # Chegada FÍSICA da peça na bancada.
    #
    # A planilha acompanha a compra até "Enviado" — é o último estado que a
    # Panasonic informa. Mas quem precisa reagendar a visita não pergunta "foi
    # enviada?", pergunta "chegou?". Entre o envio e a peça na mão passam dias,
    # e esse intervalo não existia em lugar nenhum: ficava na cabeça de quem
    # recebeu a caixa.
    #
    # Fica em tabela própria, e não numa coluna da planilha, porque é
    # informação de dentro da oficina — a planilha é alimentada pelo robô a
    # partir dos e-mails da Panasonic, e escrever ali um dado que não vem
    # deles misturaria as duas origens.
    """CREATE TABLE IF NOT EXISTS pecas_chegada (
        chave        TEXT PRIMARY KEY,
        chegou_em    TEXT,
        observacao   TEXT,
        registrado_por TEXT
    )""",

    # O QUE ACONTECEU NO ATENDIMENTO.
    #
    # Até aqui o técnico só podia dizer "concluído" — e "concluído" tanto
    # significa "consertei" quanto "fui lá e o cliente não estava". São
    # desfechos opostos que exigem ações opostas, e a diferença ficava na
    # cabeça de quem foi.
    #
    # É campo ESCOLHIDO, não texto livre, de propósito: "troquei a placa"
    # digitado de dez maneiras não vira relatório, não filtra e não dispara
    # nada. Com opção fixa dá para contar quantos atendimentos pararam por
    # falta de peça no mês — que é a pergunta que ninguém consegue responder
    # hoje.
    """CREATE TABLE IF NOT EXISTS servico_desfecho (
        servico_id      INTEGER PRIMARY KEY,
        desfecho        TEXT NOT NULL,
        motivo          TEXT,
        peca            TEXT,
        registrado_em   TEXT,
        registrado_por  TEXT
    )""",
]

_SCHEMA_SQLITE = """
    CREATE TABLE IF NOT EXISTS setores (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        nome       TEXT NOT NULL,
        cor        TEXT DEFAULT '#4f8dfb',
        ativo      INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS tecnicos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nome        TEXT NOT NULL,
        cor         TEXT DEFAULT '#1a6fd4',
        token       TEXT,
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
        status             TEXT DEFAULT 'pendente',
        concluida_em       TEXT,
        conciliada_em      TEXT,
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
        status             TEXT DEFAULT 'pendente',
        concluido_em       TEXT,
        numero_os          TEXT,
        setor_id           INTEGER,
        FOREIGN KEY (ficha_id) REFERENCES fichas(id) ON DELETE CASCADE,
        FOREIGN KEY (setor_id) REFERENCES setores(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS cache_geo (
        cep         TEXT PRIMARY KEY,
        endereco    TEXT,
        lat         REAL,
        lng         REAL,
        preciso     INTEGER DEFAULT 1,
        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS push_subscriptions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tecnico_id  INTEGER NOT NULL,
        endpoint    TEXT NOT NULL,
        p256dh      TEXT NOT NULL,
        auth        TEXT NOT NULL,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS meta_revisao (
        id            INTEGER PRIMARY KEY CHECK (id = 1),
        revisao       INTEGER NOT NULL DEFAULT 0,
        atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS rastreios (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        token         TEXT NOT NULL UNIQUE,
        servico_id    INTEGER NOT NULL,
        tecnico_id    INTEGER NOT NULL,
        lat           REAL,
        lng           REAL,
        ativo         INTEGER DEFAULT 1,
        criado_em     TEXT DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT,
        encerrado_em  TEXT,
        eta_minutos   INTEGER,
        FOREIGN KEY (servico_id) REFERENCES servicos(id) ON DELETE CASCADE,
        FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS tecnico_status (
        tecnico_id   INTEGER PRIMARY KEY,
        app_versao   TEXT,
        gps_estado   TEXT,
        gps_erro     TEXT,
        visto_em     TEXT,
        FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS usuarios (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nome        TEXT NOT NULL,
        login       TEXT NOT NULL UNIQUE,
        senha_hash  TEXT NOT NULL,
        papel       TEXT NOT NULL DEFAULT 'tecnico',
        tecnico_id  INTEGER,
        ativo       INTEGER DEFAULT 1,
        criado_em   TEXT DEFAULT CURRENT_TIMESTAMP,
        ultimo_acesso TEXT,
        FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS mensagens (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        sala       TEXT NOT NULL,
        autor_tipo TEXT NOT NULL,
        autor_nome TEXT,
        texto      TEXT NOT NULL,
        criado_em  TEXT,
        lida       INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS erros_cliente (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        quando    TEXT,
        origem    TEXT,
        versao    TEXT,
        url       TEXT,
        mensagem  TEXT
    );
    CREATE TABLE IF NOT EXISTS pecas_agoraos (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        linha_planilha       INTEGER NOT NULL UNIQUE,
        id_os                INTEGER NOT NULL,
        id_produto_extensao  INTEGER NOT NULL,
        id_item              TEXT,
        cliente              TEXT,
        peca                 TEXT,
        qtd                  REAL DEFAULT 1,
        forca                TEXT,
        criado_em            TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS pecas_chegada (
        chave        TEXT PRIMARY KEY,
        chegou_em    TEXT,
        observacao   TEXT,
        registrado_por TEXT
    );
    CREATE TABLE IF NOT EXISTS servico_desfecho (
        servico_id      INTEGER PRIMARY KEY,
        desfecho        TEXT NOT NULL,
        motivo          TEXT,
        peca            TEXT,
        registrado_em   TEXT,
        registrado_por  TEXT
    );
"""

_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_servicos_ficha   ON servicos(ficha_id)",
    "CREATE INDEX IF NOT EXISTS idx_servicos_ordem   ON servicos(ficha_id, ordem)",
    "CREATE INDEX IF NOT EXISTS idx_fichas_tecnico   ON fichas(tecnico_id)",
    "CREATE INDEX IF NOT EXISTS idx_push_tecnico     ON push_subscriptions(tecnico_id)",
    "CREATE INDEX IF NOT EXISTS idx_servicos_setor   ON servicos(setor_id)",
    "CREATE INDEX IF NOT EXISTS idx_rastreios_servico ON rastreios(servico_id)",
    "CREATE INDEX IF NOT EXISTS idx_rastreios_ativo   ON rastreios(ativo)",
    "CREATE INDEX IF NOT EXISTS idx_mensagens_sala    ON mensagens(sala, id)",
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
    "ALTER TABLE fichas ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pendente'",
    "ALTER TABLE fichas ADD COLUMN IF NOT EXISTS concluida_em TEXT",
    "ALTER TABLE fichas ADD COLUMN IF NOT EXISTS conciliada_em TEXT",
    "ALTER TABLE tecnicos ADD COLUMN IF NOT EXISTS token TEXT",
    "ALTER TABLE tecnicos ADD CONSTRAINT tecnicos_token_unique UNIQUE (token)",
    "ALTER TABLE servicos ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pendente'",
    "ALTER TABLE servicos ADD COLUMN IF NOT EXISTS concluido_em TEXT",
    "ALTER TABLE servicos ADD COLUMN IF NOT EXISTS numero_os TEXT",
    "ALTER TABLE servicos ADD COLUMN IF NOT EXISTS setor_id INTEGER",
    "ALTER TABLE rastreios ADD COLUMN IF NOT EXISTS eta_minutos INTEGER",
    "ALTER TABLE rastreios ADD COLUMN IF NOT EXISTS precisao DOUBLE PRECISION",
    "ALTER TABLE tecnicos ADD COLUMN IF NOT EXISTS foto TEXT",
]

_MIGRACOES_SQLITE = [
    "ALTER TABLE cache_geo ADD COLUMN preciso INTEGER DEFAULT 1",
    "ALTER TABLE servicos ADD COLUMN tipo_aparelho TEXT",
    "ALTER TABLE servicos ADD COLUMN modelo TEXT",
    "ALTER TABLE fichas ADD COLUMN status TEXT DEFAULT 'pendente'",
    "ALTER TABLE fichas ADD COLUMN concluida_em TEXT",
    "ALTER TABLE fichas ADD COLUMN conciliada_em TEXT",
    "ALTER TABLE tecnicos ADD COLUMN token TEXT",
    "ALTER TABLE servicos ADD COLUMN status TEXT DEFAULT 'pendente'",
    "ALTER TABLE servicos ADD COLUMN concluido_em TEXT",
    "ALTER TABLE servicos ADD COLUMN numero_os TEXT",
    "ALTER TABLE servicos ADD COLUMN setor_id INTEGER",
    "ALTER TABLE rastreios ADD COLUMN eta_minutos INTEGER",
    "ALTER TABLE rastreios ADD COLUMN precisao REAL",
    "ALTER TABLE tecnicos ADD COLUMN foto TEXT",
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


# ─── Revisão global (motor do auto-refresh) ─────────────────────────────
# Um único inteiro que só cresce. Toda escrita bem-sucedida na API o
# incrementa (ver o after_request em app.py); o navegador pergunta o valor de
# tempos em tempos e só rebaixa dados de verdade quando o número mudou.
#
# Escolhi contador em vez de MAX(updated_at) porque timestamp não detecta
# DELETE — apagar um ponto não mexe em updated_at de linha nenhuma, e o painel
# de quem estava olhando continuaria mostrando o ponto apagado.


def bump_revisao(conn) -> None:
    # UPDATE-e-só-se-preciso-INSERT em vez de um upsert com ON CONFLICT.
    # Verboso de propósito: o ON CONFLICT tem diferenças de dialeto entre
    # SQLite e Postgres, e CURRENT_TIMESTAMP indo para coluna TEXT depende de
    # cast implícito que os dois tratam diferente. Este projeto já perdeu tempo
    # com SQL que passava em SQLite e estourava em produção — aqui não há
    # dialeto nenhum em jogo, e o timestamp vai como parâmetro comum.
    # O INSERT é praticamente código morto (a linha é semeada no init_db), mas
    # garante que um banco restaurado sem ela ainda funcione.
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")

    afetadas = execute(
        conn,
        "UPDATE meta_revisao SET revisao = revisao + 1, atualizado_em = ? WHERE id = 1",
        (agora,),
    )
    if not afetadas:
        execute(
            conn,
            "INSERT INTO meta_revisao (id, revisao, atualizado_em) VALUES (1, 1, ?)",
            (agora,),
        )


def ler_revisao(conn) -> dict:
    linha = fetch_one(conn, "SELECT revisao, atualizado_em FROM meta_revisao WHERE id = 1")
    if not linha:
        return {"revisao": 0, "atualizado_em": None}
    return {"revisao": int(linha["revisao"]), "atualizado_em": linha["atualizado_em"]}


def _semear_revisao(conn):
    # Sem a linha inicial o primeiro bump viraria um INSERT comum e o
    # ON CONFLICT nunca dispararia — funciona, mas deixa a leitura devolvendo
    # vazio até a primeira escrita. Semear evita esse estado intermediário.
    try:
        execute(conn, "INSERT INTO meta_revisao (id, revisao) VALUES (1, 0)")
        conn.commit()
    except Exception:
        conn.rollback()  # já existe — é o caso normal a partir do 2º boot


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
        _gerar_tokens_faltantes(conn)
        _criar_setores_iniciais(conn)
        _semear_revisao(conn)


# Setores criados na primeira execução. Só entram se a tabela estiver vazia —
# assim o usuário pode renomear, remover ou acrescentar sem que a lista volte
# a aparecer no próximo start.
SETORES_INICIAIS = [
    ("Panasonic", "#1a6fd4"),
    ("Philco",    "#e05c2a"),
    ("Loja",      "#2aa05c"),
]


def _criar_setores_iniciais(conn):
    try:
        total = fetch_one(conn, "SELECT COUNT(*) AS total FROM setores")["total"]
    except Exception:
        return
    if total:
        return

    for nome, cor in SETORES_INICIAIS:
        execute(conn, "INSERT INTO setores (nome, cor) VALUES (?, ?)", (nome, cor))
    conn.commit()


def _gerar_tokens_faltantes(conn):
    """Técnicos criados antes do link individual existir ficam sem token —
    preenche na inicialização em vez de exigir uma migração de dados à parte."""
    import secrets as _secrets

    sem_token = fetch_all(conn, "SELECT id FROM tecnicos WHERE token IS NULL OR token = ''")
    for row in sem_token:
        execute(conn, "UPDATE tecnicos SET token = ? WHERE id = ?",
                (_secrets.token_urlsafe(24), row["id"]))
    if sem_token:
        conn.commit()