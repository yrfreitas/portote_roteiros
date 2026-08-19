# -*- coding: utf-8 -*-
"""Testes da normalização de nomes usada para casar cliente com OS.

POR QUE ESTES TESTES EXISTEM
----------------------------
O próprio módulo agoraos.py documenta que casamento aproximado de nome
PRODUZIU ERRO REAL contra a base de produção: "Jaqueline Chen" casou com
"Jaqueline Chopin" e "Jean Cardoso" com "Ana Cardoso" — duas pessoas
diferentes cada uma.

Escrever numa OS errada mexe em faturamento, e a API do AgoraOS não tem
DELETE de item de OS (só POST e PUT) — não dá para desfazer. Por isso a regra
é: **só casamento exato normalizado grava**.

Estes testes travam essa regra. Se alguém "melhorar" a normalização a ponto de
dois nomes diferentes passarem a colidir, quebra aqui e não na OS de um
cliente.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agoraos import normalizar


@pytest.mark.parametrize("entrada,esperado", [
    ("José da Silva", "jose da silva"),
    ("JOSÉ DA SILVA", "jose da silva"),
    ("  José   da   Silva  ", "jose da silva"),
    ("Conceição Ramalho", "conceicao ramalho"),
    ("Ângela Muñoz", "angela munoz"),
])
def test_normalizar_tira_acento_caixa_e_espaco_extra(entrada, esperado):
    """As variações que a mesma pessoa aparece escrita nos dois sistemas têm
    de convergir para a mesma string."""
    assert normalizar(entrada) == esperado


@pytest.mark.parametrize("a,b", [
    ("Jaqueline Chen", "Jaqueline Chopin"),
    ("Jean Cardoso", "Ana Cardoso"),
    ("Maria Souza", "Maria Souza Neto"),
    ("Carlos Lima", "Carlos Lima Filho"),
])
def test_pessoas_diferentes_nunca_normalizam_igual(a, b):
    """A trava que impede lançar peça na OS de outra pessoa.

    Os dois primeiros pares são os casos REAIS que o fuzzy errou em produção
    (documentados em agoraos.py). A normalização não pode aproximá-los.
    """
    assert normalizar(a) != normalizar(b)


def test_normalizar_aceita_vazio_sem_estourar():
    """Cliente sem nome não pode derrubar a listagem inteira."""
    assert normalizar("") == ""
    assert normalizar(None) == ""
