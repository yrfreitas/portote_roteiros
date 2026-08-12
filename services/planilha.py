"""Conciliação entre os atendimentos concluídos no site e a planilha de pedidos.

Quando o técnico finaliza a rota, cada ponto concluído é procurado na aba
"Pedidos" da planilha do Google (a mesma que o robô do porto_tec_panasonic
alimenta). Se achar, dá baixa; se não achar, registra em "Outros Atendimentos"
— porque não achar é NORMAL: pode ser cliente de outra marca ou uma vistoria,
não é erro.

Credenciais: em produção a service account vem inteira na env var
GOOGLE_CREDENTIALS_JSON (o Railway não tem sistema de arquivos persistente pra
guardar um credentials.json). Localmente aceita também o caminho de arquivo em
GOOGLE_CREDENTIALS_PATH.
"""
import json
import logging
import os
import unicodedata
from datetime import datetime
from typing import Optional

log = logging.getLogger("portotec.planilha")

ESCOPOS = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

ABA_PEDIDOS = os.environ.get("ABA_PEDIDOS", "Pedidos")
ABA_OUTROS = os.environ.get("ABA_OUTROS", "Outros Atendimentos")

CABECALHO_OUTROS = [
    "Data Conclusão", "Cliente", "Endereço", "Aparelho", "Modelo",
    "Descrição", "Técnico", "Ficha (dia)", "Motivo",
]

# Colunas da aba Pedidos que interessam (1-indexed, como o Sheets espera)
COL_NOME_CLIENTE_FINAL = 7
COL_NUMERO_OS = 8
COL_SITUACAO_OS = 9
COL_DESCRICAO_PECA = 10

VERDE = {"red": 0.85, "green": 0.94, "blue": 0.83}   # casou nome + modelo
AMARELO = {"red": 1.0, "green": 0.95, "blue": 0.80}  # casou só o nome

# A coluna "Situacao OS" tem lista suspensa no Sheets (strict), então o texto
# gravado precisa ser EXATAMENTE um dos valores dela — senão a célula é
# recusada. Opções da lista: Aguardando Peça, Peça Chegou, Em Reparo,
# Aguardando Retirada, Concluída, Cancelada.
SITUACAO_CONCLUIDA = "Concluída"


