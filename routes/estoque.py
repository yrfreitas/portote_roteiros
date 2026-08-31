"""Estoque de peças — o SITE é o dono do saldo.

POR QUE ISTO EXISTE, e não no AgoraOS:
a API do AgoraOS lê estoque mas não deixa escrever — não liga o controle nem
dá entrada de saldo (testado exaustivamente em 2026-08). Então a "baixa de
peça" que já existe lá dentro nunca reduzia nada. Aqui o saldo é do site:
entra quando a peça é comprada e sai quando é usada.

DUAS REGRAS QUE DEFINEM TUDO:

1. NADA MEXE NO SALDO SEM DEIXAR MOVIMENTO. Toda entrada, saída e ajuste grava
   uma linha em estoque_movimentos com o saldo daquele instante. Um saldo sem
   histórico é impossível de auditar — a pergunta "de onde veio esse número?"
   fica sem resposta, e é a primeira que se faz quando o estoque não bate.

2. CUSTO MÉDIO PONDERADO na entrada. Comprar 2 placas a R$ 300 e depois 3 a
   R$ 400 não dá "R$ 400 cada" nem "R$ 350 na média simples": dá
   (2×300 + 3×400) / 5 = R$ 360. É o número certo para saber quanto vale o
   estoque parado e quanto custou a peça que saiu. A média simples mentiria
   sempre que os preços variassem — e eles variam.
"""
import logging
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import IS_PG, db_conn, execute, fetch_all, fetch_one, insert_returning_id
from services.fotos_extra import (adicionar_foto_extra, listar_fotos_extra,
                                  remover_foto_extra)

log = logging.getLogger("portotec.estoque")

estoque_bp = Blueprint("estoque", __name__)

FOTO_MAXIMA = 900 * 1024
PREFIXOS_FOTO = ("data:image/jpeg;base64,", "data:image/png;base64,",
                 "data:image/webp;base64,")


def _foto_valida(foto):
    if not isinstance(foto, str) or not foto.startswith(PREFIXOS_FOTO):
        return None
    if len(foto) > FOTO_MAXIMA:
        return None
    return foto


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _autor():
    return session.get("usuario_nome") or "Administrador"


def _norm_codigo(c):
    return (c or "").strip().upper()


