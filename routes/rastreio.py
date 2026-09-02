"""Rastreio ao vivo: o cliente acompanha o técnico a caminho.

PREVISÃO DE CHEGADA **E** POSIÇÃO NO MAPA — os dois, cada um cobrindo o buraco
do outro.

A primeira versão era só previsão, e o motivo está registrado aqui embaixo
porque continua verdadeiro. O Kalebe reclamou em 2026-08-14 do resultado
prático: "no link só aparece a casa do cliente, mas não mostra o técnico indo
até ele". Reclamação correta — o mapa mostrava um alfinete parado.

O QUE MUDOU: o celular do técnico agora manda a posição enquanto o app está na
tela, e o cliente vê o carrinho andando. O que NÃO mudou é a limitação do
navegador que gerou a decisão original:

    Assim que o técnico sai do site para o Waze, o sistema CONGELA a página e
    o watchPosition para de disparar. Página web não recebe localização em
    segundo plano, nem instalada como aplicativo, nem no Android nem no iPhone.

Ou seja: a posição é real quando chega, mas ENVELHECE durante a navegação. Por
isso a página do cliente sempre diz há quanto tempo aquele ponto foi visto, e
volta a destacar a previsão quando o dado passa de POSICAO_FRESCA_SEG. Mostrar
alfinete velho como se fosse "agora" seria pior que não mostrar nada — o
cliente olharia um carro parado e concluiria que o técnico não saiu do lugar.

DECISÕES DE PRIVACIDADE (o motivo de guardar tão pouco):
- Guarda só a ÚLTIMA posição, sobrescrevendo. Não existe histórico de trajeto:
  o cliente quer saber onde ele está agora, e trajeto de funcionário é dado
  sensível que ninguém pediu para ter.
- É por ATENDIMENTO, não por técnico. Começa quando ele sai para aquele
  cliente e morre quando chega.
- Expira sozinho depois de VALIDADE_HORAS mesmo se ninguém encerrar. Técnico
  que esquece o app aberto não vira rastreado o dia inteiro.
- Concluir o ponto encerra o rastreio (ver aplicar_status_servico).
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request

from database import IS_PG, db_conn, execute, fetch_all, fetch_one
from services.otimizador import (FATOR_ROTA, MINUTOS_PARADA,
                                 VELOCIDADE_KMH, haversine)

log = logging.getLogger("portotec.rastreio")

rastreio_bp = Blueprint("rastreio", __name__)

# Depois disso o link para de mostrar posição, encerrado ou não. Uma visita
# não passa de algumas horas; o que passar disso é app esquecido aberto.
VALIDADE_HORAS = 6

# Acima disso a posição deixa de ser tratada como "ao vivo" e a página do
# cliente passa a dizer há quanto tempo foi vista. 3 min cobre o intervalo
# normal de envio (20s) com folga larga para túnel, sinal ruim e a tela do
# técnico apagando por um instante — sem deixar passar o caso real, que é ele
# ter ido para o Waze e o navegador ter congelado a página.
POSICAO_FRESCA_SEG = 180

# Leitura pior que isto é recusada: não é posição, é chute. Sem GPS com sinal,
# o navegador responde por Wi-Fi ou por IP e erra por quilômetros — no iPhone
# com "Localização Precisa" desligada, TODA leitura erra de 1 a 3 km. Ver a
# mesma constante em tecnico.js: o app filtra antes de mandar, e aqui é a
# barreira de quem grava, porque um app velho em cache não filtraria nada.
PRECISAO_MAXIMA_M = 500

_ATIVO = "ativo IS TRUE" if IS_PG else "ativo = 1"
# Mesma condição, mas qualificada com o alias de `rastreios` — obrigatório
# em qualquer JOIN que também traga uma tabela com coluna `ativo` própria
# (tecnicos, setores, usuarios...), senão vira "ambiguous column name" tanto
# no Postgres quanto no SQLite. Achado em produção em 2026-08-25: /api/avisos
# junta rastreios + tecnicos e quebrava desde que `tecnicos.ativo` existe.
_ATIVO_RA = "ra.ativo IS TRUE" if IS_PG else "ra.ativo = 1"


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _expirado(criado_em: str) -> bool:
    """Compara textualmente, no mesmo formato que gravamos. Ver a armadilha
    documentada em routes/fichas.py: a coluna é TEXT e o separador é ESPAÇO,
    então um isoformat() com T daria comparação errada."""
    if not criado_em:
        return True
    corte = (datetime.now(timezone.utc) - timedelta(hours=VALIDADE_HORAS))
    return str(criado_em)[:19] < corte.strftime("%Y-%m-%d %H:%M:%S")


def encerrar_por_servico(conn, servico_id: int) -> None:
    """Chamado quando o ponto é concluído: chegou, não faz mais sentido
    rastrear. Fica aqui para não espalhar regra de rastreio pelas rotas."""
    execute(conn, f"""
        UPDATE rastreios SET ativo = {'FALSE' if IS_PG else '0'}, encerrado_em = ?
         WHERE servico_id = ? AND {_ATIVO}
    """, (_agora(), servico_id))


def _prever_minutos(conn, servico_id: int) -> int:
    """Minutos até chegar, a partir da parada anterior da rota (ou da base).

    Mesma velocidade média do otimizador, para que a previsão do cliente e o
    tempo mostrado no painel não briguem entre si. Sem coordenada dá None: é
    melhor não mostrar horário nenhum do que mostrar um chutado.
    """
    destino = fetch_one(conn, """
        SELECT sv.lat, sv.lng, sv.ordem, sv.ficha_id,
               f.ponto_partida_lat, f.ponto_partida_lng
          FROM servicos sv JOIN fichas f ON f.id = sv.ficha_id
         WHERE sv.id = ?
    """, (servico_id,))
    if not destino or destino.get("lat") is None:
        return None

    # De onde ele sai: a parada imediatamente anterior na ordem da rota; se
    # este é o primeiro ponto do dia, a base.
    anterior = fetch_one(conn, """
        SELECT lat, lng FROM servicos
         WHERE ficha_id = ? AND ordem < ? AND lat IS NOT NULL
         ORDER BY ordem DESC
    """, (destino["ficha_id"], destino.get("ordem") or 0))

    origem = anterior or {"lat": destino.get("ponto_partida_lat"),
                          "lng": destino.get("ponto_partida_lng")}
    if origem.get("lat") is None:
        return None

    minutos, _ = _minutos_reais_ou_estimados(
        origem["lat"], origem["lng"], destino["lat"], destino["lng"])
    return minutos



# ─── Previsão de chegada ────────────────────────────────────────────────
#
# Pergunta o tempo REAL de carro (Google, com o trânsito de agora). Só cai na
# conta local quando não há chave ou o serviço falha — antes a conta local era
# a única fonte, e ela errava sempre para o mesmo lado: prometia ao cliente
# uma chegada bem mais cedo do que a real.
def _minutos_reais_ou_estimados(o_lat, o_lng, d_lat, d_lng):
    from services.rota_tempo import minutos_ate

    reais = minutos_ate(o_lat, o_lng, d_lat, d_lng)
    if reais is not None:
        return reais, "transito"

    km = haversine(o_lat, o_lng, d_lat, d_lng)
    return max(1, int(round((km * FATOR_ROTA / VELOCIDADE_KMH) * 60))), "estimado"


def _tecnico_por_token(conn, token):
    if not token:
        return None
    return fetch_one(conn, "SELECT * FROM tecnicos WHERE token = ?", (token,))


@rastreio_bp.route("/t/<token>/servicos/<int:servico_id>/rastreio", methods=["POST"])
def iniciar(token, servico_id):
    """Abre (ou reaproveita) o rastreio deste atendimento."""
    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        # O ponto tem que ser de uma ficha do próprio técnico. Sem isso, quem
        # tivesse um link de técnico poderia abrir rastreio de qualquer ponto.
        servico = fetch_one(conn, """
            SELECT sv.id FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id
             WHERE sv.id = ? AND f.tecnico_id = ?
        """, (servico_id, tecnico["id"]))
        if not servico:
            return jsonify({"erro": "Ponto não encontrado nas suas rotas"}), 404

        existente = fetch_one(conn, f"""
            SELECT * FROM rastreios WHERE servico_id = ? AND {_ATIVO}
             ORDER BY id DESC
        """, (servico_id,))

        # Reaproveita o link se ainda vale: reabrir o mesmo atendimento não
        # pode invalidar o link que o cliente já recebeu.
        if existente and not _expirado(existente.get("criado_em")):
            return jsonify({"token": existente["token"], "reaproveitado": True})

        _encerrar_outros_do_tecnico(conn, tecnico["id"], servico_id)

        novo_token = secrets.token_urlsafe(16)
        execute(conn, """
            INSERT INTO rastreios (token, servico_id, tecnico_id, criado_em, eta_minutos)
            VALUES (?, ?, ?, ?, ?)
        """, (novo_token, servico_id, tecnico["id"], _agora(),
              _prever_minutos(conn, servico_id)))

        # O aviso cai na conversa do cliente sozinho. É o que o Kalebe pediu:
        # a pessoa abre o link, vê o mapa E já encontra a mensagem dizendo que
        # o técnico saiu — sem ninguém precisar digitar.
        from routes.chat import publicar
        publicar(conn, novo_token,
                 f"{tecnico['nome'].split(' ')[0]} saiu e está a caminho. "
                 "Acompanhe pelo mapa acima — se precisar, é só escrever aqui.",
                 autor_tipo="sistema", autor_nome="Porto Tec")

    return jsonify({"token": novo_token, "reaproveitado": False}), 201


def _encerrar_outros_do_tecnico(conn, tecnico_id, servico_id_novo) -> int:
    """Fecha os rastreios anteriores deste técnico ao começar um novo.

    NINGUÉM ESTÁ A CAMINHO DE DOIS LUGARES AO MESMO TEMPO. Sem isto, cada
    "a caminho" abria mais um link vivo e TODOS recebiam a mesma posição:
    encontrado em produção em 2026-08-17, com o Pedro alimentando dois
    clientes ao mesmo tempo. Na prática, o cliente anterior via o técnico se
    AFASTANDO e concluía que ele estava indo embora — pior do que não ter
    acompanhamento nenhum.

    O link antigo não some: passa a mostrar "acompanhamento encerrado", que é
    a verdade. Quem ficou para depois será avisado de novo quando ele sair.
    """
    return execute(conn, f"""
        UPDATE rastreios SET ativo = {'FALSE' if IS_PG else '0'}, encerrado_em = ?
         WHERE tecnico_id = ? AND servico_id <> ? AND {_ATIVO}
    """, (_agora(), tecnico_id, servico_id_novo))


def _marcar_visto(conn, tecnico_id, gps_estado=None, app_versao=None, gps_erro=None):
    """Atualiza o estado do aparelho do técnico (tabela tecnico_status).

    UPDATE-e-só-se-preciso-INSERT em vez de upsert com ON CONFLICT: o dialeto
    diverge entre SQLite e Postgres — a mesma armadilha que já mordeu no
    bump_revisao. Campos None não apagam o que já se sabia.
    """
    mudou = execute(conn, """
        UPDATE tecnico_status
           SET app_versao = COALESCE(?, app_versao),
               gps_estado = COALESCE(?, gps_estado),
               gps_erro   = COALESCE(?, gps_erro),
               visto_em   = ?
         WHERE tecnico_id = ?
    """, (app_versao, gps_estado, gps_erro, _agora(), tecnico_id))
    if not mudou:
        execute(conn, """
            INSERT INTO tecnico_status
                (tecnico_id, app_versao, gps_estado, gps_erro, visto_em)
            VALUES (?, ?, ?, ?, ?)
        """, (tecnico_id, app_versao, gps_estado, gps_erro, _agora()))


def _gravar_posicao(conn, tecnico_id, lat, lng, precisao):
    """Grava a posição nos rastreios ABERTOS deste técnico. Devolve quantos.

    Escreve em todos os abertos de propósito: se o técnico tem dois links
    vivos (saiu para um cliente e o anterior não foi fechado), os dois mostram
    onde ele está — que é a verdade. Escolher um só faria o outro cliente
    olhar posição congelada.

    Zero rastreios abertos = NÃO GRAVA NADA. É esta linha que sustenta a
    promessa de não rastrear funcionário o dia inteiro: fora do atendimento,
    a posição que chega é descartada, mesmo que o aplicativo continue ligado.
    """
    abertos = fetch_all(conn, f"""
        SELECT ra.id, ra.criado_em, ra.servico_id, ra.token FROM rastreios ra
          JOIN servicos sv ON sv.id = ra.servico_id
         WHERE ra.tecnico_id = ? AND {_ATIVO} AND sv.status <> 'concluido'
    """, (tecnico_id,))

    vivos = [r for r in abertos if not _expirado(r.get("criado_em"))]
    for r in vivos:
        # Histórico de posição (pedido de 2026-09-02, "km real vs planejado")
        # — rastreios só guarda a ÚLTIMA posição; isto aqui é o traço todo,
        # pra somar trecho a trecho depois (ver km_real_ficha em tecnicos.py).
        execute(conn,
            "INSERT INTO rastreio_pings (token, lat, lng, criado_em) VALUES (?, ?, ?, ?)",
            (r.get("token") or "", lat, lng, _agora()))
        # A previsão é REFEITA a cada posição, a partir de onde o técnico está
        # de verdade. Antes ela era calculada uma única vez, na saída, medindo
        # da parada ANTERIOR da rota até o destino — o que produzia coisas como
        # "saiu 15:11, chega 15:14" com o técnico a quilômetros dali (relatado
        # pelo Kalebe em 2026-08-17). Com GPS real, estimar por tabela deixou
        # de ter desculpa.
        eta = _minutos_ate(conn, r["servico_id"], lat, lng)
        execute(conn, """
            UPDATE rastreios
               SET lat = ?, lng = ?, precisao = ?, atualizado_em = ?,
                   eta_minutos = COALESCE(?, eta_minutos)
             WHERE id = ?
        """, (lat, lng, precisao, _agora(), eta, r["id"]))
    return len(vivos)


def _minutos_ate(conn, servico_id, lat, lng):
    """Minutos da posição informada até o destino. None sem coordenada."""
    destino = fetch_one(conn, "SELECT lat, lng FROM servicos WHERE id = ?",
                        (servico_id,))
    if not destino or destino.get("lat") is None or lat is None:
        return None

    minutos, _ = _minutos_reais_ou_estimados(
        lat, lng, destino["lat"], destino["lng"])
    return minutos


@rastreio_bp.route("/t/<token>/rastreador", methods=["GET", "POST"])
def rastreador_externo(token):
    """Recebe a posição de um APLICATIVO DE GPS nativo (Traccar Client).

    POR QUE ISTO EXISTE — e por que substitui o GPS do navegador:
    página web não recebe localização em segundo plano. Assim que o técnico
    abre o Waze, o navegador congela a página e o envio para. Isso não é bug
    do nosso código e não tem contorno em web; foi o que fez o acompanhamento
    "não ir" nas tentativas de 2026-08-14.

    Um aplicativo nativo de GPS não tem essa limitação: continua reportando
    com a tela apagada e com o Waze na frente. O Traccar Client é gratuito,
    existe para Android e iPhone, e manda a posição para uma URL qualquer —
    esta. O mapa do cliente não muda; muda só quem alimenta a posição.

    Aceita GET e POST porque as versões do aplicativo divergem, e lê tanto de
    query string quanto de JSON. `lon` e `lng` são o mesmo campo com nomes
    diferentes conforme o app.

    SEMPRE devolve 200, inclusive quando descarta. O Traccar reenfileira e
    repete o que falha: responder erro para uma posição fora de atendimento
    faria o aplicativo insistir a viagem inteira, gastando bateria e dados do
    técnico por um dado que nunca vamos guardar.
    """
    # force=True: alguns aplicativos mandam JSON sem o cabeçalho
    # Content-Type correto, e sem isto o corpo seria ignorado em silêncio.
    # Retrato do que chegou, guardado ANTES de qualquer interpretação.
    #
    # Existe porque diagnosticar aplicativo de celular às cegas já custou
    # várias rodadas: eu sabia que "chegou algo sem posição", mas não O QUE
    # chegou. Com o corpo cru registrado, uma única tentativa do técnico basta
    # para saber se o app manda lista, objeto, campo com outro nome, ou nada.
    # Truncado em 300 caracteres: é diagnóstico, não histórico.
    _cru = (request.get_data(cache=True) or b"")[:300].decode("utf-8", "replace")
    _retrato = (f"{request.method} ct={request.content_type or '-'} "
                f"args={dict(request.args) or '-'} corpo={_cru or '-'}")[:300]

    dados = request.get_json(silent=True, force=True)

    # O OwnTracks pode mandar uma LISTA de mensagens, não um objeto solto —
    # é o que acontece quando ele acumulou fila sem sinal e despeja tudo de
    # uma vez. A versão anterior descartava a lista inteira: a requisição
    # chegava, nenhuma coordenada era lida, e o painel registrava só
    # "url-testada". Foi exatamente o que aconteceu com o Pedro em 2026-08-17.
    #
    # Da lista interessa a posição MAIS RECENTE: as antigas já não dizem onde
    # ele está, e gravar a última da fila como se fosse agora seria mentira.
    if isinstance(dados, list):
        posicoes = [d for d in dados
                    if isinstance(d, dict) and d.get("_type") in (None, "location")]
        # `tst` é o carimbo de tempo do OwnTracks (epoch). Sem ele, mantém a
        # ordem em que vieram, que já costuma ser cronológica.
        posicoes.sort(key=lambda d: d.get("tst") or 0)
        dados = posicoes[-1] if posicoes else {}

    if not isinstance(dados, dict):
        dados = {}

    fonte = {**request.args.to_dict(), **dados}

    # ----- particularidades do OwnTracks -----
    # Ele identifica o tipo da mensagem em `_type` e NEM TODA carrega posição
    # atual: "waypoint" (ponto salvo pelo usuário) e "transition" (entrou/saiu
    # de uma área) também trazem lat/lon. Gravar essas colocaria o técnico num
    # lugar onde ele não está — só "location" vale.
    tipo = fonte.get("_type")
    eh_owntracks = tipo is not None
    if eh_owntracks and tipo != "location":
        return jsonify([]), 200

    # O OwnTracks espera um ARRAY na resposta (é onde o servidor devolveria
    # comandos para o aparelho). Objeto JSON faz o aplicativo registrar erro a
    # cada envio e assustar quem for olhar o log dele.
    def responder(corpo, status=200):
        return (jsonify([]) if eh_owntracks else jsonify(corpo)), status

    def num(*nomes):
        for n in nomes:
            v = fonte.get(n)
            if v not in (None, ""):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    continue
        return None

    lat, lng = num("lat", "latitude"), num("lon", "lng", "longitude")

    # A checagem de faixa só pode rodar DEPOIS de saber que há coordenada:
    # comparar None com número estoura em TypeError e vira 500. Foi exatamente
    # o que quebrou a URL de teste aberta no navegador em 2026-08-14 — sem
    # coordenada, o caminho mais inofensivo do endpoint era o único que caía.
    if lat is not None and lng is not None:
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return responder({"ok": False, "motivo": "coordenada inválida"})

    precisao = num("accuracy", "acc", "hdop")

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            # 404 aqui é intencional, ao contrário dos outros casos: URL errada
            # na configuração do aplicativo TEM que falhar de forma visível,
            # senão o técnico configura errado e ninguém descobre.
            return jsonify({"erro": "URL do rastreador inválida — confira o "
                                    "endereço colado no aplicativo"}), 404

        # SEM COORDENADA = alguém abriu a URL no navegador para conferir.
        # Vira teste de configuração, e não erro: é o jeito mais rápido de o
        # técnico provar, do próprio celular, que a URL e a internet estão
        # certas — restando só a permissão do aplicativo. Registra a visita,
        # então o painel também confirma que o aparelho alcançou o servidor.
        if lat is None or lng is None:
            # Distingue "alguém abriu a URL no navegador" de "o aplicativo de
            # GPS falou aqui mas sem posição". Os dois chegam sem coordenada e
            # eu já confundi um com o outro uma vez: o painel dizia
            # "URL testada" enquanto era o OwnTracks mandando um lote que eu
            # não sabia ler.
            veio_de_app = eh_owntracks or bool(request.get_data(cache=True))
            _marcar_visto(conn, tecnico["id"],
                          gps_estado="app-sem-posicao" if veio_de_app else "url-testada",
                          gps_erro=_retrato)
            return jsonify({
                "ok": True,
                "url_correta": True,
                "tecnico": tecnico["nome"],
                "mensagem": (f"URL correta, para o técnico {tecnico['nome']}. "
                             "Se você está vendo isto no celular, o endereço e a "
                             "internet funcionam — falta o aplicativo de GPS ter "
                             "permissão de localização O TEMPO TODO."),
            }), 200

        # Mesma régua do GPS do navegador: leitura ruim não é posição, é chute.
        if precisao is not None and precisao > PRECISAO_MAXIMA_M:
            _marcar_visto(conn, tecnico["id"], gps_estado="app-impreciso",
                          gps_erro=_retrato)
            return responder({"ok": True, "gravado": False,
                              "motivo": "posição imprecisa"})

        gravados = _gravar_posicao(conn, tecnico["id"], lat, lng, precisao)

        # Registra que o aparelho está vivo mesmo quando a posição é descartada.
        # É o que responde "o Traccar está configurado certo?" sem depender de
        # haver um atendimento em andamento na hora do teste.
        _marcar_visto(conn, tecnico["id"],
                      gps_estado="owntracks" if eh_owntracks else "rastreador",
                      gps_erro=_retrato)

    return responder({"ok": True, "gravado": gravados > 0,
                      "rastreios": gravados})


@rastreio_bp.route("/t/<token>/rastreios/ativos", methods=["GET"])
def ativos_do_tecnico(token):
    """Rastreios ainda vivos deste técnico. Existe para RETOMAR o envio de GPS.

    Sem isto o rastreio era um evento de uma vez só: o GPS ligava no toque do
    "A caminho" e morria junto com a página. Fechar o app, o celular matar a
    aba por memória, ou a tela travar já bastava para o cliente ficar olhando
    um mapa parado pelo resto da viagem — sem ninguém perceber, porque não
    havia erro nenhum, só silêncio.
    """
    with db_conn() as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        linhas = fetch_all(conn, f"""
            SELECT ra.token, ra.servico_id, ra.criado_em, sv.cliente
              FROM rastreios ra
              JOIN servicos sv ON sv.id = ra.servico_id
             WHERE ra.tecnico_id = ? AND {_ATIVO} AND sv.status <> 'concluido'
             ORDER BY ra.id DESC
        """, (tecnico["id"],))

    return jsonify({"rastreios": [
        {"token": l["token"], "servico_id": l["servico_id"],
         "cliente": l.get("cliente") or ""}
        for l in linhas if not _expirado(l.get("criado_em"))
    ]})


@rastreio_bp.route("/t/<token>/rastreio/<rastreio_token>/posicao", methods=["POST"])
def enviar_posicao(token, rastreio_token):
    """O celular do técnico reporta onde está. É o que faz o carrinho andar.

    Silencioso de propósito: esta rota é chamada de 20 em 20 segundos e nenhum
    erro dela pode virar alerta na tela de quem está dirigindo. Devolve 200 com
    `gravado: false` em vez de erro quando o rastreio já morreu — o app lê isso
    e desliga o GPS sozinho, que é o comportamento certo (parar de gastar
    bateria) e não uma falha a reportar.
    """
    try:
        dados = request.get_json(silent=True) or {}
        lat = float(dados["lat"])
        lng = float(dados["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"erro": "Envie lat e lng numéricos"}), 400

    # Coordenada fora do planeta é erro de leitura do aparelho, não posição.
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return jsonify({"erro": "Coordenada inválida"}), 400

    try:
        precisao = float(dados.get("precisao") or 0) or None
    except (TypeError, ValueError):
        precisao = None

    # Segunda barreira, do lado do servidor. O app já descarta leitura ruim,
    # mas quem grava no banco não pode confiar em quem manda: um app velho em
    # cache (que foi exatamente o problema de 2026-08-14) continuaria mandando
    # posição de Wi-Fi sem precisão nenhuma e o cliente veria bairro errado.
    # `encerrado: False` é essencial aqui: diz ao app "descartei ESTA leitura,
    # continue mandando". Sem essa distinção o app desligaria o GPS de vez na
    # primeira leitura ruim — e leitura ruim acontece o tempo todo, em túnel,
    # garagem e prédio alto.
    if precisao is not None and precisao > PRECISAO_MAXIMA_M:
        return jsonify({"gravado": False, "encerrado": False,
                        "motivo": "posição imprecisa demais"})

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        # O rastreio tem que ser DESTE técnico. Sem esta checagem, quem tivesse
        # um link de técnico moveria o carrinho de qualquer atendimento.
        r = fetch_one(conn, f"""
            SELECT * FROM rastreios
             WHERE token = ? AND tecnico_id = ? AND {_ATIVO}
        """, (rastreio_token, tecnico["id"]))

        if not r or _expirado(r.get("criado_em")):
            # Aqui sim é definitivo: o app deve desligar o GPS.
            return jsonify({"gravado": False, "encerrado": True,
                            "motivo": "rastreio encerrado"})

        # RECALCULA A PREVISÃO A CADA POSIÇÃO.
        #
        # Antes esta rota só gravava onde o técnico estava. O tempo de chegada
        # continuava sendo o calculado na CRIAÇÃO do link — a distância da
        # parada anterior até o cliente, uma previsão de planejamento. O
        # carrinho andava no mapa e o "chega em X min" ficava parado no mesmo
        # número, mesmo que o técnico tivesse pegado trânsito ou desviado.
        #
        # Era esta a maior fonte do erro que o cliente via: não a fórmula, mas
        # o fato de a previsão nunca ser refeita. Agora sai da posição REAL,
        # com o trânsito do momento. O cache de 90s de rota_tempo.py absorve a
        # frequência: esta rota é chamada de 20 em 20 segundos.
        eta = _minutos_ate(conn, r["servico_id"], lat, lng)

        # UPDATE e não INSERT: uma linha por rastreio, sobrescrita. É o que
        # mantém a promessa de não guardar trajeto de funcionário.
        execute(conn, """
            UPDATE rastreios SET lat = ?, lng = ?, precisao = ?,
                   atualizado_em = ?, eta_minutos = COALESCE(?, eta_minutos)
             WHERE id = ?
        """, (lat, lng, precisao, _agora(), eta, r["id"]))

    return jsonify({"gravado": True, "eta_minutos": eta})


@rastreio_bp.route("/t/<token>/rastreio/<rastreio_token>/encerrar", methods=["POST"])
def encerrar(token, rastreio_token):
    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        execute(conn, f"""
            UPDATE rastreios SET ativo = {'FALSE' if IS_PG else '0'}, encerrado_em = ?
             WHERE token = ? AND tecnico_id = ?
        """, (_agora(), rastreio_token, tecnico["id"]))

    return jsonify({"ok": True})


@rastreio_bp.route("/servicos/<int:servico_id>/rastreio", methods=["POST"])
def iniciar_pelo_painel(servico_id):
    """Mesma coisa, mas a partir do painel (sessão de admin).

    Existe porque quem avisa o cliente muitas vezes é o escritório, não o
    técnico. Sem isto o link de acompanhamento só nasceria pelo celular dele.
    """
    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, """
            SELECT sv.id, f.tecnico_id FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id WHERE sv.id = ?
        """, (servico_id,))
        if not servico or not servico.get("tecnico_id"):
            return jsonify({"erro": "Ponto sem técnico atribuído"}), 404

        existente = fetch_one(conn, f"""
            SELECT * FROM rastreios WHERE servico_id = ? AND {_ATIVO} ORDER BY id DESC
        """, (servico_id,))
        if existente and not _expirado(existente.get("criado_em")):
            return jsonify({"token": existente["token"], "reaproveitado": True})

        # Mesma trava do caminho do técnico: abrir daqui também encerra os
        # anteriores dele. Se valesse só num dos dois, o painel reintroduziria
        # o problema que o app acabou de resolver.
        _encerrar_outros_do_tecnico(conn, servico["tecnico_id"], servico_id)

        novo_token = secrets.token_urlsafe(16)
        execute(conn, """
            INSERT INTO rastreios (token, servico_id, tecnico_id, criado_em, eta_minutos)
            VALUES (?, ?, ?, ?, ?)
        """, (novo_token, servico_id, servico["tecnico_id"], _agora(),
              _prever_minutos(conn, servico_id)))

    return jsonify({"token": novo_token, "reaproveitado": False}), 201


@rastreio_bp.route("/rastreio/<rastreio_token>", methods=["GET"])
def consultar(rastreio_token):
    """Leitura PÚBLICA — é o que a página do cliente consome.

    Devolve o mínimo: primeiro nome do técnico, posição atual e o destino.
    Nada de telefone, nome completo, outros pontos da rota ou dados da ficha.
    Quem tem o link é o cliente, não alguém com direito ao resto.
    """
    with db_conn() as conn:
        r = fetch_one(conn, """
            SELECT ra.*, sv.cliente, sv.endereco_completo,
                   sv.lat AS destino_lat, sv.lng AS destino_lng, sv.status AS servico_status,
                   t.nome AS tecnico_nome, t.foto AS tecnico_foto, t.cor AS tecnico_cor
              FROM rastreios ra
              JOIN servicos sv ON sv.id = ra.servico_id
              JOIN tecnicos t  ON t.id = ra.tecnico_id
             WHERE ra.token = ?
        """, (rastreio_token,))

    if not r:
        return jsonify({"erro": "Link de acompanhamento inválido"}), 404

    encerrado = (not r.get("ativo")) or _expirado(r.get("criado_em"))
    primeiro_nome = (r.get("tecnico_nome") or "").split(" ")[0]

    saiu_em = r.get("criado_em")
    eta = r.get("eta_minutos")

    # A contagem começa na ÚLTIMA POSIÇÃO quando existe uma, e só cai na hora
    # da saída quando não há GPS nenhum. Somar o tempo restante ao horário de
    # saída era o que fazia a previsão vencer sozinha enquanto o técnico ainda
    # estava na estrada.
    referencia = r.get("atualizado_em") if r.get("lat") is not None else saiu_em
    chegada = None
    if referencia and eta:
        try:
            base = datetime.strptime(str(referencia)[:19], "%Y-%m-%d %H:%M:%S")
            chegada = (base + timedelta(minutes=int(eta))).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            chegada = None

    # Posição do técnico, com a IDADE calculada no servidor. Mandar a idade em
    # segundos, e não só o horário, evita que o relógio errado do celular do
    # cliente transforme uma posição de agora em "vista há 3 horas" — erro que
    # já aconteceu com data em outro ponto do sistema.
    posicao = None
    if r.get("lat") is not None and r.get("lng") is not None:
        idade = None
        try:
            visto = datetime.strptime(str(r.get("atualizado_em"))[:19],
                                      "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            idade = int((datetime.now(timezone.utc) - visto).total_seconds())
        except (ValueError, TypeError):
            idade = None

        posicao = {
            "lat": r["lat"], "lng": r["lng"],
            "visto_em": r.get("atualizado_em"),
            "idade_seg": idade,
            # A página desenha um círculo com este raio. Mostrar um ponto seco
            # onde há 300m de incerteza é dizer ao cliente uma precisão que o
            # aparelho não tem.
            "precisao": r.get("precisao"),
            # Quem decide se é "ao vivo" é o servidor, não a página: assim a
            # regra é uma só e não depende do relógio de ninguém.
            "ao_vivo": idade is not None and idade <= POSICAO_FRESCA_SEG,
        }

    return jsonify({
        "ativo":     not encerrado,
        "tecnico":   primeiro_nome,
        # A foto do técnico vai para a página do cliente: quem espera em casa
        # abre a porta com mais tranquilidade sabendo QUEM vai chegar. É o
        # mesmo motivo pelo qual aplicativo de corrida mostra o motorista.
        "tecnico_foto": r.get("tecnico_foto"),
        "tecnico_cor":  r.get("tecnico_cor") or "#1a6fd4",
        "cliente":   r.get("cliente") or "",
        "destino":   {"lat": r.get("destino_lat"), "lng": r.get("destino_lng"),
                      "endereco": r.get("endereco_completo") or ""},
        "posicao":   posicao,
        # Horários em UTC; a página converte para o fuso de quem está olhando.
        "saiu_em":   saiu_em,
        "chegada_prevista": chegada,
        "chegou":    r.get("servico_status") == "concluido",
    })


@rastreio_bp.route("/rastreios/<int:rastreio_id>/posicao", methods=["DELETE"])
def limpar_posicao(rastreio_id):
    """Apaga a posição de um rastreio SEM encerrar o link do cliente.

    Existe porque eu contaminei rastreios reais duas vezes em 2026-08-14
    testando o endpoint com coordenada inventada, e a única saída era encerrar
    o link — o que tira do cliente um acompanhamento legítimo por um erro meu.

    Limpar devolve o rastreio ao estado anterior ao GPS: o cliente continua
    vendo a previsão de chegada, só não vê pino. É honesto e não custa nada a
    ele. Fica atrás da sessão de admin.
    """
    with db_conn(commit=True) as conn:
        alterados = execute(conn, """
            UPDATE rastreios
               SET lat = NULL, lng = NULL, precisao = NULL, atualizado_em = NULL
             WHERE id = ?
        """, (rastreio_id,))

    if not alterados:
        return jsonify({"erro": "Rastreio não encontrado"}), 404
    return jsonify({"ok": True, "mensagem": f"Posição do rastreio {rastreio_id} "
                                            "apagada; o link segue válido."})


@rastreio_bp.route("/rastreios/diagnostico", methods=["GET"])
def diagnostico():
    """Rastreios recentes, para saber o que de fato aconteceu no celular.

    Fica atrás da sessão de admin (não tem prefixo público). Existe porque
    "não funcionou" no aparelho de outra pessoa é impossível de investigar sem
    ver se o rastreio nasceu e se alguma posição chegou.
    """
    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT ra.id, ra.token, ra.lat, ra.lng, ra.ativo,
                   ra.criado_em, ra.atualizado_em, ra.encerrado_em,
                   t.nome AS tecnico, sv.cliente
              FROM rastreios ra
              JOIN tecnicos t  ON t.id = ra.tecnico_id
              JOIN servicos sv ON sv.id = ra.servico_id
             ORDER BY ra.id DESC
        """)

        # Estado real do celular de cada técnico, reportado pelo ping de versão.
        # É a metade que faltava do diagnóstico: saber que o rastreio nasceu e
        # não recebeu posição não diz SE o aparelho tem o código novo nem se a
        # localização está liberada — e sem isso o resto é adivinhação.
        aparelhos = fetch_all(conn, """
            SELECT t.id, t.nome, t.token, ts.app_versao, ts.gps_estado,
                   ts.gps_erro, ts.visto_em
              FROM tecnicos t
              LEFT JOIN tecnico_status ts ON ts.tecnico_id = t.id
             ORDER BY t.nome
        """)

    from extensions import VERSAO_APP

    def _resumo_aparelho(a):
        versao = a.get("app_versao")
        # O rastreador nativo torna a versão do navegador irrelevante: ele
        # reporta com o app fechado, que é justamente o que o navegador não faz.
        # "traccar" continua sendo lido porque pode haver registro antigo no
        # banco gravado antes desta separação.
        if a.get("gps_estado") in ("owntracks", "rastreador", "traccar"):
            nome_app = {"owntracks": "OwnTracks"}.get(a.get("gps_estado"),
                                                      "Rastreador")
            situacao = f"{nome_app} enviando — reporta em segundo plano"
        elif a.get("gps_estado") == "url-testada":
            situacao = ("URL testada pelo navegador e correta — falta o "
                        "aplicativo de GPS enviar (permissão/bateria)")
        elif a.get("gps_estado") == "app-impreciso":
            situacao = ("O aplicativo está enviando, mas com precisão pior que "
                        f"{PRECISAO_MAXIMA_M} m — ligue a localização precisa")
        elif a.get("gps_estado") == "app-sem-posicao":
            situacao = ("O aplicativo de GPS chegou até aqui, mas sem posição "
                        "utilizável — verifique a permissão de localização")
        elif not versao:
            situacao = "nunca reportou (app antigo, anterior à v26)"
        elif versao != VERSAO_APP:
            situacao = f"código VELHO ({versao}) — precisa recarregar"
        elif a.get("gps_estado") == "denied":
            situacao = "código atual, mas LOCALIZAÇÃO BLOQUEADA no aparelho"
        elif a.get("gps_estado") == "granted":
            situacao = "tudo certo"
        else:
            situacao = f"código atual, GPS: {a.get('gps_estado') or 'desconhecido'}"
        return {
            "tecnico": a["nome"],
            "app_versao": versao,
            "gps": a.get("gps_estado"),
            "gps_erro": a.get("gps_erro"),
            "visto_em": a.get("visto_em"),
            "situacao": situacao,
            # URL pronta para colar no Traccar Client. Sai daqui e não de um
            # papel porque o token é longo e digitar errado é o jeito mais
            # fácil de a configuração falhar em silêncio.
            "url_rastreador": (request.host_url.rstrip("/")
                               + f"/api/t/{a['token']}/rastreador"),
        }

    return jsonify({
        "servidor_versao": VERSAO_APP,
        "aparelhos": [_resumo_aparelho(a) for a in aparelhos],
        "total": len(linhas),
        "com_posicao": sum(1 for l in linhas if l.get("lat") is not None),
        "rastreios": [{
            "id": l["id"],
            "tecnico": l["tecnico"],
            "cliente": l["cliente"],
            "criado_em": l["criado_em"],
            # A pergunta que decide o diagnóstico: nasceu mas nunca recebeu
            # posição? Então o problema é o GPS do aparelho, não a API.
            "recebeu_posicao": l.get("lat") is not None,
            "atualizado_em": l.get("atualizado_em"),
            "ativo": bool(l.get("ativo")),
        } for l in linhas[:20]],
    })


