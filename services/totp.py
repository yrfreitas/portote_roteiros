"""TOTP (RFC 6238) sem dependência nova -- item #17 da lista de melhorias
(2026-09-28), "2FA opcional no login admin".

Implementado na mão (HMAC-SHA1 + truncamento dinâmico, igual todo app
autenticador -- Google Authenticator, Authy, etc.) em vez de instalar
`pyotp` só pra isso: é pouco código, sem superfície de dependência nova
numa parte sensível do sistema (login).

REGRA DE OURO: 2FA é OPT-IN, nunca automático. `totp_ativo` nasce falso pra
todo mundo (usuarios.totp_ativo e admin_mestre_2fa.totp_ativo, ver
database.py) -- ninguém é trancado pra fora da própria conta por uma
migração. Só passa a exigir código depois que a PRÓPRIA pessoa gera o
segredo, escaneia e confirma um código válido (ver rotas em routes/auth.py).
"""
import base64
import hashlib
import hmac
import io
import secrets
import struct
import time

import qrcode

_PASSO_SEGUNDOS = 30
_DIGITOS = 6


def gerar_secret() -> str:
    """Segredo aleatório em Base32 (formato padrão que todo app
    autenticador espera colar/escanear)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _codigo_para(secret: str, contador: int) -> str:
    chave = base64.b32decode(secret.upper() + "=" * ((8 - len(secret) % 8) % 8))
    msg = struct.pack(">Q", contador)
    h = hmac.new(chave, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    parte = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(parte % (10 ** _DIGITOS)).zfill(_DIGITOS)


def verificar_codigo(secret: str, codigo: str, janela: int = 1) -> bool:
    """Aceita o código do passo ATUAL e de até `janela` passos antes/depois
    (±30s de propósito -- relógio de celular e servidor nunca batem 100%,
    sem isso o código "certo" falha por 1-2 segundos de diferença)."""
    if not secret or not codigo or not codigo.isdigit():
        return False
    contador_atual = int(time.time() // _PASSO_SEGUNDOS)
    return any(
        hmac.compare_digest(_codigo_para(secret, contador_atual + delta), codigo)
        for delta in range(-janela, janela + 1)
    )


def uri_provisionamento(secret: str, conta: str, emissor: str = "Portotec") -> str:
    from urllib.parse import quote
    return (f"otpauth://totp/{quote(emissor)}:{quote(conta)}"
            f"?secret={secret}&issuer={quote(emissor)}&digits={_DIGITOS}&period={_PASSO_SEGUNDOS}")


def qr_data_uri(uri: str) -> str:
    """PNG do QR code, pronto pra <img src="...">. `qrcode` já está nas
    dependências (usado por outra feature) -- não é lib nova."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
