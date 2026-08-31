"""Fotos extras — mais de uma imagem por registro (OS, item de estoque,
cotação...), além da `foto` "principal"/capa que cada um já tinha.

Tabela ÚNICA (fotos_extra: dono_tipo + dono_id) em vez de uma por dono — ver
o comentário da migração em database.py. Este módulo é o único lugar que
sabe o nome da tabela; cada blueprint (ordens_servico, estoque...) só chama
estas três funções com o próprio `dono_tipo`.
"""
from datetime import datetime, timezone

from database import execute, fetch_all, fetch_one, insert_returning_id

# Mesmo teto/prefixos do campo `foto` único (ver routes/ordens_servico.py) —
# o front já reduz a imagem antes de mandar (reduzirFotoInteira), então isto
# só recusa quem chega direto na API pulando a tela.
FOTO_MAXIMA = 900 * 1024
PREFIXOS_FOTO = ("data:image/jpeg;base64,", "data:image/png;base64,",
                 "data:image/webp;base64,")


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def listar_fotos_extra(conn, dono_tipo: str, dono_id: int) -> list:
    return fetch_all(conn, """
        SELECT id, foto, criado_em FROM fotos_extra
         WHERE dono_tipo = ? AND dono_id = ? ORDER BY id
    """, (dono_tipo, dono_id))


def adicionar_foto_extra(conn, dono_tipo: str, dono_id: int, foto: str):
    """Devolve (erro, linha). Erro vazio = deu certo."""
    if not isinstance(foto, str) or not foto.startswith(PREFIXOS_FOTO):
        return "Foto inválida.", None
    if len(foto) > FOTO_MAXIMA:
        return "Foto grande demais.", None
    novo_id = insert_returning_id(conn, """
        INSERT INTO fotos_extra (dono_tipo, dono_id, foto, criado_em)
        VALUES (?, ?, ?, ?)
    """, (dono_tipo, dono_id, foto, _agora()))
    return "", fetch_one(conn, "SELECT id, foto, criado_em FROM fotos_extra WHERE id = ?", (novo_id,))


def remover_foto_extra(conn, dono_tipo: str, foto_id: int) -> bool:
    """True se apagou. `dono_tipo` na condição evita que a rota de um dono
    apague foto de outro só adivinhando o id."""
    apagadas = execute(conn, "DELETE FROM fotos_extra WHERE id = ? AND dono_tipo = ?",
                        (foto_id, dono_tipo))
    return bool(apagadas)
