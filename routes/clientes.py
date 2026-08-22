"""Cadastro de cliente PRÓPRIO — não depende do AgoraOS nem de mais nada.

Decisão de 2026-08-21: antes só existia `servicos.cliente`, um texto solto
redigitado a cada atendimento, sem CPF/telefone/endereço fixo. Ordem de
Serviço precisa de um cadastro de verdade, e a base de clientes serve a
outros usos futuros (histórico, marketing, financeiro) que texto solto nunca
serviria.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database import db_conn, execute, fetch_all, fetch_one, insert_returning_id
from services.geo import consultar_cep

clientes_bp = Blueprint("clientes", __name__)

# Lista FECHADA de propósito — mesmo motivo dos desfechos: texto livre não
# soma nem filtra, e "de onde vêm nossos clientes" é pergunta de negócio.
INDICACOES_VALIDAS = [
    "Google", "Instagram", "Facebook", "Indicação de amigo/família",
    "Cliente antigo", "Fachada/loja física", "WhatsApp", "Outro",
]


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _quem() -> str:
    return session.get("usuario_nome") or "Administrador"


def _campos(d: dict) -> dict:
    """Extrai e normaliza os campos de cliente vindos do corpo da requisição.
    Função própria porque criar e editar usam exatamente os mesmos campos."""
    return {
        "nome": (d.get("nome") or "").strip(),
        "tipo_pessoa": (d.get("tipo_pessoa") or "PF").strip().upper(),
        "cpf_cnpj": (d.get("cpf_cnpj") or "").strip(),
        "telefone": (d.get("telefone") or "").strip(),
        "email": (d.get("email") or "").strip(),
        "cep": (d.get("cep") or "").strip(),
        "endereco": (d.get("endereco") or "").strip(),
        "numero": (d.get("numero") or "").strip(),
        "complemento": (d.get("complemento") or "").strip(),
        "bairro": (d.get("bairro") or "").strip(),
        "cidade": (d.get("cidade") or "").strip(),
        "estado": (d.get("estado") or "").strip().upper()[:2],
        "indicacao": (d.get("indicacao") or "").strip(),
        "obs": (d.get("obs") or "").strip(),
    }


def criar_cliente(conn, dados: dict) -> int:
    """Reaproveitável por routes/ordens_servico.py (abrir OS com cliente novo,
    numa única requisição — sem isso seria dois passos e dois cliques)."""
    campos = _campos(dados)
    if not campos["nome"]:
        raise ValueError("Nome do cliente é obrigatório")
    if campos["indicacao"] and campos["indicacao"] not in INDICACOES_VALIDAS:
        raise ValueError("Indicação inválida")

    agora = _agora()
    return insert_returning_id(conn, """
        INSERT INTO clientes (nome, tipo_pessoa, cpf_cnpj, telefone, email,
                              cep, endereco, numero, complemento, bairro,
                              cidade, estado, indicacao, obs, cadastrado_por,
                              criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (campos["nome"], campos["tipo_pessoa"], campos["cpf_cnpj"],
          campos["telefone"], campos["email"], campos["cep"], campos["endereco"],
          campos["numero"], campos["complemento"], campos["bairro"],
          campos["cidade"], campos["estado"], campos["indicacao"] or None,
          campos["obs"], _quem(), agora))


@clientes_bp.route("/clientes/cep/<cep>", methods=["GET"])
def buscar_cep(cep):
    endereco = consultar_cep(cep)
    if not endereco:
        return jsonify({"erro": "CEP não encontrado"}), 404
    return jsonify(endereco)


@clientes_bp.route("/clientes/indicacoes", methods=["GET"])
def listar_indicacoes():
    return jsonify({"indicacoes": INDICACOES_VALIDAS})


@clientes_bp.route("/clientes", methods=["GET"])
def listar():
    """?busca filtra por nome, CPF/CNPJ ou telefone — os três jeitos que
    alguém no telefone descreve um cliente."""
    busca = (request.args.get("busca") or "").strip().lower()

    with db_conn() as conn:
        clientes = fetch_all(conn, "SELECT * FROM clientes ORDER BY nome")

    if busca:
        clientes = [
            c for c in clientes
            if busca in (c.get("nome") or "").lower()
            or busca in (c.get("cpf_cnpj") or "").lower()
            or busca in (c.get("telefone") or "").lower()
        ]

    return jsonify({"clientes": clientes[:50], "total": len(clientes)})


@clientes_bp.route("/clientes/<int:cliente_id>", methods=["GET"])
def obter(cliente_id):
    with db_conn() as conn:
        cliente = fetch_one(conn, "SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        if not cliente:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        ordens = fetch_all(conn, """
            SELECT id, status, tipo_aparelho, modelo, defeito_declarado, criado_em
              FROM ordens_servico WHERE cliente_id = ? ORDER BY id DESC
        """, (cliente_id,))

    return jsonify({"cliente": cliente, "ordens_servico": ordens})


@clientes_bp.route("/clientes", methods=["POST"])
def criar():
    dados = request.get_json(silent=True) or {}
    try:
        with db_conn(commit=True) as conn:
            novo_id = criar_cliente(conn, dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"mensagem": "Cliente cadastrado", "id": novo_id}), 201


@clientes_bp.route("/clientes/<int:cliente_id>", methods=["PUT"])
def editar(cliente_id):
    dados = request.get_json(silent=True) or {}
    campos = _campos(dados)
    if not campos["nome"]:
        return jsonify({"erro": "Nome do cliente é obrigatório"}), 400
    if campos["indicacao"] and campos["indicacao"] not in INDICACOES_VALIDAS:
        return jsonify({"erro": "Indicação inválida"}), 400

    with db_conn(commit=True) as conn:
        existe = fetch_one(conn, "SELECT id FROM clientes WHERE id = ?", (cliente_id,))
        if not existe:
            return jsonify({"erro": "Cliente não encontrado"}), 404

        execute(conn, """
            UPDATE clientes SET nome=?, tipo_pessoa=?, cpf_cnpj=?, telefone=?,
                   email=?, cep=?, endereco=?, numero=?, complemento=?,
                   bairro=?, cidade=?, estado=?, indicacao=?, obs=?,
                   atualizado_em=?
             WHERE id=?
        """, (campos["nome"], campos["tipo_pessoa"], campos["cpf_cnpj"],
              campos["telefone"], campos["email"], campos["cep"],
              campos["endereco"], campos["numero"], campos["complemento"],
              campos["bairro"], campos["cidade"], campos["estado"],
              campos["indicacao"] or None, campos["obs"], _agora(), cliente_id))

    return jsonify({"mensagem": "Cliente atualizado"})
