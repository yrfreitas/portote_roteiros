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
    "Descrição", "Técnico", "Ficha (dia)", "Nº OS", "Motivo",
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
    return not faltando_para_configurar()


def faltando_para_configurar() -> list:
    """Diz exatamente o que falta, pra não ter que adivinhar qual variável
    de ambiente ficou de fora. Nunca devolve o valor de nada — só o nome."""
    falta = []

    bruto = (os.environ.get("GOOGLE_CREDENTIALS_JSON") or "").strip()
    caminho = (os.environ.get("GOOGLE_CREDENTIALS_PATH") or "").strip()

    if not bruto and not caminho:
        falta.append("GOOGLE_CREDENTIALS_JSON (ou GOOGLE_CREDENTIALS_PATH)")
    elif bruto:
        # Erro comum: colar o JSON e o valor chegar truncado/escapado.
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError as exc:
            falta.append(f"GOOGLE_CREDENTIALS_JSON não é um JSON válido ({exc.msg})")
        else:
            for chave in ("client_email", "private_key", "token_uri"):
                if not dados.get(chave):
                    falta.append(f"GOOGLE_CREDENTIALS_JSON sem o campo '{chave}'")

    if not (os.environ.get("PLANILHA_ID") or "").strip():
        falta.append("PLANILHA_ID")

    return falta


