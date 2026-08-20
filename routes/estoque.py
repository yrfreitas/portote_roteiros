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
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import IS_PG, db_conn, execute, fetch_all, fetch_one, insert_returning_id

log = logging.getLogger("portotec.estoque")

estoque_bp = Blueprint("estoque", __name__)


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

    def agrega(filtro):
        sel = [i for i in itens if filtro(i)]
        return {
            "total_pecas": len(sel),
            "valor_investido": round(sum(float(i["saldo"] or 0) * float(i["custo_medio"] or 0) for i in sel), 2),
            "abaixo_minimo": sum(1 for i in sel
                                 if float(i["minimo"] or 0) > 0 and float(i["saldo"] or 0) <= float(i["minimo"])),
        }

    for g in grupos:
        g.update(agrega(lambda i, gid=g["id"]: i["grupo_id"] == gid))

    sem = agrega(lambda i: not i["grupo_id"])
    return jsonify({"grupos": grupos, "sem_estoque": sem})


@estoque_bp.route("/estoque/grupos", methods=["POST"])
def criar_grupo():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Dê um nome ao estoque"}), 400
    with db_conn(commit=True) as conn:
        # Nome único: dois 'Electrolux' viram bagunça. Avisa em vez de duplicar.
        existe = fetch_one(conn, "SELECT id FROM estoque_grupos WHERE LOWER(nome) = LOWER(?)", (nome,))
        if existe:
            return jsonify({"erro": f"Já existe um estoque chamado {nome}"}), 400
        novo_id = insert_returning_id(conn,
            "INSERT INTO estoque_grupos (nome, cor, criado_em) VALUES (?, ?, ?)",
            (nome, (d.get("cor") or "").strip() or None, _agora()))
    return jsonify({"mensagem": "Estoque criado", "id": novo_id, "nome": nome}), 201


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
    """Apaga o estoque; as peças NÃO somem — voltam para 'Sem estoque'. O
    SET NULL do FK não é confiável no SQLite (foreign_keys vem desligado), por
    isso solto as peças na mão antes de apagar, garantindo os dois bancos."""
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    with db_conn(commit=True) as conn:
        soltas = execute(conn, "UPDATE estoque_itens SET grupo_id = NULL WHERE grupo_id = ?", (grupo_id,))
        apagados = execute(conn, "DELETE FROM estoque_grupos WHERE id = ?", (grupo_id,))
    if not apagados:
        return jsonify({"erro": "Estoque não encontrado"}), 404
    return jsonify({"mensagem": "Estoque removido", "pecas_soltas": soltas})


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
    except (ValueError, TypeError) as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Entrada registrada", **r}), 201


@estoque_bp.route("/estoque/saida", methods=["POST"])
def saida():
    if not session.get("admin"):
        return jsonify({"erro": "Não autenticado"}), 401
    d = request.get_json(silent=True) or {}
    try:
        with db_conn(commit=True) as conn:
            r = dar_saida(conn, d.get("codigo"), d.get("quantidade"),
                          origem="manual", obs=d.get("obs"))
    except (ValueError, TypeError) as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Saída registrada", **r}), 201


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


@estoque_bp.route("/estoque/<int:item_id>/historico", methods=["GET"])
def historico(item_id):
    """Todo movimento do item, mais recente primeiro. É a auditoria do saldo."""
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
    return jsonify({"item": item, "movimentos": movs})
