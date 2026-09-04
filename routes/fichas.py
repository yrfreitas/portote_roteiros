import logging
import threading
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, session

from database import (db_conn, execute, fetch_all, fetch_one,
                      insert_returning_id, sql)
from services.geo import geocode_cep
from services.otimizador import (
    MINUTOS_PARADA, calcular_rota_fixa, calcular_tempo, haversine, otimizar_rota,
)
from services.push import notificar_tecnico
from services.rota_tempo import geometria_multipla

log = logging.getLogger("portotec.fichas")

fichas_bp = Blueprint("fichas", __name__)

# CEP da loja, usado como ponto de partida padrão quando ninguém informa um.
# Antes disso, transferir atendimento pra técnico sem ficha aberta no dia e
# reagendar/agendar OS criavam a ficha nova SEM ponto_partida_cep nenhum
# (obter_ou_criar_ficha não tinha fallback e os dois call-sites de
# tecnico_api.py/ordens_servico.py nunca passavam um) — rota impossível de
# otimizar até alguém notar e corrigir na mão. Pedido do Kalebe em 2026-08-24.
CEP_PARTIDA_PADRAO = "08021000"

# Trava única pra "reaproveita a ficha se já existe, senão cria" — o mesmo
# problema que services/agoraos.py já resolveu pro token: Procfile roda
# --workers 1 --threads 8, várias threads no mesmo processo. Sem isto, duas
# transferências/agendamentos pro mesmo técnico+dia quase ao mesmo tempo
# podiam cada uma checar "não existe" antes da outra commitar o INSERT, e
# criar duas fichas duplicadas pro mesmo dia. Ponto único porque são TRÊS
# lugares fazendo esse mesmo check-then-insert (transferir técnico, reagendar
# do app do técnico, agendar OS) — trava espalhada em cada um seria trava
# nenhuma.
_trava_ficha = threading.Lock()


def _aplicar_partida_padrao(extras: dict) -> None:
    """Preenche (in-place) ponto_partida_cep/lat/lng com o CEP da loja quando
    quem chamou não informou nenhum. Compartilhado entre criar ficha nova
    (obter_ou_criar_ficha) e transferir ficha existente pra outro técnico
    (transferir_ficha) — os dois jeitos de uma ficha acabar sem CEP.
    """
    cep_extra = "".join(c for c in str(extras.get("ponto_partida_cep") or "") if c.isdigit())
    if cep_extra:
        extras["ponto_partida_cep"] = cep_extra
        return
    extras["ponto_partida_cep"] = CEP_PARTIDA_PADRAO
    if extras.get("ponto_partida_lat") is None:
        geo = geocode_cep(CEP_PARTIDA_PADRAO)
        if geo:
            extras["ponto_partida_lat"] = geo.lat
            extras["ponto_partida_lng"] = geo.lng
            if not extras.get("ponto_partida"):
                extras["ponto_partida"] = geo.endereco


def obter_ou_criar_ficha(conn, tecnico_id, dia_semana, data_referencia=None, **extras):
    """Devolve (ficha_id, criou_ficha). Reaproveita ficha aberta do mesmo
    técnico/dia/data se existir; senão cria. `extras` são colunas opcionais
    do INSERT (ponto_partida, ponto_partida_cep, ...) — passe só o que tiver.

    COMMITA o INSERT na hora, ainda dentro da trava — não espera o commit da
    transação de quem chamou. Sem isso a trava não resolve nada: o SELECT da
    PRÓXIMA thread não veria o INSERT da anterior enquanto ele seguir
    pendente dentro da transação externa (testado: 20 chamadas concorrentes
    ainda criavam ficha duplicada mesmo com a trava, porque as duas liam
    "não existe" antes de qualquer uma commitar). Ficha ficar criada mesmo
    se o resto da requisição falhar depois é um custo aceitável — uma ficha
    vazia não corrompe nada; ficha duplicada, sim.

    Se quem chamou não informou (ou informou vazio) ponto_partida_cep, cai no
    CEP_PARTIDA_PADRAO (loja) — sem isso, transferir atendimento pra técnico
    sem ficha aberta no dia, reagendar ou agendar OS criavam ficha nova sem
    NENHUM ponto de partida. Geocodifica fora da trava de propósito: é
    chamada de rede (cacheada por CEP, então só pesa na primeira vez), e
    não precisa estar serializada — só o check-then-insert precisa.
    """
    _aplicar_partida_padrao(extras)

    with _trava_ficha:
        existente = fetch_one(conn, sql("""
            SELECT id FROM fichas
             WHERE tecnico_id = ? AND dia_semana = ?
               AND COALESCE(data_referencia, '') = COALESCE(?, '')
               AND status <> 'concluida'
             ORDER BY id DESC
        """), (tecnico_id, dia_semana, data_referencia))
        if existente:
            return existente["id"], False

        colunas = ["tecnico_id", "dia_semana", "data_referencia"] + list(extras.keys())
        valores = [tecnico_id, dia_semana, data_referencia] + list(extras.values())
        marcadores = ", ".join(["?"] * len(colunas))
        novo_id = insert_returning_id(conn, sql(
            f"INSERT INTO fichas ({', '.join(colunas)}) VALUES ({marcadores})"),
            tuple(valores))
        conn.commit()
        return novo_id, True