def diagnostico() -> dict:
    """Estado da integração, sem vazar segredo — só o que dá pra conferir."""
    bruto = (os.environ.get("GOOGLE_CREDENTIALS_JSON") or "").strip()
    email = ""
    if bruto:
        try:
            email = json.loads(bruto).get("client_email", "")
        except json.JSONDecodeError:
            email = "(JSON inválido)"

    return {
        "configurada": planilha_configurada(),
        "faltando": faltando_para_configurar(),
        "tem_credentials_json": bool(bruto),
        "tamanho_credentials_json": len(bruto),
        "tem_credentials_path": bool(os.environ.get("GOOGLE_CREDENTIALS_PATH")),
        "tem_planilha_id": bool((os.environ.get("PLANILHA_ID") or "").strip()),
        "conta_de_servico": email,
        "aba_pedidos": ABA_PEDIDOS,
    }


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
        aba = planilha.worksheet(ABA_OUTROS)
        # A aba pode ter sido criada com menos colunas numa versão anterior.
        # Sem migrar o cabeçalho, um campo novo entraria na coluna do campo
        # antigo e embaralharia tudo que já está gravado.
        atual = aba.row_values(1)
        if len(atual) < len(CABECALHO_OUTROS):
            if aba.col_count < len(CABECALHO_OUTROS):
                aba.add_cols(len(CABECALHO_OUTROS) - aba.col_count)
            aba.update(
                values=[CABECALHO_OUTROS],
                range_name=f"A1:{chr(64 + len(CABECALHO_OUTROS))}1",
                value_input_option="USER_ENTERED",
            )
            log.info("Cabeçalho da aba '%s' migrado para %d colunas",
                     ABA_OUTROS, len(CABECALHO_OUTROS))
        return aba
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

    Ordem de confiança:
      1. Nº da OS igual        -> certeza, é identificador único
      2. Nome + modelo         -> forte
      3. Só o nome             -> fraco, marca amarelo pra conferir

    Devolve {'linha': n, 'forca': ..., 'peca': ...} ou None. Só considera
    linhas ainda sem baixa — peça já conciliada não é reaproveitada.
    """
    nome_alvo = normalizar(servico.get("cliente"))
    os_alvo = _so_alfanumerico(servico.get("numero_os"))

    # Nº da OS bate? acabou a discussão — não precisa nem de nome.
    if os_alvo:
        for numero_linha, linha in linhas:
            situacao = (
                linha[COL_SITUACAO_OS - 1] if len(linha) >= COL_SITUACAO_OS else ""
            ).strip()
            if situacao:
                continue
            os_planilha = _so_alfanumerico(
                linha[COL_NUMERO_OS - 1] if len(linha) >= COL_NUMERO_OS else ""
            )
            if os_planilha and os_planilha == os_alvo:
                peca = (linha[COL_DESCRICAO_PECA - 1]
                        if len(linha) >= COL_DESCRICAO_PECA else "")
                return {"linha": numero_linha, "forca": "nº da OS", "peca": peca}

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
                "numero_os": s.get("numero_os") or "",
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
                "numero_os": s.get("numero_os") or "",
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

        # Prefere o nº real da OS (do DigiTeam); só cai pro dia da ficha se
        # o ponto não tiver OS preenchida — o dia é identificação fraca.
        atual = (todas[n - 1][COL_NUMERO_OS - 1]
                 if len(todas[n - 1]) >= COL_NUMERO_OS else "").strip()
        if not atual:
            aba_pedidos.update_cell(
                n, COL_NUMERO_OS, c.get("numero_os") or identificacao_ficha
            )

        cor = AMARELO if c["forca"] == "nome" else VERDE
        try:
            aba_pedidos.format(f"A{n}:J{n}", {"backgroundColor": cor})
        except Exception as exc:
            log.warning("Não consegui pintar a linha %s: %s", n, exc)

    # registra os que não casaram
    if outros:
        aba_outros = _obter_ou_criar_outros(planilha)
        aba_outros.append_rows(
            [[agora, o["cliente"], o["endereco"], o["aparelho"], o["modelo"],
              o["descricao"], tecnico_nome, identificacao_ficha,
              o.get("numero_os", ""), o["motivo"]]
             for o in outros],
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
            table_range="A1",
        )

    return resumo


def listar_pedidos(apenas_pendentes: bool = True, incluir_criado: bool = False) -> list:
    """Lista as compras de peça da aba Pedidos, pra vincular a um cliente
    pelo site em vez de digitar direto na planilha.

    Cada compra vira 2 linhas na planilha (CRIADO e APROVADO) porque o robô
    registra os dois eventos da CrediPay. Agrupa por nota fiscal e devolve
    uma entrada só, apontando pra linha que deve ser editada.

    `incluir_criado`: CRIADO ficava sempre fora (ver comentário mais abaixo)
    até o Kalebe pedir o contrário em 2026-09-03 -- precisa vincular
    cliente/agendar visita já no pedido EMITIDO, sem esperar o pagamento
    aprovar, pra não perder tempo de agenda. Continua False por padrão pra
    não mudar comportamento de quem chama sem saber desse parâmetro.
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

        # AGRUPA POR NOTA **OU** POR PEDIDO.
        #
        # Até 18/08/2026 toda compra vinha da CrediPay e trazia nota fiscal, e
        # exigir a nota bastava. A Panasonic mudou a origem dos e-mails para a
        # loja VTEX, que avisa a compra ANTES de faturar — o e-mail diz, com
        # todas as letras, "estamos providenciando a emissão da nota fiscal".
        # Essas compras chegam à planilha com a coluna de nota VAZIA, e o
        # `if not nota: continue` as descartava: sumiam da tela de Peças sem
        # deixar rastro, justamente as mais recentes.
        #
        # A coluna A guarda o identificador do registro (`nota#STATUS` no
        # formato antigo, `PED{pedido}#STATUS` no novo). Sem nota, ele é a
        # identidade da compra.
        identificador = col(1)
        chave = nota or identificador.rsplit("#", 1)[0]
        if not chave:
            continue

        # Número do pedido puro, quando a coluna A segue o formato novo
        # ("PED12345#STATUS") — existe INDEPENDENTE de ter nota ou não, pra
        # servir de elo entre a linha de antes de faturar (chave = "PED12345")
        # e a linha de depois (chave = a própria nota, uma vez que ela chega).
        # Sem esse elo, as duas viravam duas entradas em por_nota — a mesma
        # compra "duplicada" na tela, o que o Kalebe segue reportando mesmo
        # depois do filtro de CRIADO (que não pega esse caso: a linha antiga
        # muitas vezes já está como APROVADO, não CRIADO, quando a nota chega).
        pedido_num = (identificador.split("#", 1)[0][3:]
                     if identificador.startswith("PED") else "")

        cliente_final = col(COL_NOME_CLIENTE_FINAL)
        situacao = col(COL_SITUACAO_OS)

        # Prefere a linha APROVADO como a "oficial" da compra; se já tem
        # cliente vinculado, essa linha manda.
        atual = por_nota.get(chave)
        eh_melhor = (
            atual is None
            or bool(cliente_final)
            or (col(5).upper() == "APROVADO" and not atual["cliente_final"])
        )
        if not eh_melhor:
            continue

        por_nota[chave] = {
            "linha": numero_linha,
            "nota_fiscal": nota,
            "_pedido_num": pedido_num,
            # Número do pedido na loja, quando a compra ainda não tem nota.
            # É o que a tela mostra no lugar do "NF ..." para não exibir um
            # rótulo vazio.
            # Fatiamento em vez de removeprefix(): não há runtime.txt fixando
            # a versão do Python no deploy, e removeprefix só existe do 3.9 em
            # diante. Não vale arriscar a tela de Peças numa conveniência.
            "pedido": "" if nota else (chave[3:] if chave.startswith("PED") else chave),
            "valor": col(4),
            "status_compra": col(5),
            "data": col(6),
            "cliente_final": cliente_final,
            "numero_os": col(COL_NUMERO_OS),
            "situacao_os": situacao,
            "peca": col(COL_DESCRICAO_PECA),
        }

    # Funde entradas que são a MESMA compra sob chaves diferentes: uma sem
    # nota (identificada só pelo nº do pedido) e outra já com nota (chave =
    # a própria nota, uma vez que ela chega). Sem isso as duas ficavam em
    # por_nota como se fossem peças diferentes — a duplicata que persistia
    # mesmo com o filtro de CRIADO, porque a linha sem nota já costuma estar
    # como APROVADO quando a nota sai, não CRIADO.
    por_pedido = {}
    for chave, p in list(por_nota.items()):
        num = p.get("_pedido_num")
        if not num:
            continue
        rival = por_pedido.get(num)
        if rival is None:
            por_pedido[num] = chave
            continue
        anterior = por_nota[rival]
        # A que já tem nota fiscal é a mais avançada (faturada de verdade);
        # entre duas sem nota, fica a de linha mais recente.
        atual_vence = bool(p["nota_fiscal"]) or (
            not anterior["nota_fiscal"] and p["linha"] > anterior["linha"]
        )
        vencedora, perdedora = (p, anterior) if atual_vence else (anterior, p)
        chave_vencedora, chave_perdedora = (chave, rival) if atual_vence else (rival, chave)

        # A perdedora pode já ter o que a vencedora ainda não tem — o vínculo
        # com cliente é o caso real: alguém já digitou o nome na linha sem
        # nota, e a linha da nota (mais nova) chega vazia. Herda em vez de
        # jogar fora um trabalho que já foi feito.
        for campo in ("cliente_final", "numero_os", "situacao_os", "peca"):
            if not vencedora.get(campo) and perdedora.get(campo):
                vencedora[campo] = perdedora[campo]

        del por_nota[chave_perdedora]
        por_pedido[num] = chave_vencedora

    # CRIADO é o pedido no carrinho, antes do pagamento ser aprovado — pode
    # nunca virar compra de verdade (cliente desiste, cartão recusa). Peça
    # que ninguém pagou ainda não deveria aparecer pra vincular cliente de
    # qualquer jeito: mostrar antes de pagar é oferecer algo que pode nunca
    # chegar. (2026-09-03: o Kalebe decidiu assumir esse risco de propósito
    # — ver `incluir_criado` acima — porque o ganho de agendar cedo pesa
    # mais que o risco ocasional de um pedido cancelado.)
    #
    # O filtro de "só ENVIADO" (a caminho) fica em routes/pedidos.py:listar,
    # não aqui — tentei fazer aqui em 2026-08-29 e quebrou as peças que já
    # tinham sido marcadas "chegou" no site: o status_compra da planilha pode
    # avançar pra além de ENVIADO (ex: a Panasonic marca como concluída do
    # lado dela) sem que isso tenha nada a ver com o site já ter recebido a
    # caixa. Filtrar por ENVIADO aqui, ANTES de saber se já chegou, sumia com
    # peça que a pessoa já tinha fisicamente na mão.
    pedidos = list(por_nota.values())
    if not incluir_criado:
        pedidos = [p for p in pedidos if p["status_compra"].strip().upper() != "CRIADO"]
    if apenas_pendentes:
        pedidos = [p for p in pedidos if not p["cliente_final"]]

    for p in pedidos:
        p.pop("_pedido_num", None)

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


