import io
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from database import db_conn, fetch_all, sql

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
    # Acompanha o filtro de período da tela. Sem isso, quem estivesse olhando
    # os últimos 7 dias exportaria a planilha inteira e levaria para uma
    # reunião um número que não confere com o que viu.
    # Mesmo formato de corte do listar_fichas: espaço como separador, porque a
    # coluna é TEXT gravada com CURRENT_TIMESTAMP e a comparação é textual.
    dias = request.args.get("dias")
    filtro, params = "", ()
    if dias and str(dias).isdigit() and 1 <= int(dias) <= 3650:
        corte = datetime.now(timezone.utc) - timedelta(days=int(dias))
        filtro = "AND f.concluida_em >= ?"
        params = (corte.strftime("%Y-%m-%d %H:%M:%S"),)

    with db_conn() as conn:
        fichas = fetch_all(conn, f"""
            SELECT f.dia_semana, f.data_referencia, f.concluida_em,
                   f.distancia_total, t.nome AS tecnico_nome,
                   COUNT(s.id) AS total_servicos
            FROM fichas f
            LEFT JOIN servicos s ON s.ficha_id = f.id
            LEFT JOIN tecnicos t ON t.id = f.tecnico_id
            WHERE f.status = 'concluida' {filtro}
            GROUP BY f.id, t.nome
            ORDER BY f.concluida_em DESC
        """, params)

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


@relatorios_bp.route("/relatorios/tecnicos", methods=["GET"])
def comparativo_tecnicos():
    """Comparativo entre técnicos: carga, quilometragem e conclusão.

    Passou a fazer sentido quando a Porto Tec chegou a dois técnicos em campo
    (2026-08-17). Serve para duas perguntas concretas: quem está sobrecarregado
    e quanto cada rota custa em estrada.

    Conta TODAS as fichas, concluídas ou não — a de tendência já olha só as
    fechadas, e aqui o que interessa é a carga real de cada um agora.
    ?dias=N limita pela data de referência (padrão: tudo em aberto + 60 dias).
    """
    try:
        dias = max(1, min(365, int(request.args.get("dias", 60))))
    except (TypeError, ValueError):
        dias = 60

    corte = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT t.id, t.nome, t.cor, t.foto,
                   f.id AS ficha_id, f.status, f.distancia_total,
                   f.data_referencia,
                   COUNT(s.id) AS pontos,
                   SUM(CASE WHEN s.status = 'concluido' THEN 1 ELSE 0 END) AS concluidos
              FROM tecnicos t
              LEFT JOIN fichas f ON f.tecnico_id = t.id
              LEFT JOIN servicos s ON s.ficha_id = f.id
             GROUP BY t.id, t.nome, t.cor, t.foto, f.id, f.status,
                      f.distancia_total, f.data_referencia
             ORDER BY t.nome
        """)

    por_tecnico = {}
    for l in linhas:
        # Fichas antigas ficam de fora, mas o TÉCNICO continua aparecendo —
        # some da lista quem não existe, não quem teve um mês parado.
        data = l.get("data_referencia") or ""
        dentro = (not data) or (data >= corte)

        t = por_tecnico.setdefault(l["id"], {
            "id": l["id"], "nome": l["nome"], "cor": l.get("cor") or "#4f8dfb",
            "foto": l.get("foto"),
            "rotas": 0, "rotas_concluidas": 0, "pontos": 0,
            "concluidos": 0, "km": 0.0,
        })

        if not l.get("ficha_id") or not dentro:
            continue

        t["rotas"] += 1
        if l.get("status") == "concluida":
            t["rotas_concluidas"] += 1
        t["pontos"] += l.get("pontos") or 0
        t["concluidos"] += l.get("concluidos") or 0
        t["km"] += float(l.get("distancia_total") or 0)

    resultado = []
    for t in por_tecnico.values():
        t["km"] = round(t["km"], 1)
        # Km POR PONTO é o número que compara de verdade: quilometragem alta
        # com muitos pontos é rota cheia; alta com poucos é rota espalhada,
        # que é o que dói no combustível.
        t["km_por_ponto"] = round(t["km"] / t["pontos"], 1) if t["pontos"] else 0
        t["taxa_conclusao"] = (round(100 * t["concluidos"] / t["pontos"])
                               if t["pontos"] else 0)
        t["pendentes"] = t["pontos"] - t["concluidos"]
        resultado.append(t)

    resultado.sort(key=lambda x: -x["pontos"])

    total_pontos = sum(t["pontos"] for t in resultado) or 1
    for t in resultado:
        t["fatia"] = round(100 * t["pontos"] / total_pontos)

    return jsonify({"dias": dias, "tecnicos": resultado,
                    "total_pontos": total_pontos})


# ─── Painel de atendimentos registrados pelo técnico ────────────────────
#
# O técnico passou a dizer o que aconteceu em cada visita (resolvido, precisa
# de peça, volta depois, não atendido) e a mandar a foto da etiqueta. Sem uma
# tela que junte isso, o dado fica espalhado ponto a ponto dentro de cada
# rota — existe, mas ninguém enxerga.
#
# É aqui que "precisa de peça" vira lista de trabalho: são os atendimentos que
# dependem de alguém comprar alguma coisa para poderem terminar.
DESFECHOS_ORDEM = ["precisa_peca", "volto_depois", "nao_atendido", "resolvido"]


@relatorios_bp.route("/desfechos", methods=["GET"])
def listar_desfechos():
    """Atendimentos com desfecho registrado, com contagem por tipo.

    ?dias=N limita o período (padrão 30). ?tipo=X filtra um desfecho.
    """
    try:
        dias = max(1, min(365, int(request.args.get("dias", 30))))
    except (TypeError, ValueError):
        dias = 30

    tipo = (request.args.get("tipo") or "").strip()
    limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d 00:00:00")

    with db_conn() as conn:
        linhas = fetch_all(conn, sql("""
            SELECT d.servico_id, d.desfecho, d.motivo, d.peca,
                   d.registrado_em, d.registrado_por,
                   s.cliente, s.endereco_completo, s.tipo_aparelho, s.modelo,
                   s.numero_os, s.ficha_id,
                   f.dia_semana, f.data_referencia,
                   t.nome AS tecnico, t.cor AS tecnico_cor,
                   (SELECT COUNT(*) FROM servico_foto sf
                     WHERE sf.servico_id = d.servico_id) AS fotos
              FROM servico_desfecho d
              JOIN servicos s ON s.id = d.servico_id
              LEFT JOIN fichas f ON f.id = s.ficha_id
              LEFT JOIN tecnicos t ON t.id = f.tecnico_id
             WHERE d.registrado_em >= ?
             ORDER BY d.registrado_em DESC
        """), (limite,))

    # Contagem vem do conjunto INTEIRO do período, antes de aplicar o filtro:
    # os números do topo têm de continuar mostrando o total de cada tipo mesmo
    # quando a lista abaixo está filtrada em um deles.
    contagem = {k: 0 for k in DESFECHOS_ORDEM}
    for l in linhas:
        if l["desfecho"] in contagem:
            contagem[l["desfecho"]] += 1

    if tipo in contagem:
        linhas = [l for l in linhas if l["desfecho"] == tipo]

    return jsonify({
        "dias": dias,
        "total": sum(contagem.values()),
        "contagem": contagem,
        "atendimentos": linhas,
    })
