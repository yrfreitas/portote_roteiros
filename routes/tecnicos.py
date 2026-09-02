import secrets
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from database import (bump_revisao, db_conn, execute, fetch_all, fetch_one,
                      insert_returning_id, sql)
from extensions import limiter
from services.geo import geocode_cep, geocode_endereco_livre
from services.otimizador import haversine

tecnicos_bp = Blueprint("tecnicos", __name__)

CORES_PADRAO = [
    "#1a6fd4", "#e05c2a", "#2aa05c", "#9b3db8",
    "#d4a01a", "#2aaab8", "#d41a5c", "#5c7ad4",
]

CAPACIDADE_IDEAL = 8

# ─── Régua única de encaixe ──────────────────────────────────────────────
# Existia SCORE_MINIMO_BOM = 30 aqui e outros dois cortes (100 e 50) no
# _encaixeInfo do app.js. Um CEP com score 35 saía marcado como "Melhor
# encaixe" pelo backend e como "Não recomendado" pelo badge, no MESMO card.
# Agora o corte mora num lugar só e a tela apenas exibe o que o servidor
# decidiu — não há como as duas versões divergirem de novo.
ENCAIXA_BEM = 100      # mesma zona e perto de pontos que já existem
ENCAIXA_RAZOAVEL = 50  # mesma região, mas desvia a rota


# Teto de distância por classificação. Existe porque o score sozinho engana:
# zona_bonus é 100 * (pontos na mesma zona / total), então uma rota com UM
# ponto na zona leste ganha os 100 cheios e a distância mal arranha o
# resultado. Em produção isso classificou como "encaixa bem" uma rota cujo
# ponto mais próximo estava a 20,3 km — o que ninguém chamaria de encaixe.
#
# Zona é um retângulo grosseiro no mapa: dois endereços na "leste" podem estar
# a 25 km um do outro. Distância é a grandeza que o técnico paga em combustível
# e hora, então ela tem poder de veto sobre a nota.
#
# 8 km é o desvio que ainda cabe numa rota urbana sem refazer o dia; acima de
# 15 km é outra viagem. Se a operação mudar, é aqui que se mexe.
KM_MAXIMO_BEM = 8.0
KM_MAXIMO_RAZOAVEL = 15.0


def _classificar(pontuacao: float, dist_km=None) -> str:
    if pontuacao >= ENCAIXA_BEM and (dist_km is None or dist_km <= KM_MAXIMO_BEM):
        return "bem"
    if pontuacao >= ENCAIXA_RAZOAVEL and (dist_km is None or dist_km <= KM_MAXIMO_RAZOAVEL):
        return "razoavel"
    # Score alto mas longe demais: cai para "razoável" em vez de "fora", porque
    # a mesma zona ainda conta alguma coisa — só não é encaixe bom.
    if pontuacao >= ENCAIXA_BEM and dist_km is not None and dist_km <= KM_MAXIMO_RAZOAVEL:
        return "razoavel"
    return "fora"


def _motivos(f: dict, zona_alvo: str) -> list:
    """Frases curtas explicando de onde veio a nota.

    O score é uma soma de bônus de zona, distância, região e penalidade de
    lotação — não tem unidade nem teto, então o número sozinho não informa
    nada a quem olha. Estes motivos são o que transforma "87" em decisão.
    """
    motivos = []

    if f["vazia"]:
        motivos.append("Rota ainda sem pontos — cabe qualquer coisa")
        if f.get("mesma_zona_base"):
            motivos.append(f"A base de saída fica na zona {zona_alvo}")
        return motivos

    total = f["total_pontos"]
    na_zona = f["pontos_mesma_zona"]

    plural = "s" if total != 1 else ""
    if na_zona == 0:
        motivos.append(
            f"O único ponto não está na zona {zona_alvo}" if total == 1
            else f"Nenhum dos {total} pontos está na zona {zona_alvo}"
        )
    elif na_zona == total:
        motivos.append(
            f"O único ponto já está na zona {zona_alvo}" if total == 1
            else f"Todos os {total} pontos já estão na zona {zona_alvo}"
        )
    else:
        motivos.append(f"{na_zona} de {total} ponto{plural} na zona {zona_alvo}")

    dist = f["dist_minima"]
    if dist is not None:
        motivos.append(f"{dist:.1f} km do ponto mais próximo")
        # Diz na cara quando é a distância que está segurando a nota. Sem isso
        # o usuário vê "todos os pontos na mesma zona" e um veredito morno, e
        # não entende de onde veio a ressalva.
        if dist > KM_MAXIMO_RAZOAVEL:
            motivos.append("Longe demais — é outra viagem, não um desvio")
        elif dist > KM_MAXIMO_BEM:
            motivos.append(f"Mesma zona, mas acima dos {KM_MAXIMO_BEM:.0f} km de desvio confortável")

    if total >= CAPACIDADE_IDEAL:
        motivos.append(f"Rota já com {total} pontos — acima do ideal ({CAPACIDADE_IDEAL})")

    return motivos


