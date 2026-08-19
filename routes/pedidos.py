"""Vincular compras de peça (planilha) a clientes, direto pelo site.

A planilha de Pedidos é alimentada automaticamente pelo robô do
porto_tec_panasonic com as compras na CrediPay — mas ela só sabe nota fiscal
e valor. Quem é o cliente final e qual peça é aquilo só a equipe sabe, e até
agora isso teria que ser digitado na mão na planilha.

Aqui a equipe escolhe o cliente de uma lista (os que já existem nas fichas do
site), o que garante que o nome gravado é idêntico ao do site — e aí a
conciliação ao finalizar a rota casa exato em vez de aproximado.
"""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from database import (bump_revisao, db_conn, execute, fetch_all, fetch_one,
                      sql)

log = logging.getLogger("portotec.pedidos")

pedidos_bp = Blueprint("pedidos", __name__)


def _resumo_os(o: dict) -> dict:
    """Só o que a tela precisa mostrar de uma OS. O objeto cru do AgoraOS traz
    ~45 campos, a maioria interna dele — mandar tudo pro browser é peso à toa."""
    if not o:
        return None
    aparelhos = [
        (e.get("modelo") or e.get("descricao") or "").strip()
        for e in (o.get("equipamentos") or [])
    ]
    return {
        "id": o.get("id"),
        "data": (o.get("data") or "")[:10],
        "status": o.get("status"),
        "cliente": (o.get("cliente") or {}).get("nome"),
        "aparelhos": [a for a in aparelhos if a],
    }


def _resumo_previa(p: dict) -> dict:
    return {
        "pode_aplicar": p["pode_aplicar"],
        "pendencias": p["pendencias"],
        "forca": p["forca"],
        "os": _resumo_os(p["os"]),
        "os_candidatas": [_resumo_os(o) for o in p["os_candidatas"]],
        "produto": p["produto"],
        "produto_candidatos": p["produto_candidatos"],
        "qtd": p["qtd"],
        "controla_estoque": p["controla_estoque"],
    }


def _ja_lancada(linha: int):
    """A peça dessa linha já foi pro AgoraOS? Consulta a trava de idempotência."""
    with db_conn() as conn:
        return fetch_one(conn, sql(
            "SELECT id_os, id_item, peca, criado_em FROM pecas_agoraos "
            "WHERE linha_planilha = ?"), (linha,))


