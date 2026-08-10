import json
import logging
import os

from pywebpush import WebPushException, webpush

from database import db_conn, execute, fetch_all

log = logging.getLogger("portotec")

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "")


def push_configurado() -> bool:
    return bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY and VAPID_CLAIMS_EMAIL)


def notificar_tecnico(tecnico_id: int, titulo: str, corpo: str, url: str = "/") -> None:
    """Manda push pra todas as subscriptions daquele técnico (pode ter mais
    de um aparelho). Subscription expirada/removida pelo navegador (404/410
    do provedor push) é limpa do banco na hora — silencioso, não é erro do
    usuário."""
    if not push_configurado():
        return

    with db_conn() as conn:
        subs = fetch_all(
            conn, "SELECT * FROM push_subscriptions WHERE tecnico_id = ?", (tecnico_id,)
        )

    if not subs:
        return

    payload = json.dumps({"titulo": titulo, "corpo": corpo, "url": url})

    for sub in subs:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"},
            )
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                with db_conn(commit=True) as conn:
                    execute(conn, "DELETE FROM push_subscriptions WHERE id = ?", (sub["id"],))
            else:
                log.warning("Falha ao enviar push pro técnico %s: %s", tecnico_id, e)
        except Exception:
            # Uma subscription corrompida (ex: chave inválida salva pelo
            # navegador) nunca pode derrubar a criação da ficha — só essa
            # notificação falha, as outras subscriptions seguem normalmente.
            log.exception("Falha inesperada ao enviar push pro técnico %s", tecnico_id)