def zona_sp(cep) -> str:
    digitos = "".join(c for c in str(cep or "") if c.isdigit())
    if len(digitos) < 5:
        return "outros"

    n = int(digitos[:5])

    if   1000 <= n <= 1999: return "centro"
    elif 2000 <= n <= 2999: return "norte"
    elif 3000 <= n <= 3999: return "leste"
    elif 4000 <= n <= 4999: return "sul"
    elif 5000 <= n <= 5999: return "oeste"
    elif 6000 <= n <= 6999: return "oeste"
    elif 7000 <= n <= 7999: return "norte"
    elif 8000 <= n <= 8999: return "leste"
    elif 9000 <= n <= 9999: return "sul"
    return "outros"


@tecnicos_bp.route("/tecnicos", methods=["GET"])
def listar_tecnicos():
    # Login de papel "tecnico" só enxerga o PRÓPRIO técnico — achado em
    # 2026-08-31: essa rota alimenta a sidebar inteira do painel (um card por
    # técnico) e todo select de "escolher técnico" do sistema, e nunca teve
    # esse recorte. Um login de campo via usuário/senha (não o link pessoal
    # em /tecnico/<token>) via a rota de todo mundo. Admin e recepcionista
    # continuam vendo todos — só quem é o próprio técnico é que fica preso à
    # própria linha.
    papel = session.get("papel")
    meu_tecnico_id = session.get("tecnico_id")
    if papel == "tecnico":
        if not meu_tecnico_id:
            return jsonify([])
        condicao_papel = "WHERE t.id = ?"
        params_papel = (meu_tecnico_id,)
    else:
        condicao_papel = ""
        params_papel = ()

    with db_conn() as conn:
        # A FOTO fica de fora da listagem de propósito.
        #
        # Ela é um data URI de ~30 KB por técnico e esta rota é rebaixada a
        # cada auto-refresh do painel: com dois técnicos eram 62 KB de rede a
        # cada ciclo, para uma imagem que não muda. Agora vai em rota própria,
        # com cache longo no navegador — o painel baixa uma vez por sessão.
        tecnicos = fetch_all(conn, f"""
            SELECT t.id, t.nome, t.cor, t.token, t.created_at, t.ativo,
                   CASE WHEN t.foto IS NULL THEN 0 ELSE 1 END AS tem_foto,
                   COUNT(f.id) AS total_fichas
            FROM tecnicos t
            LEFT JOIN fichas f ON f.tecnico_id = t.id
            {condicao_papel}
            GROUP BY t.id
            ORDER BY t.nome
        """, params_papel)
    return jsonify(tecnicos)


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>/foto", methods=["GET"])
def obter_foto(tecnico_id):
    """A foto, separada da listagem. Cache longo: imagem de perfil muda uma
    vez por ano, e sem cache o painel rebaixaria 30 KB a cada ciclo."""
    from flask import Response

    with db_conn() as conn:
        linha = fetch_one(conn, "SELECT foto FROM tecnicos WHERE id = ?", (tecnico_id,))

    if not linha or not linha.get("foto"):
        return jsonify({"erro": "Sem foto"}), 404

    resp = jsonify({"foto": linha["foto"]})
    # 1 hora no navegador. Trocar a foto recarrega o painel, então o usuário
    # vê a nova na hora; quem não trocou não paga a rede de novo.
    resp.headers["Cache-Control"] = "private, max-age=3600"
    return resp