def listar_conciliadas_fracas() -> list:
    """Linhas com baixa que ficaram AMARELAS (casaram só pelo nome).

    Identifica pela cor de fundo, que é o que a conciliação usa pra sinalizar
    confiança: verde = nome+modelo ou nº da OS, amarelo = só o nome.
    """
    planilha = _abrir_planilha()
    aba = planilha.worksheet(ABA_PEDIDOS)
    valores = aba.get_all_values()

    # Busca as cores de fundo de uma vez só (uma chamada, não uma por linha).
    meta = aba.spreadsheet.fetch_sheet_metadata({
        "includeGridData": "true",
        "ranges": f"{ABA_PEDIDOS}!A2:A{len(valores)}",
        "fields": "sheets(data(rowData(values(effectiveFormat(backgroundColor)))))",
    })

    linhas_amarelas = set()
    try:
        grid = meta["sheets"][0]["data"][0].get("rowData", [])
        for i, row in enumerate(grid, start=2):
            vals = row.get("values") or []
            if not vals:
                continue
            cor = (vals[0].get("effectiveFormat") or {}).get("backgroundColor") or {}
            r, g, b = cor.get("red", 1), cor.get("green", 1), cor.get("blue", 1)
            # amarelo: vermelho e verde altos, azul claramente menor
            if r > 0.9 and g > 0.85 and b < 0.87:
                linhas_amarelas.add(i)
    except (KeyError, IndexError):
        log.warning("Não consegui ler as cores da planilha para revisão")

    itens = []
    for numero_linha, linha in enumerate(valores[1:], start=2):
        if numero_linha not in linhas_amarelas:
            continue

        def col(i):
            return linha[i - 1].strip() if len(linha) >= i else ""

        if not col(COL_SITUACAO_OS):
            continue

        itens.append({
            "linha": numero_linha,
            "cliente": col(COL_NOME_CLIENTE_FINAL),
            "numero_os": col(COL_NUMERO_OS),
            "situacao": col(COL_SITUACAO_OS),
            "peca": col(COL_DESCRICAO_PECA),
            "valor": col(4),
            "nota_fiscal": col(2),
        })

    return itens


