"""Backup automático diário do banco (item #4 da lista de melhorias,
2026-09-28) -- antes só existia GET /api/backup sob demanda (botão em
Diagnóstico); sem agendamento, não há rede de segurança nenhuma se ninguém
lembrar de clicar num dia ruim.

Guardado no próprio Postgres (mesmo padrão de foto em base64 já usado no
projeto inteiro) em vez de storage externo, que não está configurado.
Retenção de 14 dias -- backup automático é pra "recuperar de um estrago
recente", não um arquivo morto; quem quiser guardar mais tempo baixa pelo
botão manual (GET /api/backup) e guarda por fora.

Mesmo molde de services/nfe.py::iniciar_sincronizacao_em_segundo_plano:
thread daemon, uma falha num ciclo não derruba o site, o próximo ciclo
tenta de novo.
"""
import logging
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger("portotec.backup")

_INTERVALO_SEGUNDOS = 24 * 60 * 60
_RETENCAO_DIAS = 14


def _ciclo_backup_automatico() -> None:
    from database import db_conn, execute, fetch_all, sql
    from routes.relatorios import gerar_dump_banco

    try:
        conteudo = gerar_dump_banco()
        agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with db_conn(commit=True) as conn:
            execute(conn, sql(
                "INSERT INTO backups_automaticos (conteudo, tamanho, criado_em) VALUES (?, ?, ?)"),
                (conteudo, len(conteudo), agora))

            # Retenção: apaga o que passou de 14 dias -- comparação de texto
            # funciona aqui porque criado_em sempre é 'YYYY-MM-DD HH:MM:SS'
            # (ordem lexicográfica == ordem cronológica), mesmo truque usado
            # em outras datas do projeto guardadas como TEXT.
            limite = (datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S")
            antigos = fetch_all(conn, sql(
                "SELECT id FROM backups_automaticos WHERE criado_em < ?"),
                (_data_limite_retencao(),))
            for a in antigos:
                execute(conn, sql("DELETE FROM backups_automaticos WHERE id = ?"), (a["id"],))

        log.info("Backup automático gravado (%d bytes), %d antigo(s) removido(s) pela retenção",
                 len(conteudo), len(antigos))
    except Exception:
        log.exception("Falha no ciclo de backup automático")


def _data_limite_retencao() -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(days=_RETENCAO_DIAS)).strftime("%Y-%m-%d %H:%M:%S")


def iniciar_backup_automatico_em_segundo_plano() -> None:
    """Chamado UMA VEZ na subida do app (ver app.py). Primeiro backup sai já
    na subida (não espera 24h pra existir o primeiro), os seguintes a cada
    24h."""
    def loop():
        while True:
            _ciclo_backup_automatico()
            time.sleep(_INTERVALO_SEGUNDOS)

    threading.Thread(target=loop, daemon=True, name="backup-automatico").start()
