"""Lê os itens (peças) das notas fiscais direto do XML da NF-e.

A Panasonic manda por e-mail, de suite.nfe@br.panasonic.com, um XML anexo
cujo nome é a chave de 44 dígitos da nota — a mesma chave que a planilha de
Pedidos guarda na coluna "Numero Nota Fiscal". Então dá pra ligar
nota → peça de forma determinística, sem adivinhar nada.

Isso é bem melhor que tentar deduzir a peça pelos e-mails da loja (VTEX),
que nem sequer citam a nota fiscal: o XML é o documento oficial, traz código,
descrição, quantidade e valor — e a voltagem correta vem escrita na descrição
(127V / 220V), que é exatamente o que não se pode errar.
"""
import email
import hashlib
import imaplib
import logging
import os
import re
import socket
import time
import xml.etree.ElementTree as ET
from email.header import decode_header
from typing import Dict, List, Optional

log = logging.getLogger("portotec.nfe")

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}
REMETENTE_NFE = os.environ.get("REMETENTE_NFE", "suite.nfe")
TIMEOUT_IMAP = 30


def imap_configurado() -> bool:
    return bool((os.environ.get("IMAP_USER") or "").strip()
                and (os.environ.get("IMAP_PASSWORD") or "").strip())


def diagnostico_imap(testar_conexao: bool = False) -> dict:
    """Estado do acesso ao e-mail, sem expor a senha.

    Erros comuns num painel de deploy: a variável não salvar, salvar com
    espaço sobrando, ou a senha de app do Gmail chegar truncada.
    """
    usuario = (os.environ.get("IMAP_USER") or "").strip()
    senha = os.environ.get("IMAP_PASSWORD") or ""

    info = {
        "configurado": imap_configurado(),
        "tem_usuario": bool(usuario),
        "usuario": usuario,
        "tem_senha": bool(senha.strip()),
        "tamanho_senha": len(senha),
        "senha_tem_espaco_nas_pontas": senha != senha.strip(),
        "host": os.environ.get("IMAP_HOST", "imap.gmail.com"),
        "porta": os.environ.get("IMAP_PORT", "993"),
        # Só os NOMES das variáveis parecidas — nunca os valores. Serve pra
        # flagrar erro de digitação no nome (IMAP_PASSWORLD, IMAP_SENHA...),
        # que é indistinguível de "variável não salva" olhando só o resultado.
        "variaveis_parecidas": sorted(
            nome for nome in os.environ
            if any(p in nome.upper() for p in ("IMAP", "MAIL", "SENHA", "PASS"))
        ),
    }

    if testar_conexao and info["configurado"]:
        try:
            conn = _conectar()
            status, data = conn.search(None, "FROM", REMETENTE_NFE)
            info["conexao"] = "ok"
            info["emails_de_nfe"] = len(data[0].split()) if status == "OK" else 0
            # Assunto/remetente dos mais recentes da caixa inteira (não só
            # NF-e) — pedido de 2026-09-03: "puxa os pedidos que foram
            # feitos" precisa primeiro saber que CARA tem o e-mail de
            # confirmação de pedido da Panasonic (assunto/remetente), que
            # é diferente do e-mail de nota fiscal que este arquivo já lê.
            # Só cabeçalho (rápido, sem baixar anexo nenhum).
            info["emails_recentes"] = _cabecalhos_recentes(conn, 20)
            conn.logout()
        except Exception as exc:
            info["conexao"] = "falhou"
            info["erro"] = str(exc)[:200]

    return info


def _cabecalhos_recentes(conn, limite: int) -> List[dict]:
    status, data = conn.search(None, "ALL")
    if status != "OK" or not data or not data[0]:
        return []
    ids = sorted(data[0].split(), key=lambda x: -int(x))[:limite]
    resultado = []
    for mid in ids:
        try:
            status, d = conn.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != "OK" or not d or not d[0]:
                continue
            msg = email.message_from_bytes(d[0][1])
            resultado.append({
                "de": msg.get("From", ""), "assunto": msg.get("Subject", ""),
                "data": msg.get("Date", ""),
            })
        except Exception as exc:
            log.warning("Falha lendo cabeçalho do e-mail %s: %s", mid, exc)
    return resultado