def _registrar_movimento(conn, item_id, tipo, qtd, saldo_apos,
                         custo_unit=None, origem="manual", referencia=None, obs=None):
    execute(conn, """
        INSERT INTO estoque_movimentos
            (item_id, tipo, quantidade, saldo_apos, custo_unit, origem,
             referencia, autor, obs, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_id, tipo, qtd, saldo_apos, custo_unit, origem, referencia,
          _autor(), obs, _agora()))


def _num_ou_none(v):
    """Converte para float; devolve None quando vazio — para a entrada poder
    dizer 'não mexi nesse campo' e o COALESCE preservar o que já estava."""
    if v is None or v == "":
        return None
    return max(0.0, float(v))


def dar_entrada(conn, codigo, descricao, quantidade, custo_unit=0.0,
                origem="manual", referencia=None, obs=None,
                marca=None, aparelho=None, modelo=None, preco_venda=None,
                grupo_id="__manter__"):
    """Entra peça no estoque, recalculando o custo médio ponderado.

    Reaproveitável de fora (é o que a NF-e vai chamar, fase 2), por isso recebe
    a conexão: entra na mesma transação de quem chamou, e não sobra entrada de
    um processo que falhou no meio.

    marca/aparelho/modelo/preco_venda são opcionais e, quando a peça já existe,
    só sobrescrevem se vierem preenchidos — reentrar uma peça não apaga a
    categoria que ela já tinha.
    """
    codigo = _norm_codigo(codigo)
    if not codigo:
        raise ValueError("Código da peça é obrigatório")
    quantidade = float(quantidade)
    if quantidade <= 0:
        raise ValueError("Quantidade tem que ser maior que zero")
    custo_unit = max(0.0, float(custo_unit or 0))

    marca = (marca or "").strip()
    aparelho = (aparelho or "").strip()
    modelo = (modelo or "").strip()
    preco_venda = _num_ou_none(preco_venda)
    # grupo_id usa sentinela "__manter__": ausente = não mexe no grupo atual
    # (reentrada não desprende a peça da prateleira). Presente (int ou None)
    # = define explicitamente, inclusive tirar do grupo com None.
    mexer_grupo = grupo_id != "__manter__"
    grupo_final = (int(grupo_id) if (mexer_grupo and grupo_id) else None)

    item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE codigo = ?", (codigo,))

    # Pedido de 2026-08-29: a Panasonic às vezes reemite a MESMA peça com um
    # código novo (planilha de substituição, carregada na aba Cotação de
    # peças). Sem checar isso, bipar uma nota com o código novo abria um
    # item de estoque SEPARADO do antigo, e o saldo de uma peça só ficava
    # dividido em dois — junta no item que já existe em vez de duplicar.
    if item is None:
        substituicao = fetch_one(conn, """
            SELECT codigo FROM pecas_substituicao
             WHERE substituto_1 = ? OR substituto_2 = ? OR substituto_3 = ?
                OR substituto_4 = ? OR substituto_5 = ?
             LIMIT 1
        """, (codigo, codigo, codigo, codigo, codigo))
        if substituicao:
            item_original = fetch_one(conn, "SELECT * FROM estoque_itens WHERE codigo = ?",
                                      (substituicao["codigo"],))
            if item_original:
                item = item_original
                nota_substituicao = (f"entrou como {codigo} — substituição do código "
                                     f"{item_original['codigo']} (planilha Panasonic)")
                obs = f"{obs}; {nota_substituicao}" if obs else nota_substituicao

    if item is None:
        novo_id = insert_returning_id(conn, """
            INSERT INTO estoque_itens
                (codigo, descricao, marca, aparelho, modelo, grupo_id, saldo,
                 custo_medio, preco_venda, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, (descricao or "").strip(), marca, aparelho, modelo,
              grupo_final if mexer_grupo else None,
              quantidade, custo_unit, preco_venda or 0, _agora(), _agora()))
        _registrar_movimento(conn, novo_id, "entrada", quantidade, quantidade,
                             custo_unit, origem, referencia, obs)
        return {"item_id": novo_id, "saldo": quantidade, "custo_medio": custo_unit,
                "criado": True}

    saldo_antigo = float(item["saldo"] or 0)
    custo_antigo = float(item["custo_medio"] or 0)
    saldo_novo = saldo_antigo + quantidade

    # Custo médio ponderado. Só recalcula quando a entrada TEM custo — entrada
    # a custo zero (ex: brinde, ajuste) não pode zerar o custo do que já
    # estava lá, senão o valor do estoque despencaria de graça.
    if custo_unit > 0:
        custo_novo = (saldo_antigo * custo_antigo + quantidade * custo_unit) / saldo_novo
    else:
        custo_novo = custo_antigo

    # grupo_id fora do COALESCE porque NULL é um valor válido (tirar do grupo),
    # não "não informado" — por isso o if em vez de truque de SQL.
    set_grupo = ", grupo_id = ?" if mexer_grupo else ""
    params = [saldo_novo, custo_novo, _agora(), (descricao or "").strip(),
              marca, aparelho, modelo, preco_venda]
    if mexer_grupo:
        params.append(grupo_final)
    params.append(item["id"])
    execute(conn, f"""
        UPDATE estoque_itens
           SET saldo = ?, custo_medio = ?, atualizado_em = ?,
               descricao   = COALESCE(NULLIF(?, ''), descricao),
               marca       = COALESCE(NULLIF(?, ''), marca),
               aparelho    = COALESCE(NULLIF(?, ''), aparelho),
               modelo      = COALESCE(NULLIF(?, ''), modelo),
               preco_venda = COALESCE(?, preco_venda){set_grupo}
         WHERE id = ?
    """, params)
    _registrar_movimento(conn, item["id"], "entrada", quantidade, saldo_novo,
                        custo_unit, origem, referencia, obs)
    return {"item_id": item["id"], "saldo": saldo_novo, "custo_medio": custo_novo,
            "criado": False}