@tecnicos_bp.route("/tecnicos", methods=["POST"])
def criar_tecnico():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()

    if not nome:
        return jsonify({"erro": "Nome é obrigatório"}), 400
    if len(nome) > 80:
        return jsonify({"erro": "Nome muito longo (máx. 80 caracteres)"}), 400

    with db_conn(commit=True) as conn:
        existente = fetch_one(
            conn, "SELECT id FROM tecnicos WHERE LOWER(nome) = LOWER(?)", (nome,)
        )
        if existente:
            return jsonify({"erro": f'Já existe um técnico chamado "{nome}"'}), 409

        total = fetch_one(conn, "SELECT COUNT(*) AS total FROM tecnicos")["total"]
        cor = (data.get("cor") or CORES_PADRAO[total % len(CORES_PADRAO)])
        token = secrets.token_urlsafe(24)

        tecnico_id = insert_returning_id(
            conn, "INSERT INTO tecnicos (nome, cor, token) VALUES (?, ?, ?)",
            (nome, cor, token)
        )

    return jsonify({"id": tecnico_id, "nome": nome, "cor": cor, "token": token}), 201


# Teto do que cabe no banco por foto. O navegador já reduz para 256x256 JPEG
# antes de enviar (ver app.js), o que dá ~20-40 KB; 300 KB é folga larga para
# aparelho que gere uma imagem mais pesada, sem virar porta para alguém
# despejar arquivo grande no Postgres.
FOTO_MAXIMA_BYTES = 300 * 1024
FOTO_PREFIXOS = ("data:image/jpeg;base64,", "data:image/png;base64,",
                 "data:image/webp;base64,")


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>/foto", methods=["PUT"])
def foto_tecnico(tecnico_id):
    """Grava a foto de perfil como data URI no próprio banco.

    POR QUE NO BANCO E NÃO EM ARQUIVO: o disco do Railway é efêmero — some a
    cada deploy. Foto salva em pasta desapareceria sem aviso na próxima
    atualização do sistema, e ninguém ligaria uma coisa à outra. No Postgres
    ela sobrevive a deploy, e o backup do banco já a leva junto.

    Enviar string vazia REMOVE a foto (o botão "remover" da tela usa isso).
    """
    data = request.get_json(silent=True) or {}
    foto = (data.get("foto") or "").strip()

    if foto:
        if not foto.startswith(FOTO_PREFIXOS):
            return jsonify({"erro": "Formato inválido. Envie JPEG, PNG ou WebP."}), 400
        if len(foto) > FOTO_MAXIMA_BYTES:
            return jsonify({"erro": "Imagem muito grande. Escolha outra foto."}), 413

    with db_conn(commit=True) as conn:
        alterados = execute(conn, "UPDATE tecnicos SET foto = ? WHERE id = ?",
                            (foto or None, tecnico_id))

    if not alterados:
        return jsonify({"erro": "Técnico não encontrado"}), 404
    return jsonify({"mensagem": "Foto atualizada" if foto else "Foto removida"})


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>/sos-resolver", methods=["PUT"])
def sos_resolver_admin(tecnico_id):
    """Escritório encerra o SOS pelo painel (pedido de 2026-09-02) — quem não
    tem o link do técnico em mãos ainda precisa poder desligar o alerta."""
    with db_conn(commit=True) as conn:
        afetadas = execute(conn, sql(
            "UPDATE tecnico_status SET sos_ativo = ? WHERE tecnico_id = ?"),
            (False, tecnico_id))
    if not afetadas:
        return jsonify({"erro": "Técnico não encontrado"}), 404
    return jsonify({"mensagem": "SOS encerrado"})


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>", methods=["DELETE"])
def deletar_tecnico(tecnico_id):
    """Desativa em vez de apagar quando já tem ficha ligada — mesmo motivo do
    setores.py: apagar de verdade levaria junto o histórico de atendimentos
    concluídos (e já faturados) daquele técnico, que `fichas.tecnico_id` tem
    ON DELETE CASCADE. Só apaga quem nunca teve ficha nenhuma."""
    with db_conn(commit=True) as conn:
        tecnico = fetch_one(conn, "SELECT * FROM tecnicos WHERE id = ?", (tecnico_id,))
        if not tecnico:
            return jsonify({"erro": "Técnico não encontrado"}), 404

        usos = fetch_one(
            conn, "SELECT COUNT(*) AS total FROM fichas WHERE tecnico_id = ?",
            (tecnico_id,)
        )["total"]

        if usos:
            execute(conn, "UPDATE tecnicos SET ativo = ? WHERE id = ?", (False, tecnico_id))
            return jsonify({
                "mensagem": f'Técnico "{tecnico["nome"]}" desativado '
                            f"({usos} ficha(s) mantida(s) no histórico)",
                "desativado": True,
            })

        execute(conn, "DELETE FROM tecnicos WHERE id = ?", (tecnico_id,))

    return jsonify({"mensagem": f'Técnico "{tecnico["nome"]}" removido', "removido": True})