DIAS_VALIDOS = {
    "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado", "Domingo",
}

# Ordem da semana. A lista existe porque dia_semana é TEXTO no banco: ordenar
# por ele daria ordem alfabética (Domingo, Quarta, Quinta, Segunda, Sexta...),
# que é pior ainda que a bagunça que havia.
ORDEM_DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
              "Sexta-feira", "Sábado", "Domingo"]
_INDICE_DIA = {dia: i for i, dia in enumerate(ORDEM_DIAS)}


def nome_dia_semana(data_iso: str) -> str:
    """'2026-08-28' -> 'Sexta-feira'. Usado quando alguém escolhe uma DATA
    (reagendamento) e a ficha exige dia_semana — evita pedir a mesma coisa
    duas vezes (data e dia da semana) pra quem só sabe a data."""
    dt = datetime.strptime(data_iso, "%Y-%m-%d")
    return ORDEM_DIAS[dt.weekday()]


def ordenar_por_semana(fichas: list) -> list:
    """Ordem de CALENDÁRIO: ano, mês, dia — como a vida acontece.

    A primeira versão ordenava pelo dia da semana e agrupava todas as segundas
    juntas, independente da data. Errado: 17/08 e 24/08 são duas segundas
    diferentes, e a de hoje tem que vir antes da semana que vem.

    A data_referencia vem no formato "AAAA-MM-DD", então a ordenação textual
    já é cronológica — ano, depois mês, depois dia. Não precisa converter.

    Ficha SEM data cai no fim, agrupada pelo dia da semana: sem data não há
    onde encaixá-la na linha do tempo, e chutar uma posição seria pior que
    deixá-la claramente separada no rodapé da lista.

    Ordena em Python e não em SQL porque SQLite e Postgres divergem em NULLS
    FIRST/LAST — e aqui a regra de nulo é justamente o que importa.
    """
    def chave(f):
        data = (f.get("data_referencia") or "").strip()
        if data:
            return (0, data, f.get("id") or 0)
        return (1, "", _INDICE_DIA.get(f.get("dia_semana"), len(ORDEM_DIAS)))

    return sorted(fichas, key=chave)


@fichas_bp.route("/fichas", methods=["GET"])
def listar_fichas():
    tecnico_id = request.args.get("tecnico_id")
    status = request.args.get("status")

    # Login de papel "tecnico" só pode listar a PRÓPRIA ficha — achado em
    # 2026-08-31 junto com o mesmo recorte em GET /api/tecnicos. Sem isso,
    # bastava pedir /api/fichas?tecnico_id=<outro id> (ou nem informar
    # nenhum, trazendo TODAS) pra ver a rota de qualquer colega — a sidebar
    # do painel só escondia visualmente, o servidor entregava igual.
    # Sobrescreve o que veio na query: não é validação, é substituição.
    if session.get("papel") == "tecnico":
        meu_tecnico_id = session.get("tecnico_id")
        if not meu_tecnico_id:
            return jsonify([])
        tecnico_id = meu_tecnico_id

    condicoes, params = [], []
    if tecnico_id:
        if not str(tecnico_id).isdigit():
            return jsonify({"erro": "tecnico_id inválido"}), 400
        condicoes.append("f.tecnico_id = ?")
        params.append(int(tecnico_id))
    if status:
        condicoes.append("f.status = ?")
        params.append(status)

    # ?abertas=true esconde o que já foi concluído. Existe separado do
    # ?status=pendente de propósito: se algum dia entrar um terceiro status
    # (em andamento, cancelada), "aberta" continua significando "não fechada"
    # sem precisar caçar todos os lugares que listam ficha.
    if str(request.args.get("abertas", "")).lower() in ("1", "true", "sim"):
        condicoes.append("f.status <> 'concluida'")

    # ?dias=7 / ?dias=30 para o filtro de período do Histórico. Filtra por
    # concluida_em e não por created_at: o que interessa ali é quando a rota
    # foi FECHADA, não quando alguém a criou — uma rota montada na sexta e
    # concluída na segunda pertence à segunda.
    #
    # O corte é calculado em Python e vai como parâmetro. SQLite e Postgres não
    # compartilham função de data (date('now','-7 day') vs NOW() - INTERVAL),
    # e essa é a mesma razão pela qual as métricas por semana já são agregadas
    # em Python neste projeto.
    #
    # ARMADILHA: a coluna é TEXT e é gravada com CURRENT_TIMESTAMP, que produz
    # "2026-08-13 19:41:14" — separador ESPAÇO. Um isoformat() do Python produz
    # "2026-08-13T19:41:14", com T. Como a comparação aqui é textual e o espaço
    # (0x20) vem antes do T (0x54), o corte com T seria maior que qualquer data
    # gravada e o filtro devolveria lista vazia sempre. Daí o strftime manual.
    # O Postgres acrescenta ".123456+00" no fim, o que não atrapalha: os 19
    # primeiros caracteres já ordenam certo, e o resto só pesaria num empate.
    dias = request.args.get("dias")
    if dias:
        if not str(dias).isdigit() or not (1 <= int(dias) <= 3650):
            return jsonify({"erro": "dias inválido"}), 400
        corte = (datetime.now(timezone.utc) - timedelta(days=int(dias)))
        condicoes.append("f.concluida_em >= ?")
        params.append(corte.strftime("%Y-%m-%d %H:%M:%S"))

    filtro = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""

    query = f"""
        SELECT f.*,
               COUNT(s.id) AS total_servicos,
               t.nome AS tecnico_nome,
               t.cor  AS tecnico_cor
        FROM fichas f
        LEFT JOIN servicos s ON s.ficha_id = f.id
        LEFT JOIN tecnicos t ON t.id = f.tecnico_id
        {filtro}
        GROUP BY f.id, t.nome, t.cor
    """

    with db_conn() as conn:
        fichas = fetch_all(conn, query, tuple(params))

    # Histórico continua do mais recente para o mais antigo — ali a pergunta é
    # "o que foi feito por último". Na lista de trabalho a pergunta é outra:
    # "qual é a ordem da semana".
    if request.args.get("status") == "concluida":
        return jsonify(sorted(fichas,
                              key=lambda f: (f.get("concluida_em") or ""),
                              reverse=True))
    return jsonify(ordenar_por_semana(fichas))