def dar_saida(conn, codigo, quantidade, origem="manual", referencia=None,
              obs=None, permitir_negativo=False):
    """Baixa peça do estoque. Devolve o item ou levanta erro."""
    codigo = _norm_codigo(codigo)
    item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE codigo = ?", (codigo,))
    if item is None:
        raise ValueError(f"Peça {codigo} não existe no estoque")

    quantidade = float(quantidade)
    if quantidade <= 0:
        raise ValueError("Quantidade tem que ser maior que zero")

    saldo_antigo = float(item["saldo"] or 0)
    saldo_novo = saldo_antigo - quantidade
    # Trava contra saldo negativo: baixar mais do que existe quase sempre é
    # erro de digitação. `permitir_negativo` fica para o dia em que a baixa
    # automática precisar registrar consumo mesmo sem entrada lançada.
    if saldo_novo < 0 and not permitir_negativo:
        raise ValueError(
            f"Saldo insuficiente: há {saldo_antigo:g} em estoque e a saída é de {quantidade:g}")

    execute(conn, "UPDATE estoque_itens SET saldo = ?, atualizado_em = ? WHERE id = ?",
            (saldo_novo, _agora(), item["id"]))
    _registrar_movimento(conn, item["id"], "saida", quantidade, saldo_novo,
                        float(item["custo_medio"] or 0), origem, referencia, obs)
    return {"item_id": item["id"], "saldo": saldo_novo}


# ─── API ────────────────────────────────────────────────────────────────
@estoque_bp.route("/estoque", methods=["GET"])
def listar():
    """Todos os itens, com o alerta de mínimo já resolvido. `busca` filtra por
    código/descrição/marca/modelo; `aparelho` e `marca` filtram por categoria.
    Devolve também a lista de aparelhos e marcas existentes para montar os
    filtros da tela sem uma segunda chamada."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401

    busca = (request.args.get("busca") or "").strip().lower()
    f_aparelho = (request.args.get("aparelho") or "").strip().lower()
    f_marca = (request.args.get("marca") or "").strip().lower()
    # grupo_id: id do estoque para ver só as peças dele. "sem" = as soltas.
    f_grupo = (request.args.get("grupo_id") or "").strip()

    with db_conn() as conn:
        itens = fetch_all(conn, """
            SELECT e.*, s.nome AS setor_nome, s.cor AS setor_cor,
                   g.nome AS grupo_nome, g.cor AS grupo_cor
              FROM estoque_itens e
              LEFT JOIN setores s ON s.id = e.setor_id
              LEFT JOIN estoque_grupos g ON g.id = e.grupo_id
             ORDER BY e.aparelho, e.marca, e.descricao, e.codigo
        """)

    # Catálogos de categoria vêm do universo COMPLETO (antes de filtrar), senão
    # escolher "Geladeira" faria as outras opções sumirem do próprio filtro.
    aparelhos = sorted({(i.get("aparelho") or "").strip() for i in itens if (i.get("aparelho") or "").strip()},
                       key=str.lower)
    marcas = sorted({(i.get("marca") or "").strip() for i in itens if (i.get("marca") or "").strip()},
                    key=str.lower)

    if busca:
        itens = [i for i in itens
                 if busca in (i.get("codigo") or "").lower()
                 or busca in (i.get("descricao") or "").lower()
                 or busca in (i.get("marca") or "").lower()
                 or busca in (i.get("modelo") or "").lower()]
    if f_aparelho:
        itens = [i for i in itens if (i.get("aparelho") or "").lower() == f_aparelho]
    if f_marca:
        itens = [i for i in itens if (i.get("marca") or "").lower() == f_marca]
    if f_grupo == "sem":
        itens = [i for i in itens if not i.get("grupo_id")]
    elif f_grupo:
        itens = [i for i in itens if str(i.get("grupo_id") or "") == f_grupo]

    for i in itens:
        i["abaixo_minimo"] = (float(i.get("minimo") or 0) > 0
                              and float(i.get("saldo") or 0) <= float(i["minimo"]))
        i["valor_total"] = round(float(i.get("saldo") or 0) * float(i.get("custo_medio") or 0), 2)

    return jsonify({
        "itens": itens,
        "total_itens": len(itens),
        "abaixo_minimo": sum(1 for i in itens if i["abaixo_minimo"]),
        "valor_investido": round(sum(i["valor_total"] for i in itens), 2),
        "aparelhos": aparelhos,
        "marcas": marcas,
    })


# ─── Estoques (grupos / prateleiras) ──────────────────────────────────────
@estoque_bp.route("/estoque/grupos", methods=["GET"])
def listar_grupos():
    """Os estoques criados, cada um com os agregados das peças dentro dele
    (nº de peças, valor investido, quantas abaixo do mínimo), mais o balde
    'Sem estoque' das peças ainda não guardadas em nenhum. É a tela-raiz."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401

    with db_conn() as conn:
        grupos = fetch_all(conn, "SELECT * FROM estoque_grupos ORDER BY nome")
        itens = fetch_all(conn, "SELECT grupo_id, saldo, custo_medio, minimo FROM estoque_itens")

    # Mapa pai -> filhos, para roll-up e contagem de sub-estoques.
    filhos = {}
    for g in grupos:
        filhos.setdefault(g.get("parent_id"), []).append(g["id"])

    def subtree(gid):
        """ids do grupo + todos os descendentes (o estoque e seus sub-estoques)."""
        acc, pilha = {gid}, [gid]
        while pilha:
            for c in filhos.get(pilha.pop(), []):
                if c not in acc:
                    acc.add(c); pilha.append(c)
        return acc

    def agrega(ids):
        sel = [i for i in itens if i["grupo_id"] in ids]
        return {
            "total_pecas": len(sel),
            "valor_investido": round(sum(float(i["saldo"] or 0) * float(i["custo_medio"] or 0) for i in sel), 2),
            "abaixo_minimo": sum(1 for i in sel
                                 if float(i["minimo"] or 0) > 0 and float(i["saldo"] or 0) <= float(i["minimo"])),
        }

    for g in grupos:
        # Roll-up: o card da Panasonic soma tudo que está sob ela, sub-estoques
        # inclusive — é o total que faz sentido ver de fora.
        g.update(agrega(subtree(g["id"])))
        g["sub_estoques"] = len(filhos.get(g["id"], []))

    sem = agrega({None})  # peças sem estoque nenhum
    return jsonify({"grupos": grupos, "sem_estoque": sem})