def desfazer_baixa(linha: int) -> None:
    """Limpa a situação e volta a linha ao branco."""
    aba = _abrir_planilha().worksheet(ABA_PEDIDOS)
    aba.update_cell(linha, COL_SITUACAO_OS, "")
    try:
        aba.format(f"A{linha}:J{linha}",
                   {"backgroundColor": {"red": 1, "green": 1, "blue": 1}})
    except Exception as exc:
        log.warning("Não consegui limpar a cor da linha %s: %s", linha, exc)


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


# ─── Aba "Peças Solicitadas" ────────────────────────────────────────────
#
# Fecha o circuito que faltava. Até aqui a planilha só sabia das compras que a
# Panasonic avisava por e-mail — ou seja, do que JÁ foi comprado. O que o
# técnico pediu do campo não existia em lugar nenhum até virar compra, e
# ninguém conseguia responder "quais peças estão pendentes de pedido?".
#
# ABA PRÓPRIA, e não linha na aba Pedidos, pela mesma razão de sempre neste
# projeto: a aba Pedidos é escrita pelo robô a partir dos e-mails da
# Panasonic. Gravar ali uma solicitação interna misturaria duas origens e
# quebraria a conciliação, que casa por chave de nota.
ABA_SOLICITADAS = os.environ.get("ABA_SOLICITADAS", "Peças Solicitadas")

CABECALHO_SOLICITADAS = [
    "Data do Pedido", "Cliente", "Peça", "Aparelho", "Nº OS",
    "Técnico", "Observação", "Pedido por", "Atendimento",
]


def _aba_solicitadas(planilha):
    # Import local, como nas outras funções deste módulo: gspread não é
    # importado no topo para o site subir mesmo sem a integração instalada.
    import gspread

    try:
        return planilha.worksheet(ABA_SOLICITADAS)
    except gspread.WorksheetNotFound:
        log.info("Criando aba '%s'", ABA_SOLICITADAS)
        aba = planilha.add_worksheet(title=ABA_SOLICITADAS, rows=2000,
                                     cols=len(CABECALHO_SOLICITADAS))
        aba.append_row(CABECALHO_SOLICITADAS, value_input_option="USER_ENTERED")
        aba.freeze(rows=1)
        return aba


def registrar_peca_solicitada(dados: dict) -> dict:
    """Grava na planilha que a peça foi pedida para aquele cliente.

    `dados` traz cliente, peca, aparelho, numero_os, tecnico, observacao,
    pedido_por e servico_id.
    """
    if not planilha_configurada():
        return {"configurada": False}

    aba = _aba_solicitadas(_abrir_planilha())

    # A coluna "Atendimento" guarda o id do serviço no site. É o que permite,
    # depois, voltar da linha da planilha para o atendimento de origem — sem
    # isso a linha vira texto solto e ninguém sabe de qual visita veio.
    aba.append_row([
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        dados.get("cliente") or "",
        dados.get("peca") or "",
        dados.get("aparelho") or "",
        dados.get("numero_os") or "",
        dados.get("tecnico") or "",
        dados.get("observacao") or "",
        dados.get("pedido_por") or "",
        str(dados.get("servico_id") or ""),
    ], value_input_option="USER_ENTERED", table_range="A1")

    return {"configurada": True, "aba": ABA_SOLICITADAS}