@fichas_bp.route("/fichas", methods=["POST"])
def criar_ficha():
    data = request.get_json(silent=True) or {}

    dia = (data.get("dia_semana") or "").strip()
    tecnico_id = data.get("tecnico_id")

    if not dia:
        return jsonify({"erro": "dia_semana é obrigatório"}), 400
    if dia not in DIAS_VALIDOS:
        return jsonify({"erro": f"Dia da semana inválido: {dia}"}), 400
    if not tecnico_id:
        return jsonify({"erro": "tecnico_id é obrigatório"}), 400

    try:
        tecnico_id = int(tecnico_id)
    except (TypeError, ValueError):
        return jsonify({"erro": "tecnico_id inválido"}), 400

    # Mesma validação de editar_ficha — sem ela, criar direto pela API (sem
    # passar pelo <input type="date"> da tela) reabre o bug que a validação
    # da edição já fechou: "ficha com 2006 no lugar de 2026 encabeçando a
    # lista pra sempre", porque data_referencia ordena tudo como texto.
    data_referencia = (data.get("data_referencia") or "").strip()
    if data_referencia:
        try:
            datetime.strptime(data_referencia, "%Y-%m-%d")
        except ValueError:
            return jsonify({"erro": "Data inválida. Use o formato AAAA-MM-DD."}), 400

    partida = (data.get("ponto_partida") or "").strip()
    partida_cep = "".join(c for c in (data.get("ponto_partida_cep") or "") if c.isdigit())
    numero_partida = (data.get("ponto_partida_numero") or "").strip()

    # Sem CEP nenhum informado, cai no CEP da loja — ficha sem ponto de
    # partida não tem como ter rota otimizada. Ver CEP_PARTIDA_PADRAO.
    if not partida_cep:
        partida_cep = CEP_PARTIDA_PADRAO
        numero_partida = ""

    lat_p = lng_p = None
    aviso = None

    if partida_cep:
        geo = geocode_cep(partida_cep, numero=numero_partida)
        if geo:
            lat_p, lng_p = geo.lat, geo.lng
            if not partida:
                partida = geo.endereco
        else:
            aviso = ("Não foi possível localizar o CEP de partida. "
                     "A ficha foi criada, mas a rota só será otimizada "
                     "depois que você corrigir o ponto de partida.")

    with db_conn(commit=True) as conn:
        tecnico = fetch_one(conn, "SELECT id FROM tecnicos WHERE id = ?", (tecnico_id,))
        if not tecnico:
            return jsonify({"erro": "Técnico não encontrado"}), 404

        ficha_id = insert_returning_id(conn, """
            INSERT INTO fichas
                (tecnico_id, dia_semana, data_referencia, ponto_partida,
                 ponto_partida_cep, ponto_partida_lat, ponto_partida_lng)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tecnico_id, dia, data_referencia,
              partida, partida_cep, lat_p, lng_p))

    notificar_tecnico(
        tecnico_id, "Nova rota atribuída",
        f"Você tem uma nova ficha de {dia} pra conferir.",
    )

    resposta = {"id": ficha_id, "mensagem": "Ficha criada com sucesso"}
    if aviso:
        resposta["aviso"] = aviso
    return jsonify(resposta), 201


@fichas_bp.route("/fichas/corrigir-partida-padrao", methods=["POST"])
def corrigir_partida_padrao():
    """Aplica o CEP_PARTIDA_PADRAO em toda ficha que nunca teve ponto de
    partida — pedido do Kalebe em 2026-08-24, feito de fichas criadas antes
    do fallback existir (ver obter_ou_criar_ficha/criar_ficha/transferir_ficha).

    Ação manual, disparada por um clique no painel — de propósito NÃO roda
    sozinha em background nem em migração automática de startup: escrever em
    massa sobre dado de produção merece um clique consciente de quem está
    olhando o resultado, não silêncio.
    """
    with db_conn(commit=True) as conn:
        pendentes = fetch_all(conn, sql("""
            SELECT id, ponto_partida, ponto_partida_lat, ponto_partida_lng
              FROM fichas
             WHERE ponto_partida_cep IS NULL OR ponto_partida_cep = ''
        """))

        for f in pendentes:
            campos = {
                "ponto_partida_lat": f.get("ponto_partida_lat"),
                "ponto_partida_lng": f.get("ponto_partida_lng"),
                "ponto_partida":     f.get("ponto_partida"),
            }
            _aplicar_partida_padrao(campos)
            execute(conn, sql("""
                UPDATE fichas
                   SET ponto_partida_cep = ?, ponto_partida_lat = ?,
                       ponto_partida_lng = ?, ponto_partida = ?
                 WHERE id = ?
            """), (campos["ponto_partida_cep"], campos["ponto_partida_lat"],
                  campos["ponto_partida_lng"], campos["ponto_partida"], f["id"]))

    n = len(pendentes)
    return jsonify({
        "corrigidas": n,
        "mensagem": (f"{n} ficha(s) corrigida(s) com o CEP padrão da loja."
                     if n else "Nenhuma ficha estava sem ponto de partida."),
    })


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["GET"])
def obter_ficha(ficha_id):
    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404
        # Mesmo recorte de listar_fichas: login "tecnico" só abre a PRÓPRIA
        # ficha, mesmo sabendo o id de outra (link direto, histórico antigo
        # no navegador etc.). 404 igual à de "não existe" — não confirma pra
        # quem tentou que o id pertence a outro técnico.
        if session.get("papel") == "tecnico" and ficha.get("tecnico_id") != session.get("tecnico_id"):
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(
            conn,
            # Traz o desfecho junto: sem isto, o que o técnico registrou em
            # campo ficava preso no aplicativo dele e o escritório continuava
            # sem saber por que o atendimento fechou.
            sql("""SELECT s.*, d.desfecho, d.motivo AS desfecho_motivo,
                          d.peca AS desfecho_peca,
                          d.observacao AS desfecho_obs
                     FROM servicos s
                     LEFT JOIN servico_desfecho d ON d.servico_id = s.id
                    WHERE s.ficha_id = ? ORDER BY s.ordem, s.id"""),
            (ficha_id,),
        )

    dist = ficha.get("distancia_total") or 0.0

    resumo = {
        "distancia_km":  round(dist, 2),
        "tempo_minutos": calcular_tempo(dist, len(servicos)),
        "total_servicos": len(servicos),
        "sem_coordenada": sum(1 for s in servicos if s.get("lat") is None),
    }

    return jsonify({"ficha": ficha, "servicos": servicos, "resumo": resumo})


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["PUT"])
def editar_ficha(ficha_id):
    """Corrige dia da semana e data de referência de uma ficha existente.

    Não existia. Uma data digitada errada só se resolvia apagando a ficha e
    refazendo — perdendo todos os pontos junto. Foi assim que uma ficha ficou
    com 2006 no lugar de 2026 e passou a encabeçar a lista para sempre.

    Só estes dois campos: ponto de partida mexe em coordenada e obriga
    recalcular a rota, o que é outra operação com outras consequências.
    """
    data = request.get_json(silent=True) or {}

    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
    if not ficha:
        return jsonify({"erro": "Ficha não encontrada"}), 404

    dia = (data.get("dia_semana") or ficha.get("dia_semana") or "").strip()
    if dia not in DIAS_VALIDOS:
        return jsonify({"erro": f"Dia da semana inválido: {dia}"}), 400

    if "data_referencia" in data:
        data_ref = (data.get("data_referencia") or "").strip()
        # Vazio é permitido (ficha sem data marcada), mas texto que não seja
        # uma data real não: ela ordena a lista inteira, e lixo aqui volta a
        # embaralhar tudo — que é exatamente o problema que estamos fechando.
        if data_ref:
            try:
                datetime.strptime(data_ref, "%Y-%m-%d")
            except ValueError:
                return jsonify({"erro": "Data inválida. Use o formato AAAA-MM-DD."}), 400
    else:
        data_ref = ficha.get("data_referencia") or ""

    with db_conn(commit=True) as conn:
        execute(conn, """
            UPDATE fichas SET dia_semana = ?, data_referencia = ?,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
        """, (dia, data_ref, ficha_id))

    return jsonify({"mensagem": "Ficha atualizada",
                    "dia_semana": dia, "data_referencia": data_ref})


@fichas_bp.route("/fichas/<int:ficha_id>", methods=["DELETE"])
def deletar_ficha(ficha_id):
    with db_conn(commit=True) as conn:
        execute(conn, "DELETE FROM servicos WHERE ficha_id = ?", (ficha_id,))
        apagadas = execute(conn, "DELETE FROM fichas WHERE id = ?", (ficha_id,))

    if not apagadas:
        return jsonify({"erro": "Ficha não encontrada"}), 404
    return jsonify({"mensagem": "Ficha removida"})


STATUS_VALIDOS = {"pendente", "concluida"}


@fichas_bp.route("/fichas/<int:ficha_id>/status", methods=["PUT"])
def alterar_status_ficha(ficha_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_VALIDOS:
        return jsonify({"erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_VALIDOS))}"}), 400

    with db_conn(commit=True) as conn:
        ficha = fetch_one(conn, "SELECT id FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        if novo_status == "concluida":
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
            """, (novo_status, ficha_id))
        else:
            # Limpa conciliada_em junto: reabrir a rota tem que permitir
            # conciliar de novo depois de corrigir o que estava errado.
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = NULL,
                       conciliada_em = NULL, updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
            """, (novo_status, ficha_id))

    resposta = {"mensagem": f"Ficha marcada como {novo_status}", "status": novo_status}

    # Reabrir a rota tem que desfazer a baixa na planilha — senão o site diz
    # "pendente" e a planilha diz "concluído", e ninguém confia em nenhum dos dois.
    if novo_status == "pendente":
        try:
            from services.planilha import planilha_configurada, reverter
            if planilha_configurada():
                with db_conn() as conn:
                    servicos = fetch_all(
                        conn, "SELECT * FROM servicos WHERE ficha_id = ?", (ficha_id,)
                    )
                r = reverter({"id": ficha_id}, servicos)
                if r.get("revertidas"):
                    resposta["planilha"] = f"{r['revertidas']} baixa(s) desfeita(s) na planilha"
        except Exception:
            # Falha na planilha não pode impedir de reabrir a rota no site.
            log.exception("Falha ao reverter baixa na planilha da ficha %s", ficha_id)
            resposta["aviso"] = ("Rota reaberta, mas não consegui desfazer a baixa "
                                 "na planilha — confira manualmente.")

    return jsonify(resposta)


@fichas_bp.route("/fichas/<int:ficha_id>/conciliar", methods=["POST"])
def conciliar_ficha(ficha_id):
    """Casa os pontos concluídos da ficha com a planilha de pedidos.

    ?aplicar=true grava de verdade; sem isso é só prévia, pra o técnico ver
    o que vai acontecer antes de mexer na planilha.
    """
    from services.planilha import conciliar

    aplicar = str(request.args.get("aplicar", "")).lower() in ("1", "true", "sim")

    with db_conn() as conn:
        ficha = fetch_one(conn, """
            SELECT f.*, t.nome AS tecnico_nome
            FROM fichas f LEFT JOIN tecnicos t ON t.id = f.tecnico_id
            WHERE f.id = ?
        """, (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(conn, """
            SELECT * FROM servicos
             WHERE ficha_id = ? AND status = 'concluido'
             ORDER BY ordem, id
        """, (ficha_id,))

    if not servicos:
        return jsonify({
            "erro": "Nenhum ponto concluído nesta ficha. "
                    "Marque os pontos atendidos antes de finalizar o dia."
        }), 400

    # Gravar duas vezes duplicaria as linhas em "Outros Atendimentos" e não
    # daria baixa nenhuma (as linhas já conciliadas são puladas). Trava aqui.
    if aplicar and ficha.get("conciliada_em"):
        return jsonify({
            "erro": "Esta ficha já foi conciliada com a planilha em "
                    f"{ficha['conciliada_em']}. Reabra a rota se precisar refazer.",
            "ja_conciliada": True,
        }), 409

    try:
        resultado = conciliar(ficha, servicos, ficha.get("tecnico_nome") or "", aplicar)
    except Exception as exc:
        log.exception("Falha ao conciliar ficha %s", ficha_id)
        return jsonify({"erro": f"Falha ao acessar a planilha: {exc}"}), 502

    if resultado.get("configurada") is False:
        return jsonify(resultado), 503

    if aplicar:
        with db_conn(commit=True) as conn:
            execute(conn, """
                UPDATE fichas SET conciliada_em = CURRENT_TIMESTAMP WHERE id = ?
            """, (ficha_id,))

    resultado["ja_conciliada"] = bool(ficha.get("conciliada_em"))
    return jsonify(resultado)


@fichas_bp.route("/fichas/<int:ficha_id>/simular-encaixe", methods=["POST"])
def simular_encaixe(ficha_id):
    """Prévia de como o dia fica SE este endereço entrar na rota.

    Otimiza duas vezes — sem e com o ponto novo — e devolve as duas
    sequências. A diferença entre elas é a resposta que interessa: quantos
    quilômetros e quantos minutos o ponto custa, e em que parada ele entra.

    Não grava nada. É simulação: o usuário decide depois de ver.
    """
    data = request.get_json(silent=True) or {}

    try:
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Coordenadas inválidas para simular."}), 400

    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(conn, """
            SELECT id, cliente, endereco_completo, lat, lng, ordem
              FROM servicos
             WHERE ficha_id = ? AND lat IS NOT NULL AND lng IS NOT NULL
             ORDER BY ordem, id
        """, (ficha_id,))

    partida = {"lat": ficha.get("ponto_partida_lat"), "lng": ficha.get("ponto_partida_lng")}
    if partida["lat"] is None or partida["lng"] is None:
        # Sem base não existe trajeto para comparar: o otimizador precisa de um
        # ponto de saída. Erro explícito em vez de devolver zeros silenciosos,
        # que o usuário leria como "não custa nada adicionar".
        return jsonify({
            "erro": "Esta rota não tem CEP de partida definido — sem ele não dá "
                    "para calcular como o dia ficaria.",
            "sem_partida": True,
        }), 400

    novo = {"lat": lat, "lng": lng}
    antes = otimizar_rota(partida, servicos) if servicos else None
    depois = otimizar_rota(partida, servicos + [novo])

    def sequencia(resultado, pontos):
        """Traduz os índices devolvidos pelo otimizador em paradas legíveis."""
        saida = []
        for posicao, indice in enumerate(resultado["ordem"], start=1):
            p = pontos[indice]
            e_novo = p is novo
            saida.append({
                "posicao":  posicao,
                "cliente":  "Este endereço" if e_novo else (p.get("cliente") or "Sem nome"),
                "endereco": data.get("endereco", "") if e_novo else (p.get("endereco_completo") or ""),
                "lat": p["lat"], "lng": p["lng"],
                "novo": e_novo,
            })
        return saida

    seq_depois = sequencia(depois, servicos + [novo])
    posicao_novo = next((p["posicao"] for p in seq_depois if p["novo"]), None)

    # distancia_km (ida) e NÃO total_km (ida + retorno à base). É a métrica que
    # recalcular_rota grava em fichas.distancia_total e que aparece na sidebar,
    # no histórico e no XLSX. Usar total_km aqui mostraria 18,15 km para um dia
    # que o resto do sistema chama de 11,57 km — dois números para a mesma
    # rota, que é justamente o tipo de incoerência que esta tela veio matar.
    km_antes = antes["distancia_km"] if antes else 0.0
    min_antes = antes["tempo_minutos"] if antes else 0
    km_depois = depois["distancia_km"]

    return jsonify({
        "ficha_id":     ficha_id,
        "dia_semana":   ficha.get("dia_semana"),
        "partida":      {"lat": partida["lat"], "lng": partida["lng"],
                         "endereco": ficha.get("ponto_partida") or "Partida"},
        "antes":        {"km": km_antes, "minutos": min_antes, "paradas": len(servicos)},
        "depois":       {"km": km_depois, "minutos": depois["tempo_minutos"],
                         "paradas": len(servicos) + 1, "sequencia": seq_depois},
        "acrescimo_km":  round(km_depois - km_antes, 2),
        "acrescimo_min": depois["tempo_minutos"] - min_antes,
        "posicao_novo":  posicao_novo,
        "rota_vazia":    not servicos,
    })


@fichas_bp.route("/fichas/<int:ficha_id>/otimizar", methods=["POST"])
def otimizar_ficha(ficha_id):
    with db_conn(commit=True) as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404
        resultado = recalcular_rota(conn, ficha_id, ficha)

    return jsonify(resultado)


@fichas_bp.route("/fichas/<int:ficha_id>/reordenar", methods=["PUT"])
def reordenar_servicos(ficha_id):
    """Aplica uma ordem escolhida manualmente (arrastar/setas no front) e
    recalcula distância/tempo PARA ESSA ORDEM — sem rodar o otimizador de
    novo, que ia simplesmente desfazer o que o técnico acabou de ajustar."""
    data = request.get_json(silent=True) or {}
    ordem_ids = data.get("ordem_ids")

    if not isinstance(ordem_ids, list) or not ordem_ids:
        return jsonify({"erro": "ordem_ids deve ser uma lista de IDs de serviço"}), 400

    with db_conn(commit=True) as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        servicos = fetch_all(conn, "SELECT id FROM servicos WHERE ficha_id = ?", (ficha_id,))
        ids_da_ficha = {s["id"] for s in servicos}

        try:
            ordem_ids = [int(i) for i in ordem_ids]
        except (TypeError, ValueError):
            return jsonify({"erro": "ordem_ids deve conter apenas números"}), 400

        if set(ordem_ids) != ids_da_ficha:
            return jsonify({
                "erro": "A lista enviada não corresponde exatamente aos "
                        "pontos desta ficha (algum foi adicionado, "
                        "removido ou duplicado nesse meio tempo)."
            }), 409

        for posicao, servico_id in enumerate(ordem_ids, start=1):
            execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?",
                    (posicao, servico_id))

        resultado = recalcular_distancia_ordem_fixa(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Ordem atualizada manualmente", **resultado})


@fichas_bp.route("/fichas/<int:ficha_id>/tecnico", methods=["PUT"])
def transferir_ficha(ficha_id):
    """Passa a ficha inteira para outro técnico.

    Existe porque em 2026-08-17 a Porto Tec passou a ter dois técnicos em
    campo e TODAS as fichas estavam no nome de um só. Sem isto, a única saída
    era refazer a rota do zero no outro nome — e o rastreio, que é por
    técnico, nunca casava com quem de fato estava indo.

    A rota em si não muda: os pontos, a ordem e o ponto de partida são da
    FICHA, não de quem a executa. Só troca o dono — MAS se essa ficha nunca
    teve ponto de partida (comum em fichas antigas, de antes do CEP virar
    obrigatório em toda criação), aproveita o momento pra também sanar isso.
    Sem isso a ficha seguiria pra sempre sem partida: transferir de dono
    nunca mais mexeria nela de novo.
    """
    data = request.get_json(silent=True) or {}
    try:
        novo_tecnico = int(data.get("tecnico_id"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Informe o técnico de destino"}), 400

    with db_conn(commit=True) as conn:
        ficha = fetch_one(conn, "SELECT * FROM fichas WHERE id = ?", (ficha_id,))
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        destino = fetch_one(conn, "SELECT id, nome FROM tecnicos WHERE id = ?",
                            (novo_tecnico,))
        if not destino:
            return jsonify({"erro": "Técnico de destino não encontrado"}), 404

        if ficha.get("tecnico_id") == novo_tecnico:
            return jsonify({"mensagem": f"A ficha já é do {destino['nome']}"})

        # Rastreio é POR TÉCNICO: um link aberto pelo antigo dono continuaria
        # esperando a posição dele, que não vai mais àquele cliente. Encerrar
        # é mais honesto do que deixar o cliente olhando um mapa que nunca
        # mais se move.
        from routes.rastreio import encerrar_por_servico
        for sv in fetch_all(conn, "SELECT id FROM servicos WHERE ficha_id = ?",
                            (ficha_id,)):
            encerrar_por_servico(conn, sv["id"])

        campos = {
            "ponto_partida_cep": ficha.get("ponto_partida_cep"),
            "ponto_partida_lat": ficha.get("ponto_partida_lat"),
            "ponto_partida_lng": ficha.get("ponto_partida_lng"),
            "ponto_partida":     ficha.get("ponto_partida"),
        }
        _aplicar_partida_padrao(campos)

        execute(conn, """
            UPDATE fichas
               SET tecnico_id = ?, updated_at = CURRENT_TIMESTAMP,
                   ponto_partida_cep = ?, ponto_partida_lat = ?,
                   ponto_partida_lng = ?, ponto_partida = ?
             WHERE id = ?
        """, (novo_tecnico, campos["ponto_partida_cep"], campos["ponto_partida_lat"],
              campos["ponto_partida_lng"], campos["ponto_partida"], ficha_id))

    return jsonify({"mensagem": f"Ficha transferida para {destino['nome']}",
                    "tecnico_id": novo_tecnico})


def recalcular_rota(conn, ficha_id, ficha) -> dict:
    servicos = fetch_all(
        conn, "SELECT id, lat, lng FROM servicos WHERE ficha_id = ?", (ficha_id,)
    )

    validos = [s for s in servicos
               if s.get("lat") is not None and s.get("lng") is not None]

    tem_partida = bool(ficha) and ficha.get("ponto_partida_lat") is not None

    if not validos or not tem_partida:
        execute(conn, """
            UPDATE fichas SET distancia_total = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (ficha_id,))
        return {
            "distancia_total": 0.0,
            "retorno_km":      0.0,
            "total_servicos":  len(servicos),
            "tempo_minutos":   len(servicos) * MINUTOS_PARADA,
            "sem_partida":     not tem_partida,
            "sem_coordenada":  len(servicos) - len(validos),
        }

    partida = {"lat": ficha["ponto_partida_lat"], "lng": ficha["ponto_partida_lng"]}
    pontos = [{"lat": s["lat"], "lng": s["lng"], "id": s["id"]} for s in validos]

    r = otimizar_rota(partida, pontos)

    for posicao, idx in enumerate(r["ordem"], start=1):
        execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?",
                (posicao, pontos[idx]["id"]))

    for offset, s in enumerate(
        [s for s in servicos if s.get("lat") is None], start=len(pontos) + 1
    ):
        execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?", (offset, s["id"]))

    execute(conn, """
        UPDATE fichas SET distancia_total = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (r["distancia_km"], ficha_id))

    return {
        "distancia_total": r["distancia_km"],
        "retorno_km":      r["retorno_km"],
        "total_km":        r["total_km"],
        "total_servicos":  len(servicos),
        "tempo_minutos":   r["tempo_minutos"],
        "ganho_2opt_km":   r["ganho_2opt_km"],
        "sem_coordenada":  len(servicos) - len(validos),
        # "osrm" (distância de rua de verdade) ou "linha_reta" (o OSRM não
        # respondeu a tempo) -- pedido de 2026-09-04: mostrar isso em vez de
        # deixar parecer que a rota é sempre calculada do mesmo jeito.
        "fonte_distancia": r.get("fonte_distancia", "linha_reta"),
    }


def recalcular_distancia_ordem_fixa(conn, ficha_id, ficha) -> dict:
    servicos = fetch_all(
        conn,
        "SELECT id, lat, lng FROM servicos WHERE ficha_id = ? ORDER BY ordem, id",
        (ficha_id,),
    )
    validos = [s for s in servicos
               if s.get("lat") is not None and s.get("lng") is not None]
    tem_partida = bool(ficha) and ficha.get("ponto_partida_lat") is not None

    if not validos or not tem_partida:
        execute(conn, """
            UPDATE fichas SET distancia_total = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (ficha_id,))
        return {
            "distancia_total": 0.0,
            "total_servicos":  len(servicos),
            "tempo_minutos":   len(servicos) * MINUTOS_PARADA,
            "sem_partida":     not tem_partida,
            "sem_coordenada":  len(servicos) - len(validos),
        }

    partida = {"lat": ficha["ponto_partida_lat"], "lng": ficha["ponto_partida_lng"]}
    pontos = [{"lat": s["lat"], "lng": s["lng"]} for s in validos]

    r = calcular_rota_fixa(partida, pontos)

    execute(conn, """
        UPDATE fichas SET distancia_total = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (r["distancia_km"], ficha_id))

    return {
        "distancia_total": r["distancia_km"],
        "retorno_km":      r["retorno_km"],
        "total_km":        r["total_km"],
        "total_servicos":  len(servicos),
        "tempo_minutos":   r["tempo_minutos"],
        "sem_coordenada":  len(servicos) - len(validos),
    }

@fichas_bp.route("/fichas/<int:ficha_id>/km-real", methods=["GET"])
def km_real_ficha(ficha_id):
    """Quilometragem REAL, medida pelo GPS trecho a trecho (pedido de
    2026-09-02), pra comparar com fichas.distancia_total (planejada).

    Só existe a partir de quando rastreio_pings passou a ser gravado
    (2026-09-02) — fichas concluídas antes disso não têm ping nenhum, e a
    resposta diz isso em vez de fingir zero quilômetro rodado.
    """
    with db_conn() as conn:
        tokens = fetch_all(conn, """
            SELECT DISTINCT ra.token FROM rastreios ra
              JOIN servicos sv ON sv.id = ra.servico_id
             WHERE sv.ficha_id = ? AND ra.token IS NOT NULL
        """, (ficha_id,))
        if not tokens:
            return jsonify({"km_real": None, "motivo": "sem rastreio nesta ficha"})

        total_km = 0.0
        tem_ping = False
        for t in tokens:
            pings = fetch_all(conn, """
                SELECT lat, lng FROM rastreio_pings
                 WHERE token = ? AND lat IS NOT NULL AND lng IS NOT NULL
                 ORDER BY id
            """, (t["token"],))
            if len(pings) >= 2:
                tem_ping = True
            for i in range(1, len(pings)):
                total_km += haversine(pings[i - 1]["lat"], pings[i - 1]["lng"],
                                       pings[i]["lat"], pings[i]["lng"])

    if not tem_ping:
        return jsonify({"km_real": None, "motivo": "sem posição suficiente registrada"})
    return jsonify({"km_real": round(total_km, 1)})


@fichas_bp.route("/fichas/<int:ficha_id>/rota-geometria", methods=["GET"])
def rota_geometria_ficha(ficha_id):
    """Pontos [[lat,lng], ...] do trajeto real por rua ligando a partida às
    paradas na ordem exibida -- pedido de 2026-09-04: "o mesmo mecanismo
    [OSRM] que fez a rota do técnico, faça isso no mapa das rotas também"
    (o mapa da ficha ligava parada a parada com reta pontilhada).

    Devolve {"pontos": []} quando faltar partida/coordenada ou o OSRM não
    responder -- o front já sabe cair na reta nesse caso, mesma rede de
    segurança de sempre.
    """
    with db_conn() as conn:
        ficha = fetch_one(conn, "SELECT ponto_partida_lat, ponto_partida_lng FROM fichas WHERE id = ?",
                           (ficha_id,))
        if not ficha or ficha.get("ponto_partida_lat") is None:
            return jsonify({"pontos": []})

        servicos = fetch_all(
            conn, "SELECT lat, lng FROM servicos WHERE ficha_id = ? ORDER BY ordem, id",
            (ficha_id,))
        validos = [s for s in servicos if s.get("lat") is not None and s.get("lng") is not None]
        if not validos:
            return jsonify({"pontos": []})

        pontos = [{"lat": ficha["ponto_partida_lat"], "lng": ficha["ponto_partida_lng"]}] + [
            {"lat": s["lat"], "lng": s["lng"]} for s in validos
        ]

    return jsonify({"pontos": geometria_multipla(pontos) or []})