@estoque_bp.route("/estoque/grupos", methods=["POST"])
def criar_grupo():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Dê um nome ao estoque"}), 400
    # parent_id define se é um estoque de topo (None) ou um sub-estoque.
    parent_id = int(d["parent_id"]) if d.get("parent_id") else None
    with db_conn(commit=True) as conn:
        # Unicidade POR PAI: 'Geladeira' pode existir sob Panasonic e sob
        # Brastemp, mas não duas 'Geladeira' sob a mesma Panasonic.
        if parent_id is None:
            existe = fetch_one(conn, "SELECT id FROM estoque_grupos WHERE LOWER(nome) = LOWER(?) AND parent_id IS NULL", (nome,))
        else:
            existe = fetch_one(conn, "SELECT id FROM estoque_grupos WHERE LOWER(nome) = LOWER(?) AND parent_id = ?", (nome, parent_id))
        if existe:
            return jsonify({"erro": f"Já existe um estoque chamado {nome} aqui"}), 400
        novo_id = insert_returning_id(conn,
            "INSERT INTO estoque_grupos (nome, cor, parent_id, criado_em) VALUES (?, ?, ?, ?)",
            (nome, (d.get("cor") or "").strip() or None, parent_id, _agora()))
    return jsonify({"mensagem": "Estoque criado", "id": novo_id, "nome": nome,
                    "parent_id": parent_id}), 201


@estoque_bp.route("/estoque/grupos/<int:grupo_id>", methods=["PUT"])
def editar_grupo(grupo_id):
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    campos, valores = [], []
    if "nome" in d:
        nome = (d.get("nome") or "").strip()
        if not nome:
            return jsonify({"erro": "O nome não pode ficar vazio"}), 400
        campos.append("nome = ?"); valores.append(nome)
    if "cor" in d:
        campos.append("cor = ?"); valores.append((d.get("cor") or "").strip() or None)
    if not campos:
        return jsonify({"mensagem": "Nada para mudar"})
    valores.append(grupo_id)
    with db_conn(commit=True) as conn:
        try:
            afetadas = execute(conn, f"UPDATE estoque_grupos SET {', '.join(campos)} WHERE id = ?", valores)
        except Exception:
            return jsonify({"erro": "Já existe um estoque com esse nome"}), 400
    if not afetadas:
        return jsonify({"erro": "Estoque não encontrado"}), 404
    return jsonify({"mensagem": "Estoque atualizado"})