def _decodificar_assunto(bruto: str) -> str:
    """`Message.get('Subject')` devolve o cabeçalho cru — se vier em
    'encoded-word' (=?UTF-8?Q?...?=) tem que decodificar antes de dar match
    em regex, senão nunca casa. Alguns remetentes (VTEX, neste arquivo) não
    chegam a codificar; `decode_header` lida com os dois casos igual.
    Espaços/quebras de linha de dobra de cabeçalho viram um espaço só.
    """
    partes = decode_header(bruto or "")
    texto = "".join(
        p.decode(enc or "utf-8", errors="replace") if isinstance(p, bytes) else p
        for p, enc in partes
    )
    return re.sub(r"\s+", " ", texto).strip()


# "Seu pedido de ARADGC606120 - Gaxeta... e mais 1 item(ns) foi realizado
# com sucesso!" -- é o e-mail que a loja (VTEX) manda na hora em que o
# PEDIDO é feito, bem antes da nota fiscal existir. A mesma loja manda um
# e-mail parecido pra cada etapa seguinte (pagamento aprovado, faturado,
# enviado) -- aqui só interessa esta primeira, "foi feito o pedido", pedido
# de 2026-09-03: "puxa só os pedidos que foram feito" / "tire os faturados,
# deixe só os emitidos".
_RE_PEDIDO_EMITIDO = re.compile(
    r"seu pedido de\s+(?P<codigo>\S+)\s*-\s*(?P<descricao>.+?)"
    r"(?:\s+e mais\s+\d+\s+item\(ns\))?\s+foi realizado com sucesso!?\s*$",
    re.IGNORECASE,
)


def _candidatos_pedidos_emitidos(conn, limite: int) -> List[dict]:
    """Escaneia só CABEÇALHOS (rápido) e devolve os que batem no assunto de
    'pedido emitido', com o `mid` (id IMAP) junto. Compartilhado por
    `pedidos_emitidos_recentes` (lista rápida) e
    `descricoes_emitidos_por_chave` (busca o corpo, lenta, só do que foi
    pedido) -- ver o porquê da separação nesta última.

    Busca por remetente NO SERVIDOR (2026-09-04, achado hoje: buscar "ALL" e
    filtrar VTEX no cliente, um fetch de cabeçalho por e-mail da caixa
    inteira, era rápido o bastante ontem mas passou de 30s hoje com o IMAP
    mais lento -- Railway cortava a resposta e a tela quebrava. "FROM vtex"
    faz o próprio Gmail filtrar antes de mandar qualquer coisa: só busca
    cabeçalho de quem já é candidato de verdade, não de todo e-mail recente
    (nota fiscal, Zendesk, código de acesso...). Prazo por tempo continua
    como rede de segurança, não como estratégia principal.
    """
    status, data = conn.search(None, "FROM", "vtex")
    if status != "OK" or not data or not data[0]:
        return []

    ids = sorted(data[0].split(), key=lambda x: -int(x))[:limite]
    candidatos = []
    prazo = time.monotonic() + 15
    for mid in ids:
        if time.monotonic() > prazo:
            log.warning("Varredura de pedidos emitidos cortada por tempo (%d/%d e-mails vistos)",
                        len(candidatos), len(ids))
            break
        try:
            status, d = conn.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != "OK" or not d or not d[0]:
                continue
            msg = email.message_from_bytes(d[0][1])
            assunto = _decodificar_assunto(msg.get("Subject", ""))
            m = _RE_PEDIDO_EMITIDO.search(assunto)
            if not m:
                continue
            # A própria VTEX trunca a descrição no assunto ("Gaxet...")
            # -- só limpa os espaços e troca "..."/".." por "…" pra não
            # parecer um nome de peça pela metade sem indicar que foi
            # cortado. Serve de descrição PROVISÓRIA até
            # descricoes_emitidos_por_chave trazer a completa.
            descricao = re.sub(r"\.{2,}$", "…", m.group("descricao").strip())
            codigo = m.group("codigo").strip()
            data_email = msg.get("Date", "")
            candidatos.append({
                "mid": mid,
                # Identidade estável entre uma consulta e outra -- o mesmo
                # código pode ser comprado de novo em outro dia, então o
                # hash usa código+data (não só o código) pra não colidir
                # duas compras diferentes na mesma "chave" (ver
                # routes/pedidos.py: é essa chave que guarda o vínculo com
                # cliente na tabela pedidos_email).
                "chave": "em" + hashlib.sha1(f"{codigo}|{data_email}".encode()).hexdigest()[:14],
                "codigo": codigo,
                "descricao": descricao,
                "data": data_email,
            })
        except Exception as exc:
            log.warning("Falha lendo e-mail de pedido emitido %s: %s", mid, exc)
    return candidatos


