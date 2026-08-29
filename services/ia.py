"""Análise de erros com IA (Claude), para o botão 'Analisar com IA' no Diagnóstico.

O Kalebe aperta o botão num erro que apareceu na tela e a IA explica o que
provavelmente é e sugere a correção — em português, direto ao ponto. NÃO
conserta código sozinha (isso seria temerário): dá o diagnóstico e o caminho.

Degrada com elegância, igual às outras integrações (AgoraOS, IMAP): sem
ANTHROPIC_API_KEY, o serviço responde {"ativo": False} e a tela avisa em vez de
quebrar. A chamada fica no backend porque a chave NUNCA pode ir para o
navegador — é credencial, e credencial não sai do servidor.
"""
import logging
import os

log = logging.getLogger("portotec.ia")

# Modelo padrão recomendado pela Anthropic. Opus 5 pensa por padrão, o que dá
# uma análise melhor; o prompt é pequeno e a saída curta, então o custo por
# clique é de centavos.
MODELO = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")


def configurado() -> bool:
    return bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())


_SISTEMA = (
    "Você é a Bia, engenheira de software da Porto Tec. Recebe um erro de "
    "JavaScript que aconteceu no navegador de quem usa um painel Flask + JS "
    "puro (sem framework). Explique em português, para o Kalebe (dev júnior), "
    "de forma curta e prática:\n"
    "1. O que esse erro provavelmente significa (uma ou duas frases).\n"
    "2. A causa mais provável, ligada ao tipo de erro.\n"
    "3. O que checar/corrigir — passos objetivos, citando arquivo/função quando "
    "der para inferir pela URL ou mensagem.\n"
    "Seja direta e sem floreio. Não invente stack trace que não recebeu. Se a "
    "mensagem for genérica demais para diagnosticar, diga o que falta capturar."
)


def analisar_erro(erro: dict) -> dict:
    """Recebe um registro de erro_cliente e devolve a análise da IA.

    Retorno: {"ativo": bool, "analise": str} ou {"ativo": False, "erro": str}.
    """
    if not configurado():
        return {"ativo": False,
                "motivo": "ANTHROPIC_API_KEY não configurada no servidor."}

    # Import tardio: só carrega o SDK quando o botão é usado, e um ambiente sem
    # o pacote instalado não derruba o resto do sistema no import.
    try:
        import anthropic
    except ImportError:
        return {"ativo": False,
                "motivo": "Pacote 'anthropic' não instalado no servidor."}

    contexto = (
        f"Mensagem: {erro.get('mensagem') or '—'}\n"
        f"Origem: {erro.get('origem') or '—'}\n"
        f"Versão do app: {erro.get('versao') or '—'}\n"
        f"URL/Tela: {erro.get('url') or '—'}\n"
        f"Quando: {erro.get('quando') or '—'}"
    )

    try:
        client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
        resposta = client.messages.create(
            model=MODELO,
            max_tokens=3000,  # cobre o pensamento (ligado por padrão no Opus 5) + a resposta
            system=_SISTEMA,
            messages=[{"role": "user", "content":
                       f"Analise este erro:\n\n{contexto}"}],
        )
        # Refusal chega como 200 com stop_reason='refusal' — trata antes de ler content.
        if getattr(resposta, "stop_reason", None) == "refusal":
            return {"ativo": True, "analise": "A IA recusou analisar este conteúdo."}
        texto = "".join(b.text for b in resposta.content if getattr(b, "type", None) == "text")
        return {"ativo": True, "analise": texto.strip() or "A IA não retornou texto."}
    except Exception as exc:
        log.exception("Falha ao analisar erro com IA")
        return {"ativo": False, "motivo": f"Falha ao chamar a IA: {str(exc)[:200]}"}


# Prompt do CHAT (diferente do de análise de erro acima) — pedido de
# 2026-08-29: uma conversa de verdade no Diagnóstico, não só um botão de
# analisar erro. A ressalva do 3º parágrafo é deliberada e repetida de
# propósito: sem ela, é fácil o Kalebe achar que digitar aqui muda o
# sistema — e essa IA não tem acesso nenhum pra editar arquivo, rodar
# teste ou dar deploy, só o histórico da conversa que ela mesma lê.
_SISTEMA_CHAT = (
    "Você é a Bia, engenheira de software da Porto Tec, conversando com o "
    "Kalebe (dev júnior) dentro do painel de Diagnóstico do próprio site "
    "(Flask + JS puro, Postgres em produção/SQLite local, hospedado no "
    "Railway). Ajude a entender erros, decisões técnicas e como as coisas "
    "funcionam, em português, direto ao ponto, sem floreio.\n\n"
    "IMPORTANTE: você NÃO tem acesso ao código-fonte, ao banco de dados "
    "nem a nada além desta conversa — não pode editar arquivo, rodar "
    "teste, fazer commit ou deploy. Se o Kalebe pedir uma mudança no "
    "sistema, diga claramente que ele precisa pedir isso na conversa com "
    "o Claude Code (a sessão que programa de verdade), não aqui."
)


def conversar(historico: list) -> dict:
    """Um turno do chat de diagnóstico. `historico` é uma lista de
    {"autor": "kalebe"|"ia", "texto": str}, mais antigo primeiro, já
    incluindo a mensagem nova do Kalebe por último.

    Retorno: {"ativo": bool, "resposta": str} ou {"ativo": False, "motivo": str}.
    """
    if not configurado():
        return {"ativo": False,
                "motivo": "ANTHROPIC_API_KEY não configurada no servidor."}
    try:
        import anthropic
    except ImportError:
        return {"ativo": False,
                "motivo": "Pacote 'anthropic' não instalado no servidor."}

    mensagens = [
        {"role": "user" if h["autor"] == "kalebe" else "assistant", "content": h["texto"]}
        for h in historico
    ]
    if not mensagens or mensagens[-1]["role"] != "user":
        return {"ativo": False, "motivo": "Sem mensagem nova pra responder."}

    try:
        client = anthropic.Anthropic()
        resposta = client.messages.create(
            model=MODELO,
            max_tokens=3000,
            system=_SISTEMA_CHAT,
            messages=mensagens,
        )
        if getattr(resposta, "stop_reason", None) == "refusal":
            return {"ativo": True, "resposta": "A IA recusou responder isso."}
        texto = "".join(b.text for b in resposta.content if getattr(b, "type", None) == "text")
        return {"ativo": True, "resposta": texto.strip() or "A IA não retornou texto."}
    except Exception as exc:
        log.exception("Falha ao conversar com a IA no diagnóstico")
        return {"ativo": False, "motivo": f"Falha ao chamar a IA: {str(exc)[:200]}"}