@estoque_bp.route("/estoque/grupos/<int:grupo_id>", methods=["DELETE"])
def remover_grupo(grupo_id):
    """Apaga o estoque sem destruir o que estava dentro: as peças diretas voltam
    para 'Sem estoque' e os sub-estoques SOBEM para o pai do que foi apagado
    (some a Panasonic, a Geladeira dela vira estoque de topo). Faço na mão
    porque o SET NULL do FK não é confiável no SQLite (foreign_keys desligado)."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    with db_conn(commit=True) as conn:
        alvo = fetch_one(conn, "SELECT parent_id FROM estoque_grupos WHERE id = ?", (grupo_id,))
        if alvo is None:
            return jsonify({"erro": "Estoque não encontrado"}), 404
        avo = alvo["parent_id"]  # pai do apagado — para onde os filhos sobem
        subiram = execute(conn, "UPDATE estoque_grupos SET parent_id = ? WHERE parent_id = ?", (avo, grupo_id))
        soltas = execute(conn, "UPDATE estoque_itens SET grupo_id = NULL WHERE grupo_id = ?", (grupo_id,))
        execute(conn, "DELETE FROM estoque_grupos WHERE id = ?", (grupo_id,))
    return jsonify({"mensagem": "Estoque removido", "pecas_soltas": soltas,
                    "sub_estoques_movidos": subiram})


def _os_aguardando_esta_peca(conn, codigo: str) -> list:
    """OS em 'aguardando_peca' cujo desfecho de Cotação de peça pediu esse
    MESMO código. Só cobre o desfecho 'cotacao_peca' — é o único que grava
    código estruturado; 'precisa_peca' é texto livre e não dá pra casar com
    segurança (mesmo risco que o AgoraOS já documentou: nome parecido não é
    nome igual)."""
    codigo = _norm_codigo(codigo)
    if not codigo:
        return []
    return fetch_all(conn, """
        SELECT DISTINCT os.id, os.tipo_aparelho, os.modelo, c.nome AS cliente_nome
          FROM ordens_servico os
          JOIN servicos sv ON sv.ordem_servico_id = os.id
          JOIN servico_desfecho sd ON sd.servico_id = sv.id
          JOIN clientes c ON c.id = os.cliente_id
         WHERE os.status = 'aguardando_peca' AND UPPER(sd.codigo) = ?
    """, (codigo,))


@estoque_bp.route("/estoque/entrada", methods=["POST"])
def entrada():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    # grupo_id só é repassado quando a chave veio no corpo — ausência mantém o
    # grupo atual da peça (sentinela "__manter__" no dar_entrada).
    kw = {}
    if "grupo_id" in d:
        kw["grupo_id"] = d.get("grupo_id")
    try:
        with db_conn(commit=True) as conn:
            r = dar_entrada(conn, d.get("codigo"), d.get("descricao"),
                            d.get("quantidade"), d.get("custo_unit"),
                            origem="manual", obs=d.get("obs"),
                            marca=d.get("marca"), aparelho=d.get("aparelho"),
                            modelo=d.get("modelo"), preco_venda=d.get("preco_venda"),
                            **kw)
            os_esperando = _os_aguardando_esta_peca(conn, d.get("codigo"))
    except (ValueError, TypeError) as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Entrada registrada", "os_esperando": os_esperando, **r}), 201


@estoque_bp.route("/estoque/saida", methods=["POST"])
def saida():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    # cliente/atendimento a que a baixa se destina: vira a referência do
    # movimento e a origem passa a 'atendimento'. É o que liga a peça que saiu
    # ao trabalho que a consumiu — o histórico deixa de dizer só "saiu 1".
    cliente = (d.get("cliente") or d.get("referencia") or "").strip() or None
    origem = "atendimento" if cliente else "manual"
    try:
        with db_conn(commit=True) as conn:
            r = dar_saida(conn, d.get("codigo"), d.get("quantidade"),
                          origem=origem, referencia=cliente, obs=d.get("obs"))
    except (ValueError, TypeError) as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Saída registrada", **r}), 201


@estoque_bp.route("/estoque/atendimentos", methods=["GET"])
def atendimentos_para_baixa():
    """Clientes dos atendimentos, para o autocomplete de 'saiu para quem'.
    Vem de servicos (a base real de trabalho) — escolher em vez de digitar faz
    a referência casar certo e o histórico ficar consistente."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT DISTINCT cliente FROM servicos
             WHERE cliente IS NOT NULL AND TRIM(cliente) <> ''
             ORDER BY cliente
        """)
    return jsonify({"clientes": [l["cliente"] for l in linhas]})


@estoque_bp.route("/estoque/saldos", methods=["GET"])
def saldos_por_codigo():
    """Saldo atual de vários códigos de uma vez — usado pela aba Peças para
    mostrar 'em estoque: N' ao lado de cada compra. `codigos` separados por
    vírgula. Devolve um mapa {CODIGO: {saldo, id, ...}} só do que existe."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    brutos = (request.args.get("codigos") or "").split(",")
    codigos = {_norm_codigo(c) for c in brutos if (c or "").strip()}
    if not codigos:
        return jsonify({"saldos": {}})
    with db_conn() as conn:
        itens = fetch_all(conn, "SELECT id, codigo, descricao, saldo, custo_medio FROM estoque_itens")
    saldos = {i["codigo"]: {"id": i["id"], "saldo": float(i["saldo"] or 0),
                            "descricao": i["descricao"], "custo_medio": float(i["custo_medio"] or 0)}
              for i in itens if i["codigo"] in codigos}
    return jsonify({"saldos": saldos})


