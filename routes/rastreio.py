"""Rastreio ao vivo: o cliente acompanha o técnico a caminho.

ACOMPANHAMENTO POR PREVISÃO DE CHEGADA, não por GPS ao vivo.

A primeira versão tentou GPS: o celular do técnico mandaria a posição. Não
funciona, e a limitação é do navegador. Assim que ele sai do site para o Waze,
o sistema CONGELA a página e o watchPosition para de disparar. Página web não
recebe localização em segundo plano, nem instalada como aplicativo, nem no
Android nem no iPhone. O rastreio só reportaria enquanto ele estivesse olhando
a tela — exatamente quando não está dirigindo.

Então o acompanhamento responde a pergunta que o cliente de fato faz, que é
"a que horas ele chega?", e não "onde ele está agora". A previsão sai da
distância entre a parada anterior e o destino, com a mesma velocidade média
que o otimizador de rotas já usa. Sem GPS, sem permissão, sem depender do
técnico fazer nada além de tocar no botão ao sair.

DECISÕES DE PRIVACIDADE:
- Não guarda posição nenhuma do técnico. Some o problema inteiro de rastrear
  funcionário: o que existe é o horário de saída e uma estimativa.
- É por ATENDIMENTO, não por técnico. Começa quando ele sai para aquele
  cliente e morre quando chega.
- Expira sozinho depois de VALIDADE_HORAS mesmo se ninguém encerrar. Técnico
  que esquece o app aberto não vira rastreado o dia inteiro.
- Concluir o ponto encerra o rastreio (ver aplicar_status_servico).
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request

from database import IS_PG, db_conn, execute, fetch_all, fetch_one
from services.otimizador import MINUTOS_PARADA, VELOCIDADE_KMH, haversine

log = logging.getLogger("portotec.rastreio")

rastreio_bp = Blueprint("rastreio", __name__)

# Depois disso o link para de mostrar posição, encerrado ou não. Uma visita
# não passa de algumas horas; o que passar disso é app esquecido aberto.
VALIDADE_HORAS = 6

_ATIVO = "ativo IS TRUE" if IS_PG else "ativo = 1"


def _agora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _expirado(criado_em: str) -> bool:
    """Compara textualmente, no mesmo formato que gravamos. Ver a armadilha
    documentada em routes/fichas.py: a coluna é TEXT e o separador é ESPAÇO,
    então um isoformat() com T daria comparação errada."""
    if not criado_em:
        return True
    corte = (datetime.now(timezone.utc) - timedelta(hours=VALIDADE_HORAS))
    return str(criado_em)[:19] < corte.strftime("%Y-%m-%d %H:%M:%S")


def encerrar_por_servico(conn, servico_id: int) -> None:
    """Chamado quando o ponto é concluído: chegou, não faz mais sentido
    rastrear. Fica aqui para não espalhar regra de rastreio pelas rotas."""
    execute(conn, f"""
        UPDATE rastreios SET ativo = {'FALSE' if IS_PG else '0'}, encerrado_em = ?
         WHERE servico_id = ? AND {_ATIVO}
    """, (_agora(), servico_id))


def _prever_minutos(conn, servico_id: int) -> int:
    """Minutos até chegar, a partir da parada anterior da rota (ou da base).

    Mesma velocidade média do otimizador, para que a previsão do cliente e o
    tempo mostrado no painel não briguem entre si. Sem coordenada dá None: é
    melhor não mostrar horário nenhum do que mostrar um chutado.
    """
    destino = fetch_one(conn, """
        SELECT sv.lat, sv.lng, sv.ordem, sv.ficha_id,
               f.ponto_partida_lat, f.ponto_partida_lng
          FROM servicos sv JOIN fichas f ON f.id = sv.ficha_id
         WHERE sv.id = ?
    """, (servico_id,))
    if not destino or destino.get("lat") is None:
        return None

    # De onde ele sai: a parada imediatamente anterior na ordem da rota; se
    # este é o primeiro ponto do dia, a base.
    anterior = fetch_one(conn, """
        SELECT lat, lng FROM servicos
         WHERE ficha_id = ? AND ordem < ? AND lat IS NOT NULL
         ORDER BY ordem DESC
    """, (destino["ficha_id"], destino.get("ordem") or 0))

    origem = anterior or {"lat": destino.get("ponto_partida_lat"),
                          "lng": destino.get("ponto_partida_lng")}
    if origem.get("lat") is None:
        return None

    km = haversine(origem["lat"], origem["lng"], destino["lat"], destino["lng"])
    # Mesmo fator de 1.3 que o otimizador aplica: linha reta não é rua.
    return max(1, int(round((km * 1.3 / VELOCIDADE_KMH) * 60)))


def _tecnico_por_token(conn, token):
    if not token:
        return None
    return fetch_one(conn, "SELECT * FROM tecnicos WHERE token = ?", (token,))


@rastreio_bp.route("/t/<token>/servicos/<int:servico_id>/rastreio", methods=["POST"])
def iniciar(token, servico_id):
    """Abre (ou reaproveita) o rastreio deste atendimento."""
    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        # O ponto tem que ser de uma ficha do próprio técnico. Sem isso, quem
        # tivesse um link de técnico poderia abrir rastreio de qualquer ponto.
        servico = fetch_one(conn, """
            SELECT sv.id FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id
             WHERE sv.id = ? AND f.tecnico_id = ?
        """, (servico_id, tecnico["id"]))
        if not servico:
            return jsonify({"erro": "Ponto não encontrado nas suas rotas"}), 404

        existente = fetch_one(conn, f"""
            SELECT * FROM rastreios WHERE servico_id = ? AND {_ATIVO}
             ORDER BY id DESC
        """, (servico_id,))

        # Reaproveita o link se ainda vale: reabrir o mesmo atendimento não
        # pode invalidar o link que o cliente já recebeu.
        if existente and not _expirado(existente.get("criado_em")):
            return jsonify({"token": existente["token"], "reaproveitado": True})

        novo_token = secrets.token_urlsafe(16)
        execute(conn, """
            INSERT INTO rastreios (token, servico_id, tecnico_id, criado_em, eta_minutos)
            VALUES (?, ?, ?, ?, ?)
        """, (novo_token, servico_id, tecnico["id"], _agora(),
              _prever_minutos(conn, servico_id)))

    return jsonify({"token": novo_token, "reaproveitado": False}), 201


@rastreio_bp.route("/t/<token>/rastreio/<rastreio_token>/encerrar", methods=["POST"])
def encerrar(token, rastreio_token):
    with db_conn(commit=True) as conn:
        tecnico = _tecnico_por_token(conn, token)
        if not tecnico:
            return jsonify({"erro": "Link inválido"}), 404

        execute(conn, f"""
            UPDATE rastreios SET ativo = {'FALSE' if IS_PG else '0'}, encerrado_em = ?
             WHERE token = ? AND tecnico_id = ?
        """, (_agora(), rastreio_token, tecnico["id"]))

    return jsonify({"ok": True})


@rastreio_bp.route("/servicos/<int:servico_id>/rastreio", methods=["POST"])
def iniciar_pelo_painel(servico_id):
    """Mesma coisa, mas a partir do painel (sessão de admin).

    Existe porque quem avisa o cliente muitas vezes é o escritório, não o
    técnico. Sem isto o link de acompanhamento só nasceria pelo celular dele.
    """
    with db_conn(commit=True) as conn:
        servico = fetch_one(conn, """
            SELECT sv.id, f.tecnico_id FROM servicos sv
              JOIN fichas f ON f.id = sv.ficha_id WHERE sv.id = ?
        """, (servico_id,))
        if not servico or not servico.get("tecnico_id"):
            return jsonify({"erro": "Ponto sem técnico atribuído"}), 404

        existente = fetch_one(conn, f"""
            SELECT * FROM rastreios WHERE servico_id = ? AND {_ATIVO} ORDER BY id DESC
        """, (servico_id,))
        if existente and not _expirado(existente.get("criado_em")):
            return jsonify({"token": existente["token"], "reaproveitado": True})

        novo_token = secrets.token_urlsafe(16)
        execute(conn, """
            INSERT INTO rastreios (token, servico_id, tecnico_id, criado_em, eta_minutos)
            VALUES (?, ?, ?, ?, ?)
        """, (novo_token, servico_id, servico["tecnico_id"], _agora(),
              _prever_minutos(conn, servico_id)))

    return jsonify({"token": novo_token, "reaproveitado": False}), 201


@rastreio_bp.route("/rastreio/<rastreio_token>", methods=["GET"])
def consultar(rastreio_token):
    """Leitura PÚBLICA — é o que a página do cliente consome.

    Devolve o mínimo: primeiro nome do técnico, posição atual e o destino.
    Nada de telefone, nome completo, outros pontos da rota ou dados da ficha.
    Quem tem o link é o cliente, não alguém com direito ao resto.
    """
    with db_conn() as conn:
        r = fetch_one(conn, """
            SELECT ra.*, sv.cliente, sv.endereco_completo,
                   sv.lat AS destino_lat, sv.lng AS destino_lng, sv.status AS servico_status,
                   t.nome AS tecnico_nome
              FROM rastreios ra
              JOIN servicos sv ON sv.id = ra.servico_id
              JOIN tecnicos t  ON t.id = ra.tecnico_id
             WHERE ra.token = ?
        """, (rastreio_token,))

    if not r:
        return jsonify({"erro": "Link de acompanhamento inválido"}), 404

    encerrado = (not r.get("ativo")) or _expirado(r.get("criado_em"))
    primeiro_nome = (r.get("tecnico_nome") or "").split(" ")[0]

    saiu_em = r.get("criado_em")
    eta = r.get("eta_minutos")
    chegada = None
    if saiu_em and eta:
        try:
            base = datetime.strptime(str(saiu_em)[:19], "%Y-%m-%d %H:%M:%S")
            chegada = (base + timedelta(minutes=int(eta))).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            chegada = None

    return jsonify({
        "ativo":     not encerrado,
        "tecnico":   primeiro_nome,
        "cliente":   r.get("cliente") or "",
        "destino":   {"lat": r.get("destino_lat"), "lng": r.get("destino_lng"),
                      "endereco": r.get("endereco_completo") or ""},
        # Horários em UTC; a página converte para o fuso de quem está olhando.
        "saiu_em":   saiu_em,
        "chegada_prevista": chegada,
        "chegou":    r.get("servico_status") == "concluido",
    })


@rastreio_bp.route("/rastreios/diagnostico", methods=["GET"])
def diagnostico():
    """Rastreios recentes, para saber o que de fato aconteceu no celular.

    Fica atrás da sessão de admin (não tem prefixo público). Existe porque
    "não funcionou" no aparelho de outra pessoa é impossível de investigar sem
    ver se o rastreio nasceu e se alguma posição chegou.
    """
    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT ra.id, ra.token, ra.lat, ra.lng, ra.ativo,
                   ra.criado_em, ra.atualizado_em, ra.encerrado_em,
                   t.nome AS tecnico, sv.cliente
              FROM rastreios ra
              JOIN tecnicos t  ON t.id = ra.tecnico_id
              JOIN servicos sv ON sv.id = ra.servico_id
             ORDER BY ra.id DESC
        """)

    return jsonify({
        "total": len(linhas),
        "com_posicao": sum(1 for l in linhas if l.get("lat") is not None),
        "rastreios": [{
            "id": l["id"],
            "tecnico": l["tecnico"],
            "cliente": l["cliente"],
            "criado_em": l["criado_em"],
            # A pergunta que decide o diagnóstico: nasceu mas nunca recebeu
            # posição? Então o problema é o GPS do aparelho, não a API.
            "recebeu_posicao": l.get("lat") is not None,
            "atualizado_em": l.get("atualizado_em"),
            "ativo": bool(l.get("ativo")),
        } for l in linhas[:20]],
    })


# A página em si (/acompanhar/<token>) fica no app.py, fora deste blueprint:
# aqui tudo vive sob /api, e a página é HTML que o cliente abre no navegador.