@tecnicos_bp.route("/verificar-cep", methods=["POST"])
@limiter.limit("30 per minute")
def verificar_cep():
    data = request.get_json(silent=True) or {}
    cep = "".join(c for c in (data.get("cep") or "") if c.isdigit())

    if len(cep) != 8:
        return jsonify({"erro": "Informe um CEP válido com 8 dígitos"}), 400

    geo = geocode_cep(cep)
    if not geo:
        return jsonify({"erro": "CEP não encontrado"}), 404

    zona_alvo = zona_sp(cep)
    sugestoes, tem_boa_opcao, lista_tecnicos = _analisar_encaixe(geo.lat, geo.lng, zona_alvo)

    return jsonify({
        "cep": cep, "endereco": geo.endereco, "zona": zona_alvo, "preciso": geo.preciso,
        # lat/lng do alvo: sem elas o mapa não tem onde cravar o marcador.
        "lat": geo.lat, "lng": geo.lng,
        "tecnicos": lista_tecnicos, "sugestoes": sugestoes, "tem_boa_opcao": tem_boa_opcao,
    })


@tecnicos_bp.route("/verificar-endereco", methods=["POST"])
@limiter.limit("30 per minute")
def verificar_endereco():
    """Mesma análise do /verificar-cep, mas a partir de um endereço
    digitado por extenso — útil quando o cliente não sabe o CEP de cabeça."""
    data = request.get_json(silent=True) or {}
    endereco_busca = (data.get("endereco") or "").strip()

    if len(endereco_busca) < 6:
        return jsonify({
            "erro": "Descreva o endereço com mais detalhes (rua, bairro, cidade)"
        }), 400

    geo = geocode_endereco_livre(endereco_busca)
    if not geo:
        return jsonify({
            "erro": "Não conseguimos localizar esse endereço. "
                    "Tente incluir bairro e cidade, ou busque pelo CEP."
        }), 404

    zona_alvo = zona_sp(geo.cep) if geo.cep else "outros"
    sugestoes, tem_boa_opcao, lista_tecnicos = _analisar_encaixe(geo.lat, geo.lng, zona_alvo)

    return jsonify({
        "cep": geo.cep, "endereco": geo.endereco, "zona": zona_alvo, "preciso": geo.preciso,
        "lat": geo.lat, "lng": geo.lng,
        "tecnicos": lista_tecnicos, "sugestoes": sugestoes, "tem_boa_opcao": tem_boa_opcao,
    })