def _extrair_chave(texto):
    """Tira a chave de 44 dígitos do que veio do leitor de código de barras.

    O DANFE (NF-e modelo 55) tem um Code-128 com os 44 dígitos crus; a NFC-e
    (modelo 65) tem um QR com uma URL que carrega a chave embutida. Pegar a
    primeira sequência de exatamente 44 dígitos cobre os dois casos e ignora
    espaço, quebra de linha e o resto da URL."""
    m = re.search(r"\d{44}", (texto or ""))
    return m.group(0) if m else ""


def _num(v):
    """Número da NF-e (usa ponto decimal, padrão do XML) em float, tolerante."""
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


@estoque_bp.route("/estoque/nota/itens", methods=["POST"])
def ler_nota():
    """Resolve os itens de uma nota fiscal para conferência antes da entrada.

    Dois caminhos: `chave` (o que o leitor bipa) busca o XML no e-mail da
    Panasonic (services.nfe); `xml` colado é lido direto — cobre nota que não
    chegou por e-mail ou IMAP não configurado. Calcula o custo UNITÁRIO
    (vProd é o total do item ÷ quantidade), que é o que o estoque precisa."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    from services.nfe import _itens_do_xml, imap_configurado, itens_de_uma_nota

    d = request.get_json(silent=True) or {}
    xml = (d.get("xml") or "").strip()
    chave = _extrair_chave(d.get("chave") or d.get("codigo") or "")

    itens_brutos, fonte, erro_busca, motivo = [], None, False, None
    if xml:
        itens_brutos = _itens_do_xml(xml.encode("utf-8"))
        fonte = "xml"
    elif chave:
        # Nunca deixa estourar 502: a função sempre volta com um status.
        r = itens_de_uma_nota(chave)
        if r.get("status") == "ok":
            itens_brutos = r.get("itens") or []
            fonte = "email"
        elif r.get("status") == "erro":
            erro_busca = True
            motivo = r.get("motivo")
        # "vazio"/"off" caem em nao_encontrada abaixo.
    else:
        return jsonify({"erro": "Bipe a nota ou cole a chave/XML"}), 400

    itens = []
    for it in itens_brutos:
        qtd = _num(it.get("quantidade")) or 1
        total = _num(it.get("valor"))
        itens.append({
            "codigo": (it.get("codigo") or "").strip(),
            "descricao": (it.get("descricao") or "").strip(),
            "quantidade": qtd,
            "custo_unit": round(total / qtd, 4) if qtd else 0,
        })

    return jsonify({
        "chave": chave,
        "itens": itens,
        "fonte": fonte,
        "imap_configurado": imap_configurado(),
        # Não deu para buscar (timeout/erro no e-mail): a tela pede o XML.
        "erro_busca": erro_busca,
        "motivo": motivo,   # detalhe técnico do erro, só quando erro_busca
        # Buscou por chave e não achou o XML dessa nota no e-mail.
        "nao_encontrada": bool(chave and not xml and not itens and not erro_busca),
    })


@estoque_bp.route("/estoque/entrada-nota", methods=["POST"])
def entrada_nota():
    """Dá entrada em uma ou mais peças a partir de uma NOTA FISCAL, de uma vez.

    Idempotente por `referencia` (a chave da nota): reprocessar a mesma nota
    não duplica saldo. Sem isso, um clique a mais numa compra que já entrou
    inflaria o estoque em silêncio — o pior tipo de erro, o que ninguém vê.

    Corpo: {referencia, grupo_id?, itens:[{codigo, descricao, quantidade,
    custo_unit}]}. origem fica 'nota'.
    """
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    referencia = (d.get("referencia") or "").strip()
    itens = d.get("itens") or []
    if not itens:
        return jsonify({"erro": "Nenhum item para dar entrada"}), 400

    grupo_id = d.get("grupo_id")
    resultados, entraram, pulados = [], 0, 0
    try:
        with db_conn(commit=True) as conn:
            for it in itens:
                codigo = _norm_codigo(it.get("codigo"))
                if not codigo:
                    continue
                # Trava de idempotência: se ESTA nota já lançou ESTE código,
                # não repete. Checa antes de mexer no saldo.
                if referencia:
                    ja = fetch_one(conn, """
                        SELECT m.id FROM estoque_movimentos m
                          JOIN estoque_itens e ON e.id = m.item_id
                         WHERE m.origem = 'nota' AND m.referencia = ? AND e.codigo = ?
                         LIMIT 1
                    """, (referencia, codigo))
                    if ja:
                        pulados += 1
                        resultados.append({"codigo": codigo, "status": "ja_lancado"})
                        continue
                kw = {}
                if grupo_id not in (None, "", "__manter__"):
                    kw["grupo_id"] = grupo_id
                r = dar_entrada(conn, codigo, it.get("descricao"),
                                it.get("quantidade") or 1, it.get("custo_unit") or 0,
                                origem="nota", referencia=referencia or None, **kw)
                entraram += 1
                os_esperando = _os_aguardando_esta_peca(conn, codigo)
                resultados.append({"codigo": codigo, "status": "ok", "saldo": r["saldo"],
                                   "os_esperando": os_esperando})
    except (ValueError, TypeError) as exc:
        return jsonify({"erro": str(exc)}), 400

    total_esperando = sum(len(r.get("os_esperando") or []) for r in resultados)
    return jsonify({"mensagem": f"{entraram} peça(s) no estoque"
                    + (f", {pulados} já estavam" if pulados else ""),
                    "entraram": entraram, "pulados": pulados,
                    "resultados": resultados, "total_os_esperando": total_esperando}), 201


@estoque_bp.route("/estoque/<int:item_id>", methods=["PUT"])
def editar_item(item_id):
    """Ajusta mínimo, descrição, setor — e faz o AJUSTE de saldo por inventário.

    Ajuste é diferente de entrada/saída: é a contagem física dizendo qual é a
    verdade. Grava um movimento 'ajuste' com a diferença, para o histórico
    mostrar que o número foi corrigido na mão, e por quanto.
    """
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}

    with db_conn(commit=True) as conn:
        item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE id = ?", (item_id,))
        if not item:
            return jsonify({"erro": "Item não encontrado"}), 404

        campos, valores = [], []
        if "minimo" in d:
            campos.append("minimo = ?"); valores.append(max(0.0, float(d["minimo"] or 0)))
        if "descricao" in d:
            campos.append("descricao = ?"); valores.append((d["descricao"] or "").strip())
        if "marca" in d:
            campos.append("marca = ?"); valores.append((d["marca"] or "").strip())
        if "aparelho" in d:
            campos.append("aparelho = ?"); valores.append((d["aparelho"] or "").strip())
        if "modelo" in d:
            campos.append("modelo = ?"); valores.append((d["modelo"] or "").strip())
        if "preco_venda" in d:
            campos.append("preco_venda = ?"); valores.append(_num_ou_none(d["preco_venda"]) or 0)
        if "grupo_id" in d:
            # Mover a peça para outro estoque (ou tirá-la, com null).
            campos.append("grupo_id = ?"); valores.append(int(d["grupo_id"]) if d["grupo_id"] else None)
        if "setor_id" in d:
            campos.append("setor_id = ?"); valores.append(d["setor_id"] or None)
        if "foto" in d:
            # None explícito = remover a foto (botão "remover" no painel);
            # string = trocar, mas só se passar na validação — nunca grava
            # lixo maior que o limite ou fora do formato esperado.
            if d["foto"] is None:
                campos.append("foto = ?"); valores.append(None)
            else:
                foto_valida = _foto_valida(d["foto"])
                if not foto_valida:
                    return jsonify({"erro": "Foto inválida ou grande demais."}), 400
                campos.append("foto = ?"); valores.append(foto_valida)

        if campos:
            valores.append(item_id)
            execute(conn, f"UPDATE estoque_itens SET {', '.join(campos)} WHERE id = ?", valores)

        if "saldo_contado" in d and d["saldo_contado"] not in (None, ""):
            contado = float(d["saldo_contado"])
            diferenca = contado - float(item["saldo"] or 0)
            if diferenca != 0:
                execute(conn, "UPDATE estoque_itens SET saldo = ?, atualizado_em = ? WHERE id = ?",
                        (contado, _agora(), item_id))
                _registrar_movimento(conn, item_id, "ajuste", diferenca, contado,
                                    float(item["custo_medio"] or 0), "inventário",
                                    None, d.get("obs") or "Contagem física")

    return jsonify({"mensagem": "Item atualizado"})


@estoque_bp.route("/estoque/<int:item_id>", methods=["DELETE"])
def remover_item(item_id):
    """Remove o item e todo o histórico dele. Só admin, e some de vez —
    quando é peça cadastrada por engano, não uma que acabou (essa fica com
    saldo zero, para o histórico sobreviver)."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    with db_conn(commit=True) as conn:
        apagados = execute(conn, "DELETE FROM estoque_itens WHERE id = ?", (item_id,))
    if not apagados:
        return jsonify({"erro": "Item não encontrado"}), 404
    return jsonify({"mensagem": "Item removido"})


