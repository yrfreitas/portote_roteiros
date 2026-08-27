import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

log = logging.getLogger("portotec.tecnico_api")

from database import (db_conn, execute, fetch_all, fetch_one,
                      insert_returning_id, ler_revisao, sql)
from routes.fichas import (STATUS_VALIDOS, ordenar_por_semana,
                           recalcular_distancia_ordem_fixa)
from routes.servicos import STATUS_SERVICO_VALIDOS, aplicar_status_servico

tecnico_api_bp = Blueprint("tecnico_api", __name__)


def _tecnico_por_token(conn, token):
    if not token:
        return None
    return fetch_one(conn, "SELECT * FROM tecnicos WHERE token = ?", (token,))


def _ficha_do_tecnico(conn, ficha_id, tecnico_id):
    return fetch_one(
        conn, "SELECT * FROM fichas WHERE id = ? AND tecnico_id = ?",
        (ficha_id, tecnico_id),
    )


# Espelho do /api/versao para o técnico em campo. Existe separado porque
# /api/versao passa pela sessão de admin e o técnico não tem sessão — o link
# dele é a credencial. Valida o token do mesmo jeito que as demais rotas daqui:
# link inválido não recebe nem o número da revisão.
@tecnico_api_bp.route("/<token>/versao", methods=["GET"])
def versao_tecnico(token):
    """Ping de 20 em 20 segundos. Serve a três coisas ao mesmo tempo.

    Além de dizer se os dados e o código mudaram, ele REGISTRA o que o celular
    respondeu sobre si mesmo (`?app=` e `?gps=`). Isso existe porque diagnosticar
    o app do técnico às cegas custou três rodadas de deploy em 2026-08-14: o
    aparelho rodava código de três versões atrás e nada no servidor revelava
    isso. Aproveitar um ping que já acontece custa zero requisição nova.
    """
    from extensions import VERSAO_APP

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        # Truncado: é campo alimentado pelo cliente e não pode virar porta de
        # entrada para texto arbitrário grande no banco.
        app_versao = (request.args.get("app") or "")[:20] or None
        gps_estado = (request.args.get("gps") or "")[:20] or None
        gps_erro = (request.args.get("gps_erro") or "")[:120] or None

        if app_versao or gps_estado or gps_erro:
            # Mesma função que o rastreador externo usa — uma só regra de
            # gravação para as duas origens.
            from routes.rastreio import _marcar_visto
            _marcar_visto(conn, tecnico["id"], gps_estado=gps_estado,
                          app_versao=app_versao, gps_erro=gps_erro)

        # `revisao` diz que os DADOS mudaram; `app` diz que o CÓDIGO mudou.
        # São perguntas diferentes e o app reage a cada uma de um jeito:
        # recarregar a rota na primeira, recarregar a página na segunda.
        return jsonify({**ler_revisao(conn), "app": VERSAO_APP})


@tecnico_api_bp.route("/<token>/fichas", methods=["GET"])
def fichas_do_tecnico(token):
    with db_conn() as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        fichas = fetch_all(conn, """
            SELECT f.*, COUNT(s.id) AS total_servicos
            FROM fichas f
            LEFT JOIN servicos s ON s.ficha_id = f.id
            WHERE f.tecnico_id = ?
            GROUP BY f.id
        """, (tecnico["id"],))

        # Mesma ordem da semana do painel. O técnico abre o app para saber o
        # que vem hoje; lista embaralhada por "quem foi editado por último"
        # obriga a procurar o próprio dia numa tela pequena.
        fichas = ordenar_por_semana(fichas)

    return jsonify({"tecnico": {"id": tecnico["id"], "nome": tecnico["nome"], "cor": tecnico["cor"]},
                     "fichas": fichas})


