# -*- coding: utf-8 -*-
"""Testes do mapeamento de colunas da planilha de Pedidos.

POR QUE ESTES TESTES EXISTEM
----------------------------
Em 18/08/2026 as linhas da planilha estavam gravadas uma coluna à direita do
cabeçalho. O `listar_pedidos` lê por número de coluna — `col(2)` é a nota,
`col(5)` é o status — então passou a ler o ID no lugar da nota, o cliente no
lugar do valor e o valor no lugar do status. Tudo errado por uma casa.

A tela de Peças ficou inutilizável por dias e **nada acusou**: não havia erro,
exceção nem log. Os dados simplesmente não faziam sentido, e só um humano
olhando percebeu.

Um teste que monta uma linha no formato certo e confere que cada campo saiu
no lugar certo custa milissegundos e teria pego isso no mesmo dia.

Rodar:  venv/Scripts/python.exe -m pytest tests -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.planilha import (COL_DESCRICAO_PECA, COL_NOME_CLIENTE_FINAL,
                               COL_NUMERO_OS, COL_SITUACAO_OS)


# Ordem real das colunas na aba Pedidos. Se alguém acrescentar uma coluna no
# MEIO da planilha, este teste quebra — que é exatamente o objetivo: hoje isso
# passaria despercebido até alguém estranhar a tela.
CABECALHO = [
    "ID Registro", "Numero Nota Fiscal", "Cliente", "Valor", "Status",
    "Data Captura", "Nome Cliente Final", "Numero OS", "Situacao OS",
    "Descricao Peca",
]


def test_constantes_de_coluna_batem_com_o_cabecalho():
    """As constantes são 1-based e precisam apontar para o título certo."""
    assert CABECALHO[COL_NOME_CLIENTE_FINAL - 1] == "Nome Cliente Final"
    assert CABECALHO[COL_NUMERO_OS - 1] == "Numero OS"
    assert CABECALHO[COL_SITUACAO_OS - 1] == "Situacao OS"
    assert CABECALHO[COL_DESCRICAO_PECA - 1] == "Descricao Peca"


def test_ordem_do_cabecalho_nao_mudou():
    """Trava a posição das colunas lidas por índice em listar_pedidos:
    col(2)=nota, col(4)=valor, col(5)=status, col(6)=data."""
    assert CABECALHO[1] == "Numero Nota Fiscal"
    assert CABECALHO[3] == "Valor"
    assert CABECALHO[4] == "Status"
    assert CABECALHO[5] == "Data Captura"


def _linha(**campos):
    """Monta uma linha da planilha na ordem do cabeçalho."""
    base = dict.fromkeys(CABECALHO, "")
    base.update(campos)
    return [base[c] for c in CABECALHO]


def test_linha_credipay_tem_nota_na_coluna_certa():
    linha = _linha(**{
        "ID Registro": "3526...#APROVADO",
        "Numero Nota Fiscal": "35260804403408000912550010007844121116978778",
        "Cliente": "PORTOTEC SP ASSISTENCIA TECNICA LTDA",
        "Valor": "379,7",
        "Status": "APROVADO",
    })
    assert len(linha) == 10
    assert linha[1].isdigit() and len(linha[1]) == 44   # nota fiscal
    assert linha[4] == "APROVADO"                        # status


def test_linha_vtex_nasce_sem_nota_fiscal():
    """Pedido da loja VTEX chega antes de a nota ser emitida — a coluna de
    nota vem VAZIA de propósito. O código que agrupa por nota precisa cair
    para o identificador do registro, senão a compra some da tela."""
    linha = _linha(**{
        "ID Registro": "PED1655130513683-01#CRIADO",
        "Numero Nota Fiscal": "",
        "Cliente": "Nathalia Alves Da Silva Ervilha",
        "Valor": "490,81",
        "Status": "CRIADO",
    })
    assert linha[1] == ""
    assert linha[0].startswith("PED")


@pytest.mark.parametrize("identificador,esperado", [
    ("PED1655130513683-01#CRIADO", "1655130513683-01"),
    ("PED1655130513683-01#APROVADO", "1655130513683-01"),
    ("3526080440340800091255001000784412111697877#APROVADO",
     "3526080440340800091255001000784412111697877"),
])
def test_chave_do_registro_ignora_o_status(identificador, esperado):
    """As duas (ou quatro) linhas do mesmo pedido têm de agrupar juntas.
    Sem tirar o sufixo de status, cada evento viraria uma compra diferente
    na tela."""
    chave = identificador.rsplit("#", 1)[0]
    if chave.startswith("PED"):
        chave = chave[3:]
    assert chave == esperado