# A página em si (/acompanhar/<token>) fica no app.py, fora deste blueprint:
# aqui tudo vive sob /api, e a página é HTML que o cliente abre no navegador.


@rastreio_bp.route("/avisos", methods=["GET"])
def avisos():
    """O que precisa de atenção AGORA, numa chamada só.

    Nasceu de um caso real: o Igor tinha atendimento aberto e o celular dele
    parou de mandar posição às 17h do dia anterior. O cliente abria o link e
    não via ninguém — e a Porto Tec só descobriria pela reclamação.

    Junta os dois avisos numa resposta porque o painel já chamava
    `/setores/resumo` para a faixa de pontos sem setor; agora essa mesma
    chamada traz tudo, sem custar mais uma ida ao servidor (o painel roda com
    UM worker, ver siteroteiro-desempenho).
    """
    from routes.auth import e_admin

    saida = {"sem_setor": 0, "rastreio": []}

    with db_conn() as conn:
        orfaos = fetch_one(conn, """
            SELECT COUNT(*) AS total FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id
             WHERE sv.setor_id IS NULL AND f.status <> 'concluida'
        """)
        saida["sem_setor"] = (orfaos or {}).get("total", 0)

        # Atendimento com link aberto e posição velha (ou nenhuma): é o
        # cliente olhando um mapa parado neste exato momento.
        abertos = fetch_all(conn, f"""
            SELECT ra.atualizado_em, sv.cliente, t.nome AS tecnico
              FROM rastreios ra
              JOIN servicos sv ON sv.id = ra.servico_id
              JOIN tecnicos t  ON t.id = ra.tecnico_id
             WHERE {_ATIVO_RA} AND sv.status <> 'concluido'
        """)

    for r in abertos:
        idade = None
        if r.get("atualizado_em"):
            try:
                visto = datetime.strptime(str(r["atualizado_em"])[:19],
                                          "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                idade = (datetime.now(timezone.utc) - visto).total_seconds() / 60
            except ValueError:
                idade = None

        if idade is None:
            motivo = "ainda sem posição"
        elif idade > POSICAO_FRESCA_SEG / 60:
            motivo = f"última posição há {int(idade)} min"
        else:
            continue  # está ao vivo, não é aviso

        saida["rastreio"].append({
            "cliente": r.get("cliente") or "Cliente",
            "tecnico": r.get("tecnico") or "",
            "motivo": motivo,
        })

    # Só admin vê o detalhe do rastreio; o técnico vê apenas o próprio
    # trabalho pendente (sem setor).
    if not e_admin():
        saida["rastreio"] = []

    return jsonify(saida)