@tecnico_api_bp.route("/<token>/fichas/<int:ficha_id>", methods=["GET"])
def detalhe_ficha_tecnico(token, ficha_id):
    with db_conn() as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        ficha = _ficha_do_tecnico(conn, ficha_id, tecnico["id"])
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        # LEFT JOIN para o atendimento sem desfecho continuar aparecendo:
        # concluir sem escolher desfecho é permitido (o técnico pode fechar o
        # app antes), e sumir da lista por isso seria pior que a falta do dado.
        servicos = fetch_all(conn, sql("""
            SELECT s.*, d.desfecho, d.motivo AS desfecho_motivo,
                   d.peca AS desfecho_peca,
                          d.observacao AS desfecho_obs
              FROM servicos s
              LEFT JOIN servico_desfecho d ON d.servico_id = s.id
             WHERE s.ficha_id = ?
             ORDER BY s.ordem, s.id
        """), (ficha_id,))

    return jsonify({"ficha": ficha, "servicos": servicos})


@tecnico_api_bp.route("/<token>/fichas/<int:ficha_id>/status", methods=["PUT"])
def status_ficha_tecnico(token, ficha_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_VALIDOS:
        return jsonify({"erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_VALIDOS))}"}), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        ficha = _ficha_do_tecnico(conn, ficha_id, tecnico["id"])
        if not ficha:
            return jsonify({"erro": "Ficha não encontrada"}), 404

        if novo_status == "concluida":
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (novo_status, ficha_id))
        else:
            execute(conn, """
                UPDATE fichas SET status = ?, concluida_em = NULL,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (novo_status, ficha_id))

    return jsonify({"mensagem": f"Ficha marcada como {novo_status}", "status": novo_status})


@tecnico_api_bp.route("/<token>/servicos/<int:servico_id>/status", methods=["PUT"])
def status_servico_tecnico(token, servico_id):
    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip()

    if novo_status not in STATUS_SERVICO_VALIDOS:
        return jsonify({
            "erro": f"Status inválido. Use um de: {', '.join(sorted(STATUS_SERVICO_VALIDOS))}"
        }), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        servico = fetch_one(conn, """
            SELECT s.* FROM servicos s
            JOIN fichas f ON f.id = s.ficha_id
            WHERE s.id = ? AND f.tecnico_id = ?
        """, (servico_id, tecnico["id"]))
        if not servico:
            return jsonify({"erro": "Serviço não encontrado"}), 404

        aplicar_status_servico(conn, servico_id, novo_status)
        desfecho_gravado = _gravar_desfecho(conn, servico, novo_status,
                                            data.get("desfecho"),
                                            tecnico.get("nome") or "")

    return jsonify({"mensagem": f"Serviço marcado como {novo_status}",
                    "status": novo_status, "desfecho": desfecho_gravado})


# Desfechos possíveis de um atendimento. Lista FECHADA de propósito: o valor
# alimenta contagem e filtro, e texto livre não soma nem filtra.
DESFECHOS_VALIDOS = {"resolvido", "precisa_peca", "volto_depois", "nao_atendido",
                     "cotacao_peca"}

# Desfechos que fazem sentido levar pra um dia futuro (o cliente exige nova
# visita). "resolvido" e "cotacao_peca" terminam o atendimento ali mesmo —
# reagendar não se aplica a eles.
DESFECHOS_REAGENDAVEIS = {"volto_depois", "nao_atendido"}

# Teto por foto. O navegador já reduz para 1280px de lado maior em JPEG antes
# de enviar (ver tecnico.js), o que dá 150–350 KB em base64. 900 KB é folga
# larga para um aparelho que produza imagem mais pesada, sem virar porta para
# despejarem arquivo grande no banco.
FOTO_MAXIMA = 900 * 1024
PREFIXOS_FOTO = ("data:image/jpeg;base64,", "data:image/png;base64,",
                 "data:image/webp;base64,")


def _gravar_foto(conn, servico_id, foto, quem, agora):
    """Guarda a foto da etiqueta do aparelho.

    Existe porque para pedir a peça é preciso o modelo e o número de série,
    que estão na etiqueta — e ditar isso por telefone ou digitar no celular na
    casa do cliente troca caractere. A foto é a fonte.
    """
    if not isinstance(foto, str) or not foto.startswith(PREFIXOS_FOTO):
        return
    if len(foto) > FOTO_MAXIMA:
        log.warning("Foto do serviço %s recusada: %d bytes", servico_id, len(foto))
        return

    execute(conn, sql(
        "INSERT INTO servico_foto (servico_id, foto, legenda, criado_em, "
        "enviado_por) VALUES (?, ?, ?, ?, ?)"),
        (servico_id, foto, "etiqueta", agora, quem))


def _criar_cotacao_do_desfecho(conn, servico_id, codigo, nome_peca, foto, quem):
    """Registro na lista de Cotação de Peças (aba Peças) a partir do que o
    técnico fotografou em campo. É a MESMA tabela que a aba admin lê — o
    técnico não sabe que está alimentando uma "cotação", só está dizendo
    "olha essa peça aqui, preciso saber o preço"."""
    execute(conn, sql("""
        INSERT INTO cotacoes (codigo, descricao, quantidade, criado_em,
                              criado_por, foto, servico_id)
        VALUES (?, ?, 1, ?, ?, ?, ?)
    """), (codigo, nome_peca, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          quem, foto, servico_id))


# Desfecho -> status da OS. Fechado de propósito: "resolvido" encerra,
# peça pendente trava esperando, e reagendamento volta pra fila de Agendar
# Clientes — a mesma leitura que uma pessoa faria olhando o desfecho, só que
# automática.
#
# Até 2026-08-27, "volto_depois"/"nao_atendido" iam direto pra "agendada":
# o PRÓPRIO TÉCNICO escolhia o dia novo ali na hora (blocoReagendar() no
# tecnico.js). Isso saiu — quem decide o dia agora é o escritório, olhando a
# aba Agendar Clientes, não o técnico na calçada com uma mão ocupada. O
# desfecho só marca "precisa de nova visita"; agendar virou ação separada.
_STATUS_OS_POR_DESFECHO = {
    "resolvido": "finalizada",
    "precisa_peca": "aguardando_peca",
    "cotacao_peca": "aguardando_peca",
    "volto_depois": "aguardando_agendamento",
    "nao_atendido": "aguardando_agendamento",
}

_MOTIVO_DESFECHO_ROTULO = {
    "volto_depois": "Técnico esteve no local e vai voltar depois",
    "nao_atendido": "Não atendido — precisa remarcar",
}


def _criar_os_para_reagendamento(servico, tipo, motivo, observacao, quem):
    """Quando o atendimento reagendável NÃO tem OS (ponto adicionado direto
    em Roteiros/Verificar CEP, sem passar pela aba OS), cria uma na hora —
    do contrário esse cliente não tem pra onde ir na aba Agendar Clientes,
    que só lista Ordem de Serviço. Mesma lógica de
    routes/pedidos.py:agendar_cliente() (achar ou cadastrar cliente pelo
    nome): aqui repetida, e não importada, porque os dois pontos de entrada
    (peça chegou vs. técnico não atendeu) não têm por que depender um do
    outro.

    Roda na PRÓPRIA conexão/transação, separada da que grava o desfecho: é
    um efeito colateral (abrir OS), não o registro em si — um erro aqui (CEP
    ruim, nome duplicado, o que for) não pode derrubar a conclusão do
    atendimento, que é o que realmente importa pro técnico em campo. Ver
    chamada em _gravar_desfecho, que também blinda contra exceção.
    """
    cliente_nome = (servico.get("cliente") or "").strip()
    if not cliente_nome:
        return  # sem nome não dá nem pra cadastrar cliente — fica só no log do atendimento

    from routes.clientes import criar_cliente

    with db_conn(commit=True) as conn:
        existente = fetch_one(conn, sql(
            "SELECT id FROM clientes WHERE LOWER(nome) = LOWER(?)"), (cliente_nome,))
        if existente:
            cliente_id = existente["id"]
        else:
            try:
                cliente_id = criar_cliente(conn, {"nome": cliente_nome})
            except ValueError:
                return

        agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        partes_defeito = [_MOTIVO_DESFECHO_ROTULO.get(tipo, "Precisa de nova visita")]
        if motivo:
            partes_defeito.append(motivo)
        if servico.get("descricao"):
            partes_defeito.append(servico["descricao"])

        os_id = insert_returning_id(conn, sql("""
            INSERT INTO ordens_servico
                (cliente_id, atendente, tipo_aparelho, modelo, defeito_declarado,
                 taxa_avaliacao, status, observacao, criado_em, criado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (cliente_id, quem, servico.get("tipo_aparelho") or "",
              servico.get("modelo") or "", " — ".join(partes_defeito), 0,
              "aguardando_agendamento", observacao or "", agora, quem))

        # Amarra o atendimento na OS nova — sem isso não teria como saber, mais
        # tarde, que esse servico já gerou uma OS de reagendamento (evita
        # duplicar se o técnico registrar desfecho de novo no mesmo serviço).
        execute(conn, sql("UPDATE servicos SET ordem_servico_id = ? WHERE id = ?"),
               (os_id, servico["id"]))


def _atualizar_status_os(ordem_servico_id, tipo):
    """Roda em conexão própria — mesmo motivo de _criar_os_para_reagendamento:
    se isso falhar (OS apagada entre uma tela e outra, o que for), não pode
    deixar a transação principal (que já gravou o desfecho) sem como dar
    commit. Ver a chamada em _gravar_desfecho, que blinda os dois."""
    if not ordem_servico_id:
        return
    novo = _STATUS_OS_POR_DESFECHO.get(tipo)
    if not novo:
        return
    # UTC de propósito: ordens_servico.criado_em é gravado em UTC
    # (routes/ordens_servico.py), e a métrica de tempo médio até finalizar
    # compara os dois — hora local aqui faria a duração dar negativa.
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with db_conn(commit=True) as conn:
        if novo == "finalizada":
            execute(conn, sql(
                "UPDATE ordens_servico SET status = ?, atualizado_em = ?, "
                "finalizada_em = ? WHERE id = ?"), (novo, agora, agora, ordem_servico_id))
        else:
            execute(conn, sql(
                "UPDATE ordens_servico SET status = ?, atualizado_em = ? WHERE id = ?"),
                (novo, agora, ordem_servico_id))


def _gravar_desfecho(conn, servico, novo_status, desfecho, quem):
    """Guarda o que aconteceu no atendimento, junto com a conclusão.

    Vem na MESMA requisição do status, e não num endpoint próprio, porque o
    aplicativo do técnico tem fila offline: duas requisições significariam
    que uma pode subir e a outra não, deixando atendimento concluído sem
    desfecho — ou desfecho órfão de um atendimento que voltou a pendente.

    Reabrir o atendimento apaga o desfecho: ele descreve uma conclusão que
    deixou de existir.
    """
    servico_id = servico["id"]
    ordem_servico_id = servico.get("ordem_servico_id")
    if novo_status != "concluido":
        execute(conn, sql("DELETE FROM servico_desfecho WHERE servico_id = ?"),
                (servico_id,))
        return None

    if not isinstance(desfecho, dict):
        return None

    tipo = (desfecho.get("tipo") or "").strip().lower()
    if tipo not in DESFECHOS_VALIDOS:
        return None

    motivo = (desfecho.get("motivo") or "").strip()[:120]
    peca = (desfecho.get("peca") or "").strip()[:200]
    codigo = (desfecho.get("codigo") or "").strip().upper()[:60]
    nome_peca = (desfecho.get("nome_peca") or "").strip()[:200]
    # Observação é COMPLEMENTO das opções, não substituta: as opções dão o
    # número que dá para somar, a observação dá o contexto que só quem esteve
    # lá conhece ("cliente pediu para voltar de manhã", "tomada queimada").
    observacao = (desfecho.get("observacao") or "").strip()[:600]
    foto = desfecho.get("foto")
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Cotação de peça exige código, nome E foto — sem os três não é uma peça
    # identificável, e "identifiquei errado" custa mais caro que recusar aqui
    # e pedir pro técnico tentar de novo com a etiqueta na mão.
    if tipo == "cotacao_peca":
        foto_valida = isinstance(foto, str) and foto.startswith(PREFIXOS_FOTO) \
            and len(foto) <= FOTO_MAXIMA
        if not codigo or not nome_peca or not foto_valida:
            return None
        peca = f"{codigo} — {nome_peca}"

    _gravar_foto(conn, servico_id, foto, quem, agora)

    execute(conn, sql("DELETE FROM servico_desfecho WHERE servico_id = ?"),
            (servico_id,))
    execute(conn, sql(
        "INSERT INTO servico_desfecho (servico_id, desfecho, motivo, peca, "
        "codigo, observacao, registrado_em, registrado_por) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"),
        (servico_id, tipo, motivo, peca, codigo, observacao, agora, quem))

    if tipo == "cotacao_peca":
        _criar_cotacao_do_desfecho(conn, servico_id, codigo, nome_peca, foto, quem)

    # Reagendável com OS: só muda o status, ela reaparece em Agendar Clientes
    # sozinha. Reagendável SEM OS (ponto solto de Roteiros/Verificar CEP):
    # cria uma OS na hora, porque sem OS não existe como aparecer lá — quem
    # marca o dia novo agora é o escritório, não mais o técnico em campo.
    #
    # BLINDADO: o desfecho em si (acima) já está gravado nesta transação —
    # nada daqui pra baixo pode virar "erro interno" pro técnico. Se a OS não
    # sair ou o status não atualizar, fica só logado; dá pra corrigir na mão
    # depois. O que NÃO pode acontecer de novo é o técnico ficar sem
    # conseguir concluir o atendimento por causa de um efeito colateral.
    try:
        if tipo in DESFECHOS_REAGENDAVEIS and not ordem_servico_id:
            _criar_os_para_reagendamento(servico, tipo, motivo, observacao, quem)
        else:
            _atualizar_status_os(ordem_servico_id, tipo)
    except Exception:
        log.exception("Falha ao atualizar OS/criar reagendamento pro serviço %s (tipo=%s)",
                      servico_id, tipo)

    resultado = {"tipo": tipo, "motivo": motivo, "peca": peca, "observacao": observacao}
    return resultado


@tecnico_api_bp.route("/<token>/fichas/<int:ficha_id>/reordenar", methods=["PUT"])
def reordenar_tecnico(token, ficha_id):
    data = request.get_json(silent=True) or {}
    ordem_ids = data.get("ordem_ids")

    if not isinstance(ordem_ids, list) or not ordem_ids:
        return jsonify({"erro": "ordem_ids deve ser uma lista de IDs de serviço"}), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        ficha = _ficha_do_tecnico(conn, ficha_id, tecnico["id"])
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
                "erro": "A lista enviada não corresponde exatamente aos pontos desta ficha."
            }), 409

        for posicao, servico_id in enumerate(ordem_ids, start=1):
            execute(conn, "UPDATE servicos SET ordem = ? WHERE id = ?", (posicao, servico_id))

        resultado = recalcular_distancia_ordem_fixa(conn, ficha_id, ficha)

    return jsonify({"mensagem": "Ordem atualizada manualmente", **resultado})


