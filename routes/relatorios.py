import io
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from database import db_conn, fetch_all

relatorios_bp = Blueprint("relatorios", __name__)


def _parse_dt(valor):
    if not valor:
        return None
    texto = str(valor).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None


@relatorios_bp.route("/historico/exportar", methods=["GET"])
def exportar_historico():
    with db_conn() as conn:
        fichas = fetch_all(conn, """
            SELECT f.dia_semana, f.data_referencia, f.concluida_em,
                   f.distancia_total, t.nome AS tecnico_nome,
                   COUNT(s.id) AS total_servicos
            FROM fichas f
            LEFT JOIN servicos s ON s.ficha_id = f.id
            LEFT JOIN tecnicos t ON t.id = f.tecnico_id
            WHERE f.status = 'concluida'
            GROUP BY f.id, t.nome
            ORDER BY f.concluida_em DESC
        """)

    wb = Workbook()
    ws = wb.active
    ws.title = "Histórico"

    cabecalho = ["Técnico", "Dia da semana", "Data de referência",
                 "Concluída em", "Pontos atendidos", "Km rodados"]
    ws.append(cabecalho)
    for celula in ws[1]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill(start_color="1A6FD4", end_color="1A6FD4", fill_type="solid")

    for f in fichas:
        concluida_em = _parse_dt(f.get("concluida_em"))
        ws.append([
            f.get("tecnico_nome") or "—",
            f.get("dia_semana") or "",
            f.get("data_referencia") or "",
            concluida_em.strftime("%d/%m/%Y %H:%M") if concluida_em else "",
            f.get("total_servicos") or 0,
            round(f.get("distancia_total") or 0, 1),
        ])

    for i, largura in enumerate([22, 16, 16, 18, 16, 12], start=1):
        ws.column_dimensions[chr(64 + i)].width = largura

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    nome_arquivo = f"historico-rotas-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return send_file(
        buffer, as_attachment=True, download_name=nome_arquivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@relatorios_bp.route("/metricas/tendencia", methods=["GET"])
def metricas_tendencia():
    """Agrega rotas concluídas por técnico e por semana (últimas 8 semanas).
    Feito em Python em vez de SQL de data porque SQLite e Postgres não
    compartilham as mesmas funções de data — mais portável assim."""
    with db_conn() as conn:
        fichas = fetch_all(conn, """
            SELECT f.tecnico_id, t.nome AS tecnico_nome, t.cor AS tecnico_cor,
                   f.concluida_em, f.distancia_total,
                   COUNT(s.id) AS total_servicos
            FROM fichas f
            LEFT JOIN servicos s ON s.ficha_id = f.id
            LEFT JOIN tecnicos t ON t.id = f.tecnico_id
            WHERE f.status = 'concluida' AND f.concluida_em IS NOT NULL
            GROUP BY f.id, t.nome, t.cor
        """)

    hoje = datetime.now()
    inicio_janela = hoje - timedelta(weeks=8)

    semanas = defaultdict(lambda: defaultdict(lambda: {"rotas": 0, "pontos": 0, "km": 0.0}))
    tecnicos_vistos = {}

    for f in fichas:
        dt = _parse_dt(f.get("concluida_em"))
        if not dt or dt < inicio_janela:
            continue

        semana_iso = f"{dt.isocalendar()[0]}-S{dt.isocalendar()[1]:02d}"
        tid = f["tecnico_id"]
        tecnicos_vistos[tid] = {"nome": f.get("tecnico_nome") or "—", "cor": f.get("tecnico_cor") or "#4f8dfb"}

        bucket = semanas[semana_iso][tid]
        bucket["rotas"] += 1
        bucket["pontos"] += f.get("total_servicos") or 0
        bucket["km"] += f.get("distancia_total") or 0

    semanas_ordenadas = sorted(semanas.keys())

    resultado = []
    for semana in semanas_ordenadas:
        por_tecnico = []
        for tid, dados in semanas[semana].items():
            info = tecnicos_vistos.get(tid, {"nome": "—", "cor": "#4f8dfb"})
            por_tecnico.append({
                "tecnico_id": tid,
                "tecnico_nome": info["nome"],
                "tecnico_cor": info["cor"],
                "rotas": dados["rotas"],
                "pontos": dados["pontos"],
                "km": round(dados["km"], 1),
            })
        por_tecnico.sort(key=lambda x: x["km"], reverse=True)
        resultado.append({"semana": semana, "tecnicos": por_tecnico})

    return jsonify({"semanas": resultado})