def _analisar_encaixe(lat_alvo: float, lng_alvo: float, zona_alvo: str):
    """Núcleo do "isso encaixa em qual rota": recebe só coordenadas +
    zona, então serve tanto pra busca por CEP quanto por endereço livre —
    as duas rotas HTTP acima só resolvem como chegar em lat/lng/zona."""
    # Só encaixa em rota que ainda vai acontecer.
    #
    # A verificação listava TODAS as fichas — inclusive as já concluídas e as
    # de dias que já passaram. O Kalebe reclamou disso em 2026-08-20 ("aparecem
    # uns dias que não tem mais"): não faz sentido oferecer encaixe numa rota
    # que já foi feita ou num dia que ficou para trás.
    #
    # Duas condições, e as duas importam:
    # - status <> 'concluida': rota fechada não recebe ponto novo (mexeria em
    #   número de dia já entregue);
    # - data_referencia vazia OU >= hoje: ficha antiga com data no passado sai;
    #   ficha sem data fica (é modelo recorrente, ainda não agendado).
    #
    # A data de hoje vem do fuso da máquina do servidor. Como a coluna é TEXTO
    # no formato AAAA-MM-DD, a comparação de string funciona como comparação de
    # data — mesma garantia usada no resto do sistema.
    from datetime import datetime, timezone
    hoje = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

    with db_conn() as conn:
        linhas = fetch_all(conn, """
            SELECT f.id AS ficha_id, f.dia_semana, f.data_referencia,
                   f.tecnico_id, f.ponto_partida_lat, f.ponto_partida_lng,
                   f.ponto_partida_cep,
                   t.nome AS tecnico_nome, t.cor AS tecnico_cor,
                   s.lat AS s_lat, s.lng AS s_lng, s.cep AS s_cep
            FROM fichas f
            JOIN tecnicos t ON t.id = f.tecnico_id
            LEFT JOIN servicos s
                   ON s.ficha_id = f.id
                  AND s.lat IS NOT NULL AND s.lng IS NOT NULL
           WHERE f.status <> 'concluida'
             AND (f.data_referencia IS NULL
                  OR f.data_referencia = ''
                  OR f.data_referencia >= ?)
        """, (hoje,))
        lista_tecnicos = fetch_all(
            conn, "SELECT id, nome, cor FROM tecnicos ORDER BY nome"
        )

    if not linhas:
        return [], False, lista_tecnicos

    fichas = {}
    for l in linhas:
        fid = l["ficha_id"]
        if fid not in fichas:
            fichas[fid] = {
                "ficha_id":          fid,
                "dia_semana":        l["dia_semana"],
                "data_referencia":   l.get("data_referencia") or "",
                "tecnico_id":        l["tecnico_id"],
                "tecnico_nome":      l["tecnico_nome"],
                "tecnico_cor":       l["tecnico_cor"] or CORES_PADRAO[0],
                "dist_minima":       None,
                "total_pontos":      0,
                "pontos_mesma_zona": 0,
                "vazia":             True,
                "pontos":            [],
                "ponto_proximo":     None,
                "_base_lat":         l.get("ponto_partida_lat"),
                "_base_lng":         l.get("ponto_partida_lng"),
                "_base_cep":         l.get("ponto_partida_cep"),
            }

        if l.get("s_lat") is None:
            continue

        f = fichas[fid]
        f["vazia"] = False
        f["total_pontos"] += 1
        # Coordenadas vão para o mapa da tela de encaixe. Sem elas o usuário
        # via só um número e tinha que imaginar onde a rota passa.
        f["pontos"].append({"lat": l["s_lat"], "lng": l["s_lng"]})

        dist = haversine(lat_alvo, lng_alvo, l["s_lat"], l["s_lng"])
        if f["dist_minima"] is None or dist < f["dist_minima"]:
            # Guarda QUAL é o ponto mais próximo, não só a distância: o mapa
            # traça a linha do CEP consultado até ele, que é o que torna
            # "2,1 km fora da rota" uma coisa que se enxerga.
            f["ponto_proximo"] = {"lat": l["s_lat"], "lng": l["s_lng"]}
            f["dist_minima"] = dist

        if zona_sp(l.get("s_cep")) == zona_alvo:
            f["pontos_mesma_zona"] += 1

    for f in fichas.values():
        if not f["vazia"]:
            continue
        if f["_base_lat"] is not None and f["_base_lng"] is not None:
            f["dist_minima"] = haversine(
                lat_alvo, lng_alvo, f["_base_lat"], f["_base_lng"]
            )
            f["mesma_zona_base"] = zona_sp(f["_base_cep"]) == zona_alvo
            # Rota vazia não tem ponto de serviço: a referência no mapa passa
            # a ser a base de saída, que é de onde o técnico realmente parte.
            f["ponto_proximo"] = {"lat": f["_base_lat"], "lng": f["_base_lng"],
                                  "e_base": True}
        else:
            f["dist_minima"] = None
            f["mesma_zona_base"] = False

    def score(f):
        if f["dist_minima"] is None:
            return 0.0

        dist_score = max(0, 50 - f["dist_minima"])

        if f["vazia"]:
            zona_bonus = 60 if f.get("mesma_zona_base") else 0
            return zona_bonus + dist_score + 20

        total = f["total_pontos"]
        pct_mesma_zona = f["pontos_mesma_zona"] / total if total else 0
        zona_bonus   = 100 * pct_mesma_zona
        regiao_bonus = min(30, f["pontos_mesma_zona"] * 3)
        penal_lotacao = max(0, total - CAPACIDADE_IDEAL) * 15

        return zona_bonus + dist_score + regiao_bonus - penal_lotacao

    # Ordena por CLASSIFICAÇÃO primeiro, score depois. Ordenar só por score
    # deixava um card "Dá pra encaixar" (164 pontos, mas 10 km) acima de um
    # "Encaixa bem" (162 pontos, 5,5 km) — a lista contradizia os próprios
    # rótulos, que é o problema que esta tela toda veio resolver.
    _PESO = {"bem": 0, "razoavel": 1, "fora": 2}

    def ordem(f):
        pontuacao = max(0, round(score(f), 1))
        return (_PESO[_classificar(pontuacao, f["dist_minima"])], -pontuacao)

    ordenadas = sorted(fichas.values(), key=ordem)
    sugestoes = []

    for f in ordenadas[:10]:
        pontuacao = max(0, round(score(f), 1))
        sugestoes.append({
            "ficha_id":          f["ficha_id"],
            "dia_semana":        f["dia_semana"],
            "data_referencia":   f["data_referencia"],
            "tecnico_id":        f["tecnico_id"],
            "tecnico_nome":      f["tecnico_nome"],
            "tecnico_cor":       f["tecnico_cor"],
            "total_pontos":      f["total_pontos"],
            "pontos_mesma_zona": f["pontos_mesma_zona"],
            "dist_minima":       round(f["dist_minima"], 1) if f["dist_minima"] is not None else None,
            "mesma_zona":        f["pontos_mesma_zona"] > 0 or f.get("mesma_zona_base", False),
            "zona_alvo":         zona_alvo,
            "vazia":             f["vazia"],
            "score":             pontuacao,
            # Classificação e motivos saem do SERVIDOR, não da tela. Antes o
            # backend dizia "boa opção" com score >= 30 e o badge do front
            # chamava o mesmo card de "não recomendado" abaixo de 50 — o card
            # se contradizia. Com uma régua só, isso não pode mais acontecer.
            "classificacao":     _classificar(pontuacao, f["dist_minima"]),
            "motivos":           _motivos(f, zona_alvo),
            "pontos":            f["pontos"],
            "ponto_proximo":     f["ponto_proximo"],
            "lotada":            (not f["vazia"]) and f["total_pontos"] >= CAPACIDADE_IDEAL,
        })

    # "Existe alguma boa opção?", não "a primeira é boa?". Com a lista já
    # ordenada por classificação as duas perguntas dão no mesmo, mas escrito
    # assim a resposta não depende da ordenação continuar como está.
    tem_boa_opcao = any(s["classificacao"] == "bem" for s in sugestoes)

    return sugestoes, tem_boa_opcao, lista_tecnicos

