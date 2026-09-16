"""Auto-cadastro de cliente NOVO por /novo-atendimento — pedido do Kalebe em
2026-09-16: a "Central do Cliente" (routes/central_cliente.py) só serve quem
JÁ tem uma OS aberta pela equipe; isto aqui é a entrada de quem NUNCA foi
atendido, abrindo o próprio caso pelo site, sem ligar.

Cria cliente + Ordem de Serviço (modelo 'chamado_tecnico') exatamente como o
formulário "Nova OS" do painel cria, mas com duas diferenças de propósito:

1. setor_id fica NULL — classificação por fabricante (Panasonic/Philco/Loja)
   é vocabulário interno que quem preenche o formulário não tem como saber.
   Mesma filosofia já usada pro CEP sem geocodificação em agendar()
   (routes/ordens_servico.py): corrige depois é melhor que travar a entrada.
2. Não agenda visita nenhuma — só guarda a PREFERÊNCIA de data/período que a
   pessoa escolheu. Virar rota de verdade continua exigindo alguém da equipe
   escolher técnico e dia (mesmo agendar() de sempre), porque a otimização de
   rota é montada manualmente dia a dia — não existe agenda de capacidade por
   região reservada com antecedência (decisão de negócio ainda pendente).

A OS entra com status 'aguardando_agendamento' e origem_publica_em preenchido,
o que a faz aparecer na aba "Agendar Clientes" (fonte=publico) do painel —
mesma fila que peça-chegou/reagendamento já usam, sem painel novo.
"""
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from database import db_conn, execute, insert_returning_id

novo_atendimento_bp = Blueprint("novo_atendimento", __name__)

_PERIODOS_VALIDOS = ("manha", "tarde")


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _validar_data(valor):
    texto = (valor or "").strip()
    if not texto:
        return None
    try:
        data = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return None
    if data < datetime.now(timezone.utc).date():
        return None
    return texto


@novo_atendimento_bp.route("", methods=["POST"])
def criar():
    d = request.get_json(silent=True) or {}

    nome = (d.get("nome") or "").strip()
    telefone = (d.get("telefone") or "").strip()
    cep = "".join(c for c in (d.get("cep") or "") if c.isdigit())
    tipo_aparelho = (d.get("tipo_aparelho") or "").strip()
    defeito_declarado = (d.get("defeito_declarado") or "").strip()
    preferencia_periodo = (d.get("preferencia_periodo") or "").strip().lower()

    erros = []
    if not nome:
        erros.append("Informe seu nome")
    if len("".join(c for c in telefone if c.isdigit())) < 10:
        erros.append("Informe um telefone válido com DDD")
    if len(cep) != 8:
        erros.append("Informe um CEP válido")
    if not tipo_aparelho:
        erros.append("Escolha o equipamento")
    if not defeito_declarado:
        erros.append("Descreva o problema")
    preferencia_data = _validar_data(d.get("preferencia_data"))
    if not preferencia_data:
        erros.append("Escolha uma data de preferência (hoje ou uma data futura)")
    if preferencia_periodo not in _PERIODOS_VALIDOS:
        erros.append("Escolha manhã ou tarde")
    if erros:
        return jsonify({"erro": erros[0], "erros": erros}), 400

    situacao = "garantia" if (d.get("situacao") or "").strip().lower() == "garantia" else "particular"
    observacao = ("Cliente informou que o aparelho está na garantia."
                  if situacao == "garantia" else "Cliente informou: particular.")

    agora = _agora()
    with db_conn(commit=True) as conn:
        cliente_id = insert_returning_id(conn, """
            INSERT INTO clientes (nome, telefone, cep, endereco, numero, complemento,
                                  bairro, cidade, cadastrado_por, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome, telefone, cep,
              (d.get("endereco") or "").strip(), (d.get("numero") or "").strip(),
              (d.get("complemento") or "").strip(), (d.get("bairro") or "").strip(),
              (d.get("cidade") or "").strip(), "Site (auto-cadastro)", agora))

        token_cliente = secrets.token_urlsafe(24)
        os_id = insert_returning_id(conn, """
            INSERT INTO ordens_servico
                (cliente_id, atendente, tipo_aparelho, marca, modelo,
                 defeito_declarado, status, observacao, criado_em, criado_por,
                 modelo_os, token_cliente, origem_publica_em,
                 preferencia_data, preferencia_periodo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cliente_id, "Site", tipo_aparelho,
              (d.get("marca") or "").strip(), (d.get("modelo") or "").strip(),
              defeito_declarado, "aguardando_agendamento", observacao, agora,
              "Site (auto-cadastro)", "chamado_tecnico", token_cliente, agora,
              preferencia_data, preferencia_periodo))

    return jsonify({"mensagem": "Solicitação recebida", "id": os_id,
                    "token": token_cliente}), 201
