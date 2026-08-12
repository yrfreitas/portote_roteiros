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