# ═══ Estoque do carro ═══════════════════════════════════════════════════
#
# O técnico carrega um jogo de peças de giro na van. Isso só existia na cabeça
# dele: o escritório comprava peça que já estava rodando na rua, e o cliente
# esperava a compra chegar enquanto a peça passava na porta dele.
#
# O código é guardado em MAIÚSCULA e sem espaços nas pontas porque é por ele
# que o casamento com o pedido do técnico acontece — "aww024" e "AWW024 " têm
# de ser a mesma peça.
def _normalizar_codigo(valor: str) -> str:
    return (valor or "").strip().upper()


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>/carro", methods=["GET"])
def listar_pecas_carro(tecnico_id):
    with db_conn() as conn:
        pecas = fetch_all(conn, sql(
            "SELECT id, codigo, descricao, quantidade, atualizado_em, "
            "atualizado_por FROM peca_carro WHERE tecnico_id = ? "
            "ORDER BY codigo"), (tecnico_id,))
    return jsonify({"pecas": pecas})


@tecnicos_bp.route("/tecnicos/<int:tecnico_id>/carro", methods=["POST"])
def adicionar_peca_carro(tecnico_id):
    data = request.get_json(silent=True) or {}
    codigo = _normalizar_codigo(data.get("codigo"))[:60]
    descricao = (data.get("descricao") or "").strip()[:200]

    if not codigo:
        return jsonify({"erro": "Informe o código da peça"}), 400

    try:
        quantidade = max(1, min(999, int(data.get("quantidade") or 1)))
    except (TypeError, ValueError):
        quantidade = 1

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    quem = (session.get("usuario_nome") or "").strip()[:80]

    with db_conn(commit=True) as conn:
        if not fetch_one(conn, "SELECT id FROM tecnicos WHERE id = ?", (tecnico_id,)):
            return jsonify({"erro": "Técnico não encontrado"}), 404

        # A mesma peça no mesmo carro SOMA em vez de virar linha nova: duas
        # linhas do mesmo código seriam dois números para a mesma pergunta.
        ja = fetch_one(conn, sql(
            "SELECT id, quantidade FROM peca_carro "
            "WHERE tecnico_id = ? AND codigo = ?"), (tecnico_id, codigo))
        if ja:
            execute(conn, sql(
                "UPDATE peca_carro SET quantidade = ?, descricao = ?, "
                "atualizado_em = ?, atualizado_por = ? WHERE id = ?"),
                ((ja["quantidade"] or 0) + quantidade,
                 descricao or None, agora, quem, ja["id"]))
        else:
            execute(conn, sql(
                "INSERT INTO peca_carro (tecnico_id, codigo, descricao, "
                "quantidade, atualizado_em, atualizado_por) "
                "VALUES (?, ?, ?, ?, ?, ?)"),
                (tecnico_id, codigo, descricao, quantidade, agora, quem))
        bump_revisao(conn)

    return jsonify({"codigo": codigo, "quantidade": quantidade}), 201


