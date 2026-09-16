"""Cálculo de prazo de garantia de uma Ordem de Serviço.

Extraído de app.py (_montar_documento_os) em 2026-09-16 pra ser reaproveitado
também pela Central do Cliente — o prazo mostrado pro cliente tem que ser
exatamente o mesmo que já sai no documento impresso, não uma segunda conta
que pode divergir.
"""
from datetime import datetime
import calendar

# "saida_oficina" soma aos outros três em 2026-08-29: o termo dela promete
# 3 meses "a partir da data da conclusão do reparo" (ver TERMOS_POR_TIPO em
# routes/ordens_servico.py), só que essa data é escolhida à mão no painel
# (ordem.garantia_inicio) — o dia em que o aparelho de fato saiu, não
# necessariamente hoje. Os outros três tipos não têm esse campo preenchido.
_GARANTIA_MESES = {
    "garantia_3_meses": 3, "garantia_6_meses": 6, "garantia_1_ano": 12,
    "saida_oficina": 3,
}


def _somar_meses(data, meses):
    mes_total = data.month - 1 + meses
    ano = data.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return data.replace(year=ano, month=mes, day=min(data.day, ultimo_dia))


def calcular_garantia(ordem: dict):
    """Recebe uma linha de ordens_servico (precisa de tipo_os, modelo_os,
    garantia_meses, garantia_inicio) e devolve:

        {"meses": int, "prazo_rotulo": str,
         "inicio_br": str | None, "fim_br": str | None}

    ou None quando a OS não tem garantia aplicável (nenhum prazo resolvido).
    inicio_br/fim_br vêm None quando o prazo existe mas garantia_inicio ainda
    não foi preenchida ou está inválida — nunca inventa uma data.
    """
    # "saida_oficina" pode escolher 3/6/12 meses em vez do padrão fixo — os
    # outros três tipos já SÃO um prazo fixo cada um (é a própria escolha do
    # tipo que decide). O modelo Orçamento entra na mesma regra: não tem
    # tipo_os fixo, mas aceita o mesmo campo de prazo escolhido à mão.
    garantia_meses = (
        ordem.get("garantia_meses")
        if (ordem.get("tipo_os") == "saida_oficina" or ordem.get("modelo_os") == "orcamento")
           and ordem.get("garantia_meses")
        else _GARANTIA_MESES.get(ordem.get("tipo_os"))
    )
    if not garantia_meses:
        return None

    prazo_rotulo = "1 ano" if garantia_meses == 12 else f"{garantia_meses} meses"
    inicio_br = fim_br = None
    if ordem.get("garantia_inicio"):
        try:
            base = datetime.strptime(ordem["garantia_inicio"], "%Y-%m-%d")
            inicio_br = base.strftime("%d/%m/%Y")
            fim_br = _somar_meses(base, garantia_meses).strftime("%d/%m/%Y")
        except ValueError:
            pass   # data inválida no banco — não inventa uma

    return {
        "meses": garantia_meses,
        "prazo_rotulo": prazo_rotulo,
        "inicio_br": inicio_br,
        "fim_br": fim_br,
    }