# ─── Fotos extras (mais de uma, além da `foto` principal) ────────────────
# Pedido de 2026-08-31. Mesmo padrão da OS — ver services/fotos_extra.py.
@estoque_bp.route("/estoque/<int:item_id>/fotos", methods=["GET"])
def listar_fotos_item(item_id):
    with db_conn() as conn:
        return jsonify({"fotos": listar_fotos_extra(conn, "estoque", item_id)})


@estoque_bp.route("/estoque/<int:item_id>/fotos", methods=["POST"])
def adicionar_foto_item(item_id):
    d = request.get_json(silent=True) or {}
    with db_conn(commit=True) as conn:
        existe = fetch_one(conn, "SELECT id FROM estoque_itens WHERE id = ?", (item_id,))
        if not existe:
            return jsonify({"erro": "Item não encontrado"}), 404
        erro, linha = adicionar_foto_extra(conn, "estoque", item_id, d.get("foto"))
        if erro:
            return jsonify({"erro": erro}), 400
    return jsonify({"foto": linha}), 201


@estoque_bp.route("/estoque/fotos/<int:foto_id>", methods=["DELETE"])
def apagar_foto_item(foto_id):
    with db_conn(commit=True) as conn:
        if not remover_foto_extra(conn, "estoque", foto_id):
            return jsonify({"erro": "Foto não encontrada"}), 404
    return jsonify({"mensagem": "Foto removida"})