def pedidos_emitidos_recentes(limite: int = 80) -> List[dict]:
    """Pedidos feitos na loja da Panasonic, direto do e-mail de confirmação
    -- não espera o robô da planilha achar a nota fiscal (que só chega bem
    depois, e às vezes nem chega se o pedido for cancelado no meio).

    Só cabeçalho (rápido): a descrição vem truncada pela VTEX ("Gaxet...").
    O nome completo é buscado à parte, por `descricoes_emitidos_por_chave`
    -- juntar os dois numa chamada só chegou a estourar 30s pra ~8 pedidos
    (Railway corta em ~30s, achado em 2026-09-04) porque cada nome completo
    exige baixar o e-mail INTEIRO (RFC822), não só o cabeçalho.
    """
    if not imap_configurado():
        return []

    conn = None
    try:
        conn = _conectar()
        candidatos = _candidatos_pedidos_emitidos(conn, limite)
        for c in candidatos:
            c.pop("mid", None)
        return candidatos
    except Exception:
        log.exception("Falha ao buscar pedidos emitidos por e-mail")
        return []
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass


def descricoes_emitidos_por_chave(chaves: List[str], limite: int = 80) -> Dict[str, str]:
    """Nome completo da peça (do CORPO do e-mail) só pras chaves pedidas.

    Endpoint/chamada separada de propósito, em lotes pequenos do lado do
    front (mesma ideia de GET /pedidos/sugestoes pra nota fiscal): buscar o
    corpo INTEIRO de cada e-mail é lento o bastante pra estourar o timeout
    do Railway se feito pra todos de uma vez (ver pedidos_emitidos_recentes).
    """
    if not chaves or not imap_configurado():
        return {}

    procuradas = set(chaves)
    conn = None
    try:
        conn = _conectar()
        candidatos = _candidatos_pedidos_emitidos(conn, limite)
        resultado = {}
        # Prazo próprio pra essa parte, à parte do prazo da varredura de
        # cabeçalho -- as duas juntas não podem passar do limite do Railway.
        # O front já manda em lotes pequenos (2), então isso raramente
        # deveria disparar; é rede de segurança, não o caminho normal.
        prazo = time.monotonic() + 12
        for c in candidatos:
            if c["chave"] not in procuradas:
                continue
            if time.monotonic() > prazo:
                log.warning("Busca de descrição completa cortada por tempo (%d/%d)",
                            len(resultado), len(procuradas))
                break
            descricao_longa = _descricao_completa_do_corpo(conn, c["mid"], c["codigo"])
            if descricao_longa:
                resultado[c["chave"]] = descricao_longa
        return resultado
    except Exception:
        log.exception("Falha ao buscar descrição completa dos pedidos emitidos")
        return {}
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass


