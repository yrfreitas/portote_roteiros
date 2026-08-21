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
import imaplib
import logging
import os
import re
import socket
import xml.etree.ElementTree as ET
from typing import Dict, List

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
            conn.logout()
        except Exception as exc:
            info["conexao"] = "falhou"
            info["erro"] = str(exc)[:200]

    return info


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


def itens_de_uma_nota(chave: str):
    """Busca DIRECIONADA de UMA nota pela chave — rápida o bastante para caber
    numa requisição web (é o que o 'bipar' usa).

    O pecas_por_nota varre TODOS os e-mails da Panasonic baixando cada um
    inteiro até achar — 24s+ — e estourava o timeout do gateway (502 ao bipar).
    Aqui a busca é mirada: no Gmail o X-GM-RAW acha o e-mail exato pela chave
    (indexa nome do anexo e conteúdo); fora do Gmail, cai num fallback limitado
    aos mais recentes. Um socket curto impede travar.

    Retorno: lista de itens se achou; [] se buscou e não achou; None se NÃO deu
    para buscar (IMAP desligado, timeout, erro) — a tela então pede o XML."""
    chave = re.sub(r"\D", "", chave or "")
    if len(chave) != 44 or not imap_configurado():
        return None

    conn = None
    try:
        conn = _conectar()
        # Encurta o socket para search/fetch: melhor devolver "não deu, cole o
        # XML" em ~12s do que deixar o gateway cortar em 502.
        socket.setdefaulttimeout(12)

        ids = []
        try:
            status, data = conn.search(None, "X-GM-RAW", f'"{chave}"')
            if status == "OK" and data and data[0]:
                ids = data[0].split()
        except Exception:
            ids = []  # servidor não-Gmail: usa o fallback abaixo

        if not ids:
            status, data = conn.search(None, "FROM", REMETENTE_NFE)
            if status == "OK" and data and data[0]:
                # Só os mais recentes: sem isso o fallback repete o problema.
                ids = sorted(data[0].split(), key=lambda x: -int(x))[:30]

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
                    return itens
        return []
    except Exception:
        log.exception("Busca direcionada da nota %s falhou", chave[:8])
        return None
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