@estoque_bp.route("/estoque/<int:item_id>/historico", methods=["GET"])
def historico(item_id):
    """Todo movimento do item, mais recente primeiro. É a auditoria do saldo.

    'ordem_servico' e 'venda' guardam só um id em referencia (o suficiente
    pra função que deu a saída, mas ilegível pra quem lê depois) — aqui
    resolve pra cliente/OS de verdade, pra "saiu 1" virar "saiu 1 — Fulano,
    OS #000042" (pedido de 2026-08-29). 'nota' e 'atendimento' já são
    legíveis por si (nº da nota, nome do cliente) — não precisam de busca."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    with db_conn() as conn:
        item = fetch_one(conn, "SELECT * FROM estoque_itens WHERE id = ?", (item_id,))
        if not item:
            return jsonify({"erro": "Item não encontrado"}), 404
        movs = fetch_all(conn, """
            SELECT tipo, quantidade, saldo_apos, custo_unit, origem,
                   referencia, autor, obs, criado_em
              FROM estoque_movimentos WHERE item_id = ?
             ORDER BY id DESC
        """, (item_id,))

        for m in movs:
            m["contexto"] = None
            ref = (m.get("referencia") or "").strip()
            if not ref:
                continue
            if m["origem"] == "ordem_servico" and ref.isdigit():
                os_row = fetch_one(conn, """
                    SELECT os.id, c.nome AS cliente_nome
                      FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id
                     WHERE os.id = ?
                """, (int(ref),))
                if os_row:
                    m["contexto"] = {"tipo": "os", "os_id": os_row["id"], "cliente": os_row["cliente_nome"]}
            elif m["origem"] == "venda" and ref.startswith("venda:"):
                venda_id = ref.split(":", 1)[1]
                if venda_id.isdigit():
                    venda_row = fetch_one(conn, "SELECT id, cliente_nome FROM vendas WHERE id = ?",
                                          (int(venda_id),))
                    if venda_row:
                        m["contexto"] = {"tipo": "venda", "venda_id": venda_row["id"],
                                         "cliente": venda_row["cliente_nome"]}

    return jsonify({"item": item, "movimentos": movs})