def _registrar(linha, cliente, peca, previa, lancado):
    with db_conn(commit=True) as conn:
        execute(conn, sql("""
            INSERT INTO pecas_agoraos
                (linha_planilha, id_os, id_produto_extensao, id_item,
                 cliente, peca, qtd, forca)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (linha, int(previa["os"]["id"]),
               int(previa["produto"]["id_produto_extensao"]),
               str(lancado.get("id_item") or ""), cliente, peca,
               float(lancado.get("qtd") or 1), previa["forca"]))


@pedidos_bp.route("/pedidos/diagnostico", methods=["GET"])
def diagnostico_planilha():
    """Diz o que falta pra integração funcionar, sem expor nenhum segredo.

    ?testar=true também abre a conexão com o e-mail pra confirmar que a
    senha de app é aceita — só dizer que a variável existe não prova nada.
    """
    from services.nfe import diagnostico_imap
    from services.planilha import diagnostico

    testar = str(request.args.get("testar", "")).lower() in ("1", "true", "sim")

    return jsonify({
        "planilha": diagnostico(),
        "email": diagnostico_imap(testar_conexao=testar),
    })


@pedidos_bp.route("/pedidos", methods=["GET"])
def listar():
    """Compras de peça. ?todos=true traz também as já vinculadas."""
    from services.planilha import (faltando_para_configurar, listar_pedidos,
                                   planilha_configurada)

    if not planilha_configurada():
        falta = faltando_para_configurar()
        return jsonify({
            "erro": "Integração com a planilha não está configurada. "
                    "Falta: " + "; ".join(falta),
            "faltando": falta,
            "configurada": False,
        }), 503

    todos = str(request.args.get("todos", "")).lower() in ("1", "true", "sim")

    try:
        pedidos = listar_pedidos(apenas_pendentes=not todos)
    except Exception as exc:
        log.exception("Falha ao listar pedidos da planilha")
        return jsonify({"erro": f"Falha ao ler a planilha: {exc}"}), 502

    # A sugestão de peça NÃO é feita aqui de propósito: ler os XMLs das notas
    # por IMAP levava 24s e a tela ficava travada em "carregando" (e o Railway
    # cortaria a requisição). Vem por /pedidos/sugestoes, chamado depois que a
    # lista já apareceu.
    for p in pedidos:
        p["peca_sugerida"] = ""
        p["itens_nota"] = []

    # Junta a chegada física. A planilha sabe até "Enviado"; quem recebe a
    # caixa é que sabe que chegou, e essa informação só existia na memória de
    # quem abriu o pacote.
    chaves = [(p.get("nota_fiscal") or ("PED" + (p.get("pedido") or ""))) for p in pedidos]
    chegadas = {}
    if chaves:
        with db_conn() as conn:
            marcadores = ",".join(["?"] * len(chaves))
            for l in fetch_all(
                conn,
                sql(f"SELECT chave, chegou_em, observacao FROM pecas_chegada "
                    f"WHERE chave IN ({marcadores})"),
                tuple(chaves),
            ):
                chegadas[l["chave"]] = l
    for p, chave in zip(pedidos, chaves):
        registro = chegadas.get(chave)
        p["chave"] = chave
        p["chegou_em"] = (registro or {}).get("chegou_em") or ""
        p["chegou_obs"] = (registro or {}).get("observacao") or ""

    # Clientes já cadastrados no site, pra oferecer como lista de escolha —
    # escolher em vez de digitar é o que faz a conciliação casar exato depois.
    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT DISTINCT s.cliente, s.tipo_aparelho, s.modelo
              FROM servicos s
             WHERE s.cliente IS NOT NULL AND TRIM(s.cliente) <> ''
             ORDER BY s.cliente
        """)

    clientes = [
        {"nome": l["cliente"],
         "aparelho": l.get("tipo_aparelho") or "",
         "modelo": l.get("modelo") or ""}
        for l in linhas
    ]

    from services.nfe import imap_configurado as _imap_ok

    return jsonify({
        "configurada": True,
        "pedidos": pedidos,
        "clientes": clientes,
        "sugestao_peca_ativa": _imap_ok(),
        "pendentes": sum(1 for p in pedidos if not p["cliente_final"]),
    })


@pedidos_bp.route("/pedidos/sugestoes", methods=["GET"])
def sugerir_pecas():
    """Peças lidas do XML da NF-e, por chave de nota.

    Separado da listagem porque ler os XMLs por IMAP é lento (~24s pra 18
    notas): a tela mostra a lista na hora e preenche as sugestões quando
    chegarem, em vez de ficar travada carregando.
    """
    from services.nfe import imap_configurado, pecas_por_nota

    if not imap_configurado():
        return jsonify({"ativo": False, "sugestoes": {}})

    chaves = [c.strip() for c in (request.args.get("notas") or "").split(",") if c.strip()]
    if not chaves:
        return jsonify({"ativo": True, "sugestoes": {}})

    # Trava de segurança: uma requisição não pode varrer a caixa inteira.
    chaves = chaves[:40]

    try:
        achadas = pecas_por_nota(chaves)
    except Exception:
        log.exception("Falha ao buscar peças nas notas fiscais")
        return jsonify({"ativo": True, "sugestoes": {}, "erro": True})

    return jsonify({
        "ativo": True,
        "sugestoes": {k: v["resumo"] for k, v in achadas.items()},
    })


@pedidos_bp.route("/pedidos/revisar", methods=["GET"])
def revisar():
    """Baixas que casaram só pelo nome (as amarelas), pra conferência.

    Casar só por nome é o elo mais fraco — dois clientes homônimos, ou o
    mesmo nome em compras diferentes, dariam baixa na linha errada. Ficam
    marcadas de amarelo na planilha; aqui dá pra revisar sem caçar na mão.
    """
    from services.planilha import listar_conciliadas_fracas, planilha_configurada

    if not planilha_configurada():
        return jsonify({"itens": [], "configurada": False})

    try:
        return jsonify({"configurada": True, "itens": listar_conciliadas_fracas()})
    except Exception as exc:
        log.exception("Falha ao listar conciliações para revisão")
        return jsonify({"erro": f"Falha ao ler a planilha: {exc}"}), 502


@pedidos_bp.route("/pedidos/<int:linha>/desfazer", methods=["PUT"])
def desfazer(linha):
    """Tira a baixa de uma linha — quando a revisão mostra que casou errado."""
    from services.planilha import desfazer_baixa, planilha_configurada

    if not planilha_configurada():
        return jsonify({"erro": "Integração com a planilha não está configurada."}), 503
    if linha < 2:
        return jsonify({"erro": "Linha inválida"}), 400

    try:
        desfazer_baixa(linha)
    except Exception as exc:
        log.exception("Falha ao desfazer baixa na linha %s", linha)
        return jsonify({"erro": f"Falha ao gravar na planilha: {exc}"}), 502

    return jsonify({"mensagem": f"Baixa desfeita na linha {linha}"})


@pedidos_bp.route("/pedidos/pendentes", methods=["GET"])
def contar_pendentes():
    """Só a contagem, pro selo na aba. Não lê e-mail nem sugere peça —
    é chamado no carregamento da página e precisa ser barato."""
    from services.planilha import listar_pedidos, planilha_configurada

    if not planilha_configurada():
        return jsonify({"pendentes": 0, "configurada": False})

    try:
        return jsonify({
            "pendentes": len(listar_pedidos(apenas_pendentes=True)),
            "configurada": True,
        })
    except Exception:
        log.exception("Falha ao contar peças pendentes")
        return jsonify({"pendentes": 0, "configurada": True, "erro": True})


@pedidos_bp.route("/pedidos/<int:linha>", methods=["PUT"])
def vincular(linha):
    from services.planilha import atualizar_pedido, planilha_configurada

    if not planilha_configurada():
        return jsonify({"erro": "Integração com a planilha não está configurada."}), 503

    data = request.get_json(silent=True) or {}
    cliente = (data.get("cliente") or "").strip()
    peca = (data.get("peca") or "").strip()
    numero_os = (data.get("numero_os") or "").strip()

    if not cliente:
        return jsonify({"erro": "Informe o cliente"}), 400
    if linha < 2:
        return jsonify({"erro": "Linha inválida (a 1 é o cabeçalho)"}), 400

    try:
        atualizar_pedido(linha, cliente, peca, numero_os)
    except Exception as exc:
        log.exception("Falha ao vincular pedido na linha %s", linha)
        return jsonify({"erro": f"Falha ao gravar na planilha: {exc}"}), 502

    # A planilha já está gravada — o AgoraOS é bônus e NUNCA pode derrubar o
    # vínculo. Por isso vem depois, dentro de try, e uma falha aqui só vira
    # aviso na resposta: o trabalho do usuário não se perde por causa do ERP.
    resposta = {"mensagem": f"Peça vinculada a {cliente}", "linha": linha}
    resposta["agoraos"] = _tentar_lancar(linha, cliente, peca, numero_os,
                                         (data.get("modelo") or "").strip(),
                                         data.get("qtd") or 1)
    return jsonify(resposta)


def _tentar_lancar(linha, cliente, peca, numero_os, modelo="", qtd=1):
    """Lança a peça no AgoraOS quando — e só quando — não há ambiguidade.

    Por que automático em vez de sempre perguntar: o Kalebe vincula peça em
    lote e uma confirmação por linha inviabiliza o uso. Por que não automático
    sempre: a API não apaga item de OS, então casamento duvidoso vira prévia
    em vez de estrago. É a mesma escada de confiança da conciliação da rota,
    que já provou funcionar.
    """
    from services import agoraos

    if not agoraos.configurado():
        return {"ativo": False}

    ja = _ja_lancada(linha)
    if ja:
        return {"ativo": True, "estado": "ja_lancada",
                "mensagem": f"Já estava lançada na OS {ja['id_os']} do AgoraOS",
                "id_os": ja["id_os"], "id_item": ja["id_item"]}

    try:
        previa = agoraos.preparar(cliente, peca, numero_os, modelo, qtd)
    except Exception as exc:
        log.exception("AgoraOS: falha ao preparar lançamento da linha %s", linha)
        return {"ativo": True, "estado": "erro", "mensagem": str(exc)}

    if not previa["pode_aplicar"]:
        return {"ativo": True, "estado": "revisar",
                "mensagem": "; ".join(previa["pendencias"]),
                "previa": _resumo_previa(previa)}

    try:
        lancado = agoraos.lancar_item(previa["os"]["id"],
                                      previa["produto"]["id_produto_extensao"], qtd)
        _registrar(linha, cliente, peca, previa, lancado)
    except Exception as exc:
        log.exception("AgoraOS: falha ao lançar peça da linha %s", linha)
        return {"ativo": True, "estado": "erro", "mensagem": str(exc)}

    aviso = None
    if not previa["controla_estoque"]:
        # Dito na cara: o item entrou na OS, mas não reduziu saldo — porque
        # nenhum produto do AgoraOS está com controle de estoque ligado.
        aviso = ("Lançado na OS, mas o produto está sem controle de estoque "
                 "no AgoraOS — não reduziu saldo.")

    return {"ativo": True, "estado": "lancada", "forca": previa["forca"],
            "id_os": previa["os"]["id"], "id_item": lancado.get("id_item"),
            "produto": previa["produto"]["nome"], "aviso": aviso or lancado.get("aviso"),
            "mensagem": f"Lançada na OS {previa['os']['id']} do AgoraOS"}


@pedidos_bp.route("/pedidos/<int:linha>/agoraos/previa", methods=["POST"])
def previa_agoraos(linha):
    """Mostra o que seria lançado, sem gravar nada. É a tela de decisão."""
    from services import agoraos

    if not agoraos.configurado():
        return jsonify({"configurada": False,
                        "faltando": agoraos.faltando_para_configurar()}), 503

    data = request.get_json(silent=True) or {}
    ja = _ja_lancada(linha)
    if ja:
        return jsonify({"configurada": True, "ja_lancada": True,
                        "id_os": ja["id_os"], "id_item": ja["id_item"],
                        "criado_em": ja["criado_em"]})

    try:
        previa = agoraos.preparar(
            (data.get("cliente") or "").strip(),
            (data.get("peca") or "").strip(),
            (data.get("numero_os") or "").strip(),
            (data.get("modelo") or "").strip(),
            data.get("qtd") or 1,
        )
    except Exception as exc:
        log.exception("AgoraOS: prévia falhou na linha %s", linha)
        return jsonify({"erro": str(exc)}), 502

    return jsonify({"configurada": True, "ja_lancada": False,
                    **_resumo_previa(previa)})


@pedidos_bp.route("/pedidos/<int:linha>/agoraos", methods=["POST"])
def lancar_agoraos(linha):
    """Lança de verdade, com OS e produto ESCOLHIDOS na tela.

    Rota separada da prévia de propósito: aqui o id da OS e o do produto vêm
    explícitos do cliente, não de adivinhação. É o caminho de quem revisou uma
    ambiguidade e decidiu — o único jeito de lançar num caso duvidoso.
    """
    from services import agoraos

    if not agoraos.configurado():
        return jsonify({"erro": "AgoraOS não configurado. Falta: " +
                        ", ".join(agoraos.faltando_para_configurar())}), 503

    data = request.get_json(silent=True) or {}
    id_os = data.get("id_os")
    id_prod = data.get("id_produto_extensao")
    if not id_os or not id_prod:
        return jsonify({"erro": "Informe id_os e id_produto_extensao"}), 400

    if _ja_lancada(linha):
        return jsonify({"erro": "Essa linha já foi lançada no AgoraOS. "
                                "A API não apaga item de OS — remova por lá "
                                "antes de lançar de novo."}), 409

    qtd = float(data.get("qtd") or 1)
    try:
        lancado = agoraos.lancar_item(id_os, id_prod, qtd)
    except Exception as exc:
        log.exception("AgoraOS: falha ao lançar linha %s escolhida na mão", linha)
        return jsonify({"erro": str(exc)}), 502

    # Registro montado à mão porque aqui a escolha foi humana: a "força" do
    # casamento é justamente ter sido uma pessoa que decidiu.
    _registrar(linha, (data.get("cliente") or "").strip(),
               (data.get("peca") or "").strip(),
               {"os": {"id": id_os},
                "produto": {"id_produto_extensao": id_prod},
                "forca": "escolha manual"},
               lancado)

    return jsonify({"mensagem": f"Peça lançada na OS {id_os} do AgoraOS",
                    "id_os": id_os, "id_item": lancado.get("id_item"),
                    "aviso": lancado.get("aviso")})


@pedidos_bp.route("/pedidos/agoraos/diagnostico", methods=["GET"])
def diagnostico_agoraos():
    """Estado da integração com o AgoraOS, sem expor senha."""
    from services import agoraos
    return jsonify(agoraos.diagnostico())


@pedidos_bp.route("/pedidos/lote", methods=["PUT"])
def vincular_lote():
    """Vincula várias linhas de uma vez. Cada item: {linha, cliente, peca}.

    Grava uma por uma e relata individualmente: se a 3ª falhar, as duas
    primeiras continuam valendo e o usuário vê exatamente qual não foi.
    """
    from services.planilha import atualizar_pedido, planilha_configurada

    if not planilha_configurada():
        return jsonify({"erro": "Integração com a planilha não está configurada."}), 503

    itens = (request.get_json(silent=True) or {}).get("itens") or []
    if not isinstance(itens, list) or not itens:
        return jsonify({"erro": "Nada para vincular"}), 400

    gravados, falhas = [], []
    lancadas, revisar = [], []
    for item in itens:
        try:
            linha = int(item.get("linha"))
        except (TypeError, ValueError):
            falhas.append({"linha": item.get("linha"), "erro": "linha inválida"})
            continue

        cliente = (item.get("cliente") or "").strip()
        if not cliente or linha < 2:
            falhas.append({"linha": linha, "erro": "cliente vazio ou linha inválida"})
            continue

        peca = (item.get("peca") or "").strip()
        numero_os = (item.get("numero_os") or "").strip()

        try:
            atualizar_pedido(linha, cliente, peca, numero_os)
            gravados.append(linha)
        except Exception as exc:
            log.exception("Falha ao vincular linha %s em lote", linha)
            falhas.append({"linha": linha, "erro": str(exc)})
            continue

        # Mesma regra do vínculo individual: o AgoraOS entra depois da
        # planilha e não derruba nada. Em lote isso importa mais ainda —
        # 20 linhas não podem parar porque uma peça não existe no catálogo.
        r = _tentar_lancar(linha, cliente, peca, numero_os,
                           (item.get("modelo") or "").strip(),
                           item.get("qtd") or 1)
        if r.get("estado") in ("revisar", "erro"):
            revisar.append({"linha": linha, "motivo": r.get("mensagem")})
        elif r.get("estado") == "lancada":
            lancadas.append(linha)

    mensagem = f"{len(gravados)} peça(s) vinculada(s)"
    if falhas:
        mensagem += f", {len(falhas)} com erro"
    if lancadas:
        mensagem += f", {len(lancadas)} lançada(s) no AgoraOS"
    if revisar:
        mensagem += f", {len(revisar)} para revisar"

    return jsonify({
        "gravados": gravados,
        "falhas": falhas,
        "lancadas_agoraos": lancadas,
        "revisar_agoraos": revisar,
        "mensagem": mensagem,
    })


@pedidos_bp.route("/pedidos/chegada", methods=["POST"])
def marcar_chegada():
    """Registra que a peça chegou fisicamente na oficina — ou desfaz.

    Existe porque o último estado que a Panasonic informa é "Enviado", e entre
    o envio e a peça na mão passam dias. Quem vai reagendar a visita do técnico
    não pergunta "foi enviada?", pergunta "chegou?". Sem isso, a resposta
    dependia de alguém lembrar de ter aberto a caixa.
    """
    data = request.get_json(silent=True) or {}
    chave = (data.get("chave") or "").strip()
    if not chave:
        return jsonify({"erro": "chave é obrigatória"}), 400

    chegou = bool(data.get("chegou", True))
    observacao = (data.get("observacao") or "").strip()[:300]
    quem = (session.get("usuario_nome") or "").strip()[:80]

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_conn(commit=True) as conn:
        if not chegou:
            # Desmarcar APAGA a linha em vez de gravar chegou_em vazio: marcar
            # por engano e desfazer tem que voltar ao estado anterior de fato,
            # não deixar um registro fantasma que confunde a leitura depois.
            execute(conn, sql("DELETE FROM pecas_chegada WHERE chave = ?"), (chave,))
            bump_revisao(conn)
            return jsonify({"chave": chave, "chegou_em": ""})

        ja = fetch_one(conn, sql("SELECT chave FROM pecas_chegada WHERE chave = ?"),
                       (chave,))
        if ja:
            execute(conn, sql(
                "UPDATE pecas_chegada SET chegou_em = ?, observacao = ?, "
                "registrado_por = ? WHERE chave = ?"),
                (agora, observacao, quem, chave))
        else:
            execute(conn, sql(
                "INSERT INTO pecas_chegada (chave, chegou_em, observacao, "
                "registrado_por) VALUES (?, ?, ?, ?)"),
                (chave, agora, observacao, quem))
        bump_revisao(conn)

    return jsonify({"chave": chave, "chegou_em": agora, "registrado_por": quem})