@tecnico_api_bp.route("/<token>/push/subscribe", methods=["POST"])
def push_subscribe(token):
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth_key = (keys.get("auth") or "").strip()

    if not endpoint or not p256dh or not auth_key:
        return jsonify({"erro": "Subscription incompleta"}), 400

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        existente = fetch_one(
            conn, "SELECT id FROM push_subscriptions WHERE endpoint = ?", (endpoint,)
        )
        if existente:
            execute(conn, """
                UPDATE push_subscriptions SET tecnico_id = ?, p256dh = ?, auth = ?
                WHERE id = ?
            """, (tecnico["id"], p256dh, auth_key, existente["id"]))
        else:
            execute(conn, """
                INSERT INTO push_subscriptions (tecnico_id, endpoint, p256dh, auth)
                VALUES (?, ?, ?, ?)
            """, (tecnico["id"], endpoint, p256dh, auth_key))

    return jsonify({"mensagem": "Notificações ativadas"}), 201


@tecnico_api_bp.route("/<token>/push/subscribe", methods=["DELETE"])
def push_unsubscribe(token):
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()

    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        execute(conn, """
            DELETE FROM push_subscriptions WHERE endpoint = ? AND tecnico_id = ?
        """, (endpoint, tecnico["id"]))

    return jsonify({"mensagem": "Notificações desativadas"})