def normalizar(texto: str) -> str:
    """Tira acento, baixa a caixa e colapsa espaço — pra 'MARIA DAS GRAÇAS'
    casar com 'Maria das Gracas'."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().split())


def _so_alfanumerico(texto: str) -> str:
    """'NR-BB64PV1BA' e 'bb64' viram comparáveis: tira hífen, espaço e caixa."""
    return "".join(c for c in normalizar(texto) if c.isalnum())


def planilha_configurada() -> bool:
    tem_credencial = bool(
        os.environ.get("GOOGLE_CREDENTIALS_JSON")
        or os.environ.get("GOOGLE_CREDENTIALS_PATH")
    )
    return tem_credencial and bool(os.environ.get("PLANILHA_ID"))


def _abrir_planilha():
    import gspread
    from google.oauth2.service_account import Credentials

    bruto = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if bruto:
        cred = Credentials.from_service_account_info(json.loads(bruto), scopes=ESCOPOS)
    else:
        caminho = os.environ["GOOGLE_CREDENTIALS_PATH"]
        cred = Credentials.from_service_account_file(caminho, scopes=ESCOPOS)

    return gspread.authorize(cred).open_by_key(os.environ["PLANILHA_ID"])


def _obter_ou_criar_outros(planilha):
    import gspread

    try:
        return planilha.worksheet(ABA_OUTROS)
    except gspread.WorksheetNotFound:
        log.info("Criando aba '%s'", ABA_OUTROS)
        aba = planilha.add_worksheet(
            title=ABA_OUTROS, rows=2000, cols=len(CABECALHO_OUTROS)
        )
        aba.append_row(CABECALHO_OUTROS, value_input_option="USER_ENTERED")
        aba.freeze(rows=1)
        return aba


def _casar(servico: dict, linhas: list) -> Optional[dict]:
    """Procura o serviço na aba Pedidos.

    Devolve {'linha': n, 'forca': 'nome+modelo'|'nome', 'peca': ...} ou None.
    Só considera linhas ainda sem baixa — uma peça já conciliada não é
    reaproveitada por outro atendimento.
    """
    nome_alvo = normalizar(servico.get("cliente"))
    if not nome_alvo:
        return None

    palavras = [p for p in nome_alvo.split() if len(p) > 2]
    modelo_alvo = _so_alfanumerico(servico.get("modelo"))

    candidato_fraco = None

    for numero_linha, linha in linhas:
        nome_planilha = normalizar(
            linha[COL_NOME_CLIENTE_FINAL - 1] if len(linha) >= COL_NOME_CLIENTE_FINAL else ""
        )
        if not nome_planilha:
            continue

        situacao = (
            linha[COL_SITUACAO_OS - 1] if len(linha) >= COL_SITUACAO_OS else ""
        ).strip()
        if situacao:  # já tem baixa, não mexe
            continue

        nome_bate = (
            nome_alvo == nome_planilha
            or (palavras and all(p in nome_planilha for p in palavras))
        )
        if not nome_bate:
            continue

        peca = linha[COL_DESCRICAO_PECA - 1] if len(linha) >= COL_DESCRICAO_PECA else ""
        peca_norm = _so_alfanumerico(peca)

        modelo_bate = bool(modelo_alvo) and bool(peca_norm) and (
            modelo_alvo in peca_norm or peca_norm in modelo_alvo
        )

        if modelo_bate:
            return {"linha": numero_linha, "forca": "nome+modelo", "peca": peca}
        if candidato_fraco is None:
            candidato_fraco = {"linha": numero_linha, "forca": "nome", "peca": peca}

    return candidato_fraco


def conciliar(ficha: dict, servicos: list, tecnico_nome: str,
              aplicar: bool = False) -> dict:
    """Concilia os serviços com a planilha.

    aplicar=False  -> só simula e devolve o que faria (prévia pro técnico)
    aplicar=True   -> grava de verdade
    """
    if not planilha_configurada():
        return {"erro": "Integração com a planilha não está configurada.",
                "configurada": False}

    planilha = _abrir_planilha()
    aba_pedidos = planilha.worksheet(ABA_PEDIDOS)
    todas = aba_pedidos.get_all_values()
    # (numero_da_linha_no_sheets, conteudo) — pulando o cabeçalho
    linhas = [(i, l) for i, l in enumerate(todas[1:], start=2)]

    casados, outros = [], []
    linhas_usadas = set()

    for s in servicos:
        resultado = _casar(s, [(n, l) for n, l in linhas if n not in linhas_usadas])
        if resultado:
            linhas_usadas.add(resultado["linha"])
            casados.append({
                "cliente": s.get("cliente"),
                "modelo": s.get("modelo"),
                "linha": resultado["linha"],
                "forca": resultado["forca"],
                "peca": resultado["peca"],
            })
        else:
            outros.append({
                "cliente": s.get("cliente"),
                "endereco": s.get("endereco_completo"),
                "aparelho": s.get("tipo_aparelho"),
                "modelo": s.get("modelo"),
                "descricao": s.get("descricao"),
                "motivo": "Sem correspondência na aba Pedidos "
                          "(outra marca, vistoria ou peça ainda não lançada)",
            })

    resumo = {
        "configurada": True,
        "aplicado": aplicar,
        "total": len(servicos),
        "casados": casados,
        "outros": outros,
    }

    if not aplicar:
        return resumo

    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    identificacao_ficha = f"{ficha.get('dia_semana', '')} {ficha.get('data_referencia') or ''}".strip()

    # dá baixa nas linhas que casaram
    for c in casados:
        n = c["linha"]
        aba_pedidos.update_cell(n, COL_SITUACAO_OS, SITUACAO_CONCLUIDA)
        if not (todas[n - 1][COL_NUMERO_OS - 1] if len(todas[n - 1]) >= COL_NUMERO_OS else ""):
            aba_pedidos.update_cell(n, COL_NUMERO_OS, identificacao_ficha)
        cor = VERDE if c["forca"] == "nome+modelo" else AMARELO
        try:
            aba_pedidos.format(f"A{n}:J{n}", {"backgroundColor": cor})
        except Exception as exc:
            log.warning("Não consegui pintar a linha %s: %s", n, exc)

    # registra os que não casaram
    if outros:
        aba_outros = _obter_ou_criar_outros(planilha)
        aba_outros.append_rows(
            [[agora, o["cliente"], o["endereco"], o["aparelho"], o["modelo"],
              o["descricao"], tecnico_nome, identificacao_ficha, o["motivo"]]
             for o in outros],
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
            table_range="A1",
        )

    return resumo


def listar_pedidos(apenas_pendentes: bool = True) -> list:
    """Lista as compras de peça da aba Pedidos, pra vincular a um cliente
    pelo site em vez de digitar direto na planilha.

    Cada compra vira 2 linhas na planilha (CRIADO e APROVADO) porque o robô
    registra os dois eventos da CrediPay. Agrupa por nota fiscal e devolve
    uma entrada só, apontando pra linha que deve ser editada.
    """
    if not planilha_configurada():
        return []

    aba = _abrir_planilha().worksheet(ABA_PEDIDOS)
    todas = aba.get_all_values()

    por_nota = {}
    for numero_linha, linha in enumerate(todas[1:], start=2):
        def col(i):
            return linha[i - 1].strip() if len(linha) >= i else ""

        nota = col(2)
        if not nota:
            continue

        cliente_final = col(COL_NOME_CLIENTE_FINAL)
        situacao = col(COL_SITUACAO_OS)

        # Prefere a linha APROVADO como a "oficial" da compra; se já tem
        # cliente vinculado, essa linha manda.
        atual = por_nota.get(nota)
        eh_melhor = (
            atual is None
            or bool(cliente_final)
            or (col(5).upper() == "APROVADO" and not atual["cliente_final"])
        )
        if not eh_melhor:
            continue

        por_nota[nota] = {
            "linha": numero_linha,
            "nota_fiscal": nota,
            "valor": col(4),
            "status_compra": col(5),
            "data": col(6),
            "cliente_final": cliente_final,
            "numero_os": col(COL_NUMERO_OS),
            "situacao_os": situacao,
            "peca": col(COL_DESCRICAO_PECA),
        }

    pedidos = list(por_nota.values())
    if apenas_pendentes:
        pedidos = [p for p in pedidos if not p["cliente_final"]]

    pedidos.sort(key=lambda p: p["linha"], reverse=True)
    return pedidos


def atualizar_pedido(linha: int, cliente: str, peca: str, numero_os: str = "") -> dict:
    """Grava cliente/peça/OS numa linha da aba Pedidos."""
    if not planilha_configurada():
        return {"configurada": False}

    aba = _abrir_planilha().worksheet(ABA_PEDIDOS)

    aba.update_cell(linha, COL_NOME_CLIENTE_FINAL, cliente)
    aba.update_cell(linha, COL_DESCRICAO_PECA, peca)
    if numero_os:
        aba.update_cell(linha, COL_NUMERO_OS, numero_os)

    return {"configurada": True, "linha": linha}


def reverter(ficha: dict, servicos: list) -> dict:
    """Desfaz a baixa quando a rota é reaberta — senão site e planilha divergem
    e ninguém confia em nenhum dos dois."""
    if not planilha_configurada():
        return {"configurada": False}

    planilha = _abrir_planilha()
    aba = planilha.worksheet(ABA_PEDIDOS)
    todas = aba.get_all_values()
    linhas = [(i, l) for i, l in enumerate(todas[1:], start=2)]

    revertidas = 0
    for s in servicos:
        for numero_linha, linha in linhas:
            nome_planilha = normalizar(
                linha[COL_NOME_CLIENTE_FINAL - 1] if len(linha) >= COL_NOME_CLIENTE_FINAL else ""
            )
            situacao = (
                linha[COL_SITUACAO_OS - 1] if len(linha) >= COL_SITUACAO_OS else ""
            ).strip()
            if nome_planilha and situacao and nome_planilha == normalizar(s.get("cliente")):
                aba.update_cell(numero_linha, COL_SITUACAO_OS, "")
                try:
                    aba.format(f"A{numero_linha}:J{numero_linha}",
                               {"backgroundColor": {"red": 1, "green": 1, "blue": 1}})
                except Exception:
                    pass
                revertidas += 1
                break

    return {"configurada": True, "revertidas": revertidas}