@tecnicos_bp.route("/tecnicos/carro/<int:peca_id>", methods=["PUT"])
def atualizar_peca_carro(peca_id):
    """Muda a quantidade. Zero REMOVE: 'acabou' e 'nunca teve' dão no mesmo
    para quem consulta, e deixar linha com zero encheria a lista de peça que
    o técnico não tem."""
    data = request.get_json(silent=True) or {}
    try:
        quantidade = int(data.get("quantidade"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Quantidade inválida"}), 400

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    quem = (session.get("usuario_nome") or "").strip()[:80]

    with db_conn(commit=True) as conn:
        if quantidade <= 0:
            execute(conn, sql("DELETE FROM peca_carro WHERE id = ?"), (peca_id,))
        else:
            execute(conn, sql(
                "UPDATE peca_carro SET quantidade = ?, atualizado_em = ?, "
                "atualizado_por = ? WHERE id = ?"),
                (min(999, quantidade), agora, quem, peca_id))
        bump_revisao(conn)

    return jsonify({"quantidade": max(0, quantidade)})


# ─── Ponto de almoço — visível só no painel (pedido de 2026-08-29) ───────
#
# Botão mora na tela do técnico (static/tecnico.js), mas o STATUS ("quem tá
# almoçando agora", "quanto tempo já foi") e o AVISO em tempo real são só
# daqui, do painel do admin — nunca aparece pra outro técnico. Por isso as
# rotas de gravar ficam em tecnico_api.py (autenticadas pelo token de quem
# aperta o botão) e as de LER ficam aqui, atrás da sessão de admin de sempre.

@tecnicos_bp.route("/tecnicos/almoco/status", methods=["GET"])
def almoco_status_geral():
    """Quem está em almoço agora, e desde quando — pro selo ao lado do nome
    na sidebar de Roteiros."""
    with db_conn() as conn:
        tecnicos_ativos = fetch_all(conn, "SELECT id FROM tecnicos")
        status = {}
        for t in tecnicos_ativos:
            ultimo = fetch_one(conn, """
                SELECT tipo, quando FROM almoco_eventos
                 WHERE tecnico_id = ? ORDER BY id DESC LIMIT 1
            """, (t["id"],))
            if ultimo and ultimo["tipo"] == "inicio":
                status[str(t["id"])] = {"em_almoco": True, "desde": ultimo["quando"]}
    return jsonify({"status": status})


@tecnicos_bp.route("/tecnicos/almoco/eventos", methods=["GET"])
def almoco_eventos_novos():
    """Eventos (início/volta) mais recentes que `desde_id`, pro painel dar o
    aviso na hora — poll leve, mesmo espírito do /api/revisao."""
    try:
        desde_id = int(request.args.get("desde_id", 0))
    except (TypeError, ValueError):
        desde_id = 0

    with db_conn() as conn:
        eventos = fetch_all(conn, sql("""
            SELECT e.id, e.tipo, e.quando, e.duracao_min, t.nome AS tecnico_nome, t.cor AS tecnico_cor
              FROM almoco_eventos e
              JOIN tecnicos t ON t.id = e.tecnico_id
             WHERE e.id > ?
             ORDER BY e.id ASC
             LIMIT 50
        """), (desde_id,))
        ultimo_id = fetch_one(conn, "SELECT MAX(id) AS m FROM almoco_eventos")["m"] or 0

    return jsonify({"eventos": eventos, "ultimo_id": ultimo_id})