def _corpo_texto(msg) -> str:
    """Corpo do e-mail em texto simples, espaço colapsado -- prefere
    text/plain; se só houver text/html, tira as tags na marra (sem lib de
    parsing de HTML, que este projeto não usa em nenhum outro lugar)."""
    corpo_html = None
    partes = msg.walk() if msg.is_multipart() else [msg]
    for parte in partes:
        if parte.is_multipart():
            continue
        ctype = parte.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        try:
            bruto = parte.get_payload(decode=True)
            if bruto is None:
                continue
            texto = bruto.decode(parte.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            continue
        if ctype == "text/plain":
            return re.sub(r"\s+", " ", texto).strip()
        if corpo_html is None:
            corpo_html = texto

    if corpo_html:
        texto = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", corpo_html, flags=re.DOTALL | re.IGNORECASE)
        texto = re.sub(r"<[^>]+>", " ", texto)
        texto = re.sub(r"&nbsp;", " ", texto)
        return re.sub(r"\s+", " ", texto).strip()
    return ""


def _descricao_completa_do_corpo(conn, mid, codigo: str) -> Optional[str]:
    """Nome completo da peça, lido do CORPO do e-mail (o assunto vem
    truncado pela VTEX, ex: "Gaxet..."). Achado investigando em 2026-09-04:
    o corpo do e-mail (HTML) repete a descrição da peça duas vezes seguidas
    logo depois do código -- sobra do template renderizar o mesmo dado em
    dois elementos visuais (nome + tooltip/alt, por exemplo) que a extração
    de texto (que tira as tags) junta numa frase só:

        "Receber ARADGC606120 - Gaxeta porta FC / Gasket door FC BB64-5
         Gaxeta porta FC / Gasket door FC BB64-5 até 07/09/2026 ..."

    Captura o texto entre o código e essa repetição -- é o nome completo,
    sem o corte que o assunto tem.
    """
    try:
        status, d = conn.fetch(mid, "(RFC822)")
        if status != "OK" or not d or not d[0]:
            return None
        msg = email.message_from_bytes(d[0][1])
        corpo = _corpo_texto(msg)
    except Exception as exc:
        log.warning("Falha lendo corpo do e-mail %s: %s", mid, exc)
        return None

    if not corpo:
        return None

    m = re.search(re.escape(codigo) + r"\s*-\s*(.+?)\s+\1(?:\s|$)", corpo)
    if not m:
        return None
    return m.group(1).strip()


def _conectar():
    socket.setdefaulttimeout(TIMEOUT_IMAP)
    conn = imaplib.IMAP4_SSL(
        os.environ.get("IMAP_HOST", "imap.gmail.com"),
        int(os.environ.get("IMAP_PORT", "993")),
    )
    conn.login(os.environ["IMAP_USER"], os.environ["IMAP_PASSWORD"])
    conn.select(os.environ.get("IMAP_PASTA", "INBOX"), readonly=True)
    return conn


def _itens_do_xml(bruto: bytes) -> List[dict]:
    try:
        raiz = ET.fromstring(bruto)
    except ET.ParseError as exc:
        log.warning("XML de NF-e ilegível: %s", exc)
        return []

    itens = []
    for det in raiz.findall(".//n:det", NS):
        prod = det.find("n:prod", NS)
        if prod is None:
            continue
        itens.append({
            "codigo": (prod.findtext("n:cProd", "", NS) or "").strip(),
            "descricao": (prod.findtext("n:xProd", "", NS) or "").strip(),
            "quantidade": (prod.findtext("n:qCom", "", NS) or "").strip(),
            "valor": (prod.findtext("n:vProd", "", NS) or "").strip(),
        })
    return itens


def _resumir(itens: List[dict]) -> str:
    """Texto curto pra coluna 'Descricao Peca' da planilha.

    Um item só: 'CODIGO - DESCRIÇÃO'. Vários: lista os códigos, porque a
    célula tem que caber na tela e o código é o que identifica a peça.
    """
    if not itens:
        return ""
    if len(itens) == 1:
        i = itens[0]
        return f"{i['codigo']} - {i['descricao']}".strip(" -")
    codigos = ", ".join(i["codigo"] for i in itens if i["codigo"])
    return f"{len(itens)} itens: {codigos}"


def itens_de_uma_nota(chave: str) -> dict:
    """Busca DIRECIONADA de UMA nota pela chave — rápida o bastante para caber
    numa requisição web (é o que o 'bipar' usa).

    Devolve um dict com `status`:
      - "off"   : IMAP desligado ou chave inválida (a tela pede o XML)
      - "ok"    : achou; `itens` preenchido
      - "vazio" : buscou e não achou o XML dessa nota
      - "erro"  : falha/timeout ao ler o e-mail; `motivo` explica (mostra na tela)

    Por que é rápida (o pecas_por_nota varria TUDO e dava 502): no Gmail o
    X-GM-RAW acha o e-mail exato pela chave; senão, varre só os MAIS RECENTES —
    a nota bipada acabou de chegar, está no topo. Fetch limitado e socket curto
    impedem travar o gateway.
    """
    chave = re.sub(r"\D", "", chave or "")
    if len(chave) != 44 or not imap_configurado():
        return {"status": "off", "itens": []}

    conn = None
    try:
        conn = _conectar()
        # Socket curto: melhor "não deu, cole o XML" em ~15s do que 502.
        socket.setdefaulttimeout(15)

        ids = []
        try:
            status, data = conn.search(None, "X-GM-RAW", chave)  # Gmail: tiro certo
            if status == "OK" and data and data[0]:
                ids = data[0].split()
        except Exception as exc:
            log.warning("X-GM-RAW indisponível (%s); usando varredura recente", exc)

        if not ids:
            status, data = conn.search(None, "FROM", REMETENTE_NFE)
            if status == "OK" and data and data[0]:
                # Recentes primeiro e no máximo 25 — os e-mails de NF-e são só o
                # XML (pequenos), então isso resolve em poucos segundos.
                ids = sorted(data[0].split(), key=lambda x: -int(x))[:25]

        for mid in ids:
            try:
                status, d = conn.fetch(mid, "(RFC822)")
                if status != "OK" or not d or not d[0]:
                    continue
                msg = email.message_from_bytes(d[0][1])
            except Exception:
                continue
            for parte in msg.walk():
                nome = parte.get_filename() or ""
                if not nome.lower().endswith(".xml"):
                    continue
                if re.sub(r"\D", "", nome)[:44] != chave:
                    continue
                itens = _itens_do_xml(parte.get_payload(decode=True))
                if itens:
                    return {"status": "ok", "itens": itens}

        return {"status": "vazio", "itens": []}
    except Exception as exc:
        log.exception("Busca direcionada da nota %s falhou", chave[:8])
        return {"status": "erro", "itens": [], "motivo": str(exc)[:200]}
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass


def pecas_por_nota(chaves: List[str]) -> Dict[str, dict]:
    """Devolve {chave_da_nota: {"resumo": str, "itens": [...]}}.

    Só olha os e-mails de NF-e; ignora chave que não achar.
    """
    procuradas = {re.sub(r"\D", "", c) for c in chaves if c}
    procuradas = {c for c in procuradas if len(c) == 44}
    if not procuradas or not imap_configurado():
        return {}

    achadas: Dict[str, dict] = {}
    conn = None
    try:
        conn = _conectar()
        status, data = conn.search(None, "FROM", REMETENTE_NFE)
        if status != "OK":
            return {}

        # Do mais recente pro mais antigo: para assim que achar todas.
        for mid in sorted(data[0].split(), key=lambda x: -int(x)):
            if not procuradas - set(achadas):
                break
            try:
                status, d = conn.fetch(mid, "(RFC822)")
                if status != "OK" or not d or not d[0]:
                    continue
                msg = email.message_from_bytes(d[0][1])
            except Exception as exc:
                log.warning("Falha ao ler e-mail %s: %s", mid, exc)
                continue

            for parte in msg.walk():
                nome = parte.get_filename() or ""
                if not nome.lower().endswith(".xml"):
                    continue
                chave = re.sub(r"\D", "", nome)[:44]
                if chave not in procuradas or chave in achadas:
                    continue
                try:
                    itens = _itens_do_xml(parte.get_payload(decode=True))
                except Exception as exc:
                    log.warning("Falha ao extrair itens de %s: %s", nome, exc)
                    continue
                if itens:
                    achadas[chave] = {"resumo": _resumir(itens), "itens": itens}
    except Exception:
        log.exception("Falha ao buscar peças nas notas fiscais")
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass

    return achadas
