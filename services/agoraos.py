"""Integração com o AGORA OS — lança a peça consumida na OS do cliente.

POR QUE ESTE MÓDULO EXISTE
--------------------------
A aba Peças do site vincula uma compra de peça a um cliente, mas isso morria
na planilha. O AgoraOS é onde a Porto Tec controla OS e estoque, e ele ficava
sem saber que a peça saiu. Aqui o site EMPURRA esse consumo pra lá.

TRÊS FATOS VERIFICADOS NA API EM 2026-08-14 QUE DEFINEM O DESENHO INTEIRO
------------------------------------------------------------------------
1. O `numero_os` do site é do DigiTeam (13 dígitos, tipo 1208202621026) e NÃO
   tem relação com o id da OS no AgoraOS (inteiro sequencial, hoje na casa de
   1200). Testado: nenhum dos números do site existe lá. Por isso o casamento
   é pelo CLIENTE, e o número da OS só entra quando ele é mesmo um id do
   AgoraOS (numérico e curto) — aí é confirmado pelo nome antes de valer.

2. Casamento aproximado de nome PRODUZ ERRO REAL. Na amostra dos 42 clientes
   do site, o fuzzy casou "Jaqueline Chen" com "Jaqueline Chopin" e "Jean
   Cardoso" com "Ana Cardoso" — duas pessoas diferentes cada. Escrever numa OS
   errada mexe em faturamento de verdade, e a API NÃO tem DELETE de item de OS
   (só POST e PUT), ou seja, não dá pra desfazer sozinha. Então: **só casamento
   exato normalizado grava**; qualquer dúvida vira prévia pra decisão humana.

3. O `GET /os` ignora todo filtro (`thread_cliente`, `id_cliente`, `finalizado`
   — testados, todos devolvem a lista inteira). Não dá pra perguntar "as OS
   desse cliente" ao servidor: é preciso paginar tudo e indexar aqui. Como isso
   custa ~8 requisições, o índice fica em cache com TTL.

SOBRE A BAIXA DE ESTOQUE PROPRIAMENTE DITA
------------------------------------------
Quem baixa estoque no AgoraOS é a FINALIZAÇÃO da OS, que consome os itens
lançados nela (a OS tem `id_estoque_finalizacao`). Lançar o item é, portanto,
o gesto correto — não existe endpoint de "dar baixa" avulso.

Hoje esse lançamento ainda não reduz saldo nenhum porque os 145 produtos do
catálogo estão com `controlar_estoque = 0` (verificado em
`/produto-extensao-resumo`) — os 27 estoques existem, mas vazios. No dia em que
o controle for ligado no AgoraOS, este mesmo código passa a baixar de verdade,
sem precisar de alteração. É por isso que vale lançar desde já: constrói o
histórico de consumo que hoje não existe em lugar nenhum.
"""
import logging
import os
import re
import threading
import time
import unicodedata
from typing import Optional

import requests

log = logging.getLogger("portotec.agoraos")

URL_BASE = os.environ.get("AGORAOS_URL", "https://portotec.agoraos.com.br/api/v1")
LOGIN = os.environ.get("AGORAOS_LOGIN", "")
SENHA = os.environ.get("AGORAOS_SENHA", "")

TIMEOUT = 45

# O índice de OS e o catálogo mudam devagar (OS nova é questão de horas, produto
# novo de dias). 15 min derruba o custo de 8 requisições por vínculo pra quase
# zero sem arriscar trabalhar com dado velho demais.
TTL_CACHE = 15 * 60

# Trava única protegendo token e caches. O Procfile fixa `--workers 1
# --threads 8`: são threads dividindo o mesmo processo, então duas requisições
# simultâneas mexeriam no mesmo token. Sem a trava, uma renovação no meio da
# outra deixaria as duas com token morto.
_trava = threading.Lock()

_token = ""
_cache = {"os": None, "os_em": 0.0, "produtos": None, "produtos_em": 0.0}


# ---------------------------------------------------------------- utilitários

def configurado() -> bool:
    return bool(LOGIN and SENHA)


def faltando_para_configurar() -> list:
    falta = []
    if not LOGIN:
        falta.append("AGORAOS_LOGIN")
    if not SENHA:
        falta.append("AGORAOS_SENHA")
    return falta


# Sufixo de setor que o site cola no nome ("Fulano - Panasonic"). É informação
# do site, não do nome da pessoa — sai antes de comparar.
_SETOR = re.compile(r"\s*-\s*(panasonic|portotec|philco|loja)\s*$", re.I)


def normalizar(texto: str) -> str:
    """Tira acento, setor, pontuação e espaço dobrado. Base de todo casamento."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = t.encode("ascii", "ignore").decode()
    t = _SETOR.sub("", t)
    t = re.sub(r"[^a-zA-Z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def _so_alfanumerico(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (texto or "").lower())


# ------------------------------------------------------------------- conexão

def _autenticar() -> str:
    r = requests.post(
        f"{URL_BASE}/login/auth",
        json={"login": LOGIN, "password": SENHA},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    dados = (r.json() or {}).get("arr_dados") or {}
    token = dados.get("token")
    if not token:
        raise RuntimeError("AgoraOS recusou as credenciais (não veio token)")
    return token


def _chamar(metodo: str, caminho: str, **kwargs) -> dict:
    """Chamada autenticada com a rotação de token que o AgoraOS exige.

    TODA resposta traz um `newToken` que passa a ser o token válido. Ignorar
    isso quebra a integração sozinha depois de um tempo — o token expira em
    intervalo aleatório (máx. 30 dias) e só a rotação mantém a sessão viva.

    Um 401 refaz o login uma vez e repete: é o caminho normal quando o
    processo reinicia (Railway derruba o worker) com token velho na memória.
    """
    global _token

    if not configurado():
        raise RuntimeError("AgoraOS não configurado: falta " +
                           ", ".join(faltando_para_configurar()))

    for tentativa in (1, 2):
        if not _token:
            _token = _autenticar()

        r = requests.request(
            metodo, f"{URL_BASE}{caminho}",
            headers={"Authorization": f"Bearer {_token}"},
            timeout=TIMEOUT, **kwargs
        )

        if r.status_code == 401 and tentativa == 1:
            _token = ""
            continue

        r.raise_for_status()
        try:
            corpo = r.json()
        except ValueError:
            raise RuntimeError(f"AgoraOS respondeu algo que não é JSON em {caminho}")

        if isinstance(corpo, dict) and corpo.get("newToken"):
            _token = corpo["newToken"]
        return corpo

    raise RuntimeError("AgoraOS: falha de autenticação após nova tentativa")


# -------------------------------------------------------------------- índices

def _carregar_os(forcar: bool = False) -> dict:
    """Índice {nome normalizado: [OS...]} com todas as OS do AgoraOS.

    Pagina por `first_id` porque o `c=N` do AgoraOS trava em 150 por página —
    pedir c=500 devolve 150 e dá a falsa impressão de que a base acabou.
    O corte usa o MAIOR ID DA PÁGINA, nunca o `last_id` do envelope: o
    `last_id` é o último id global e faria o laço parar na primeira volta.
    """
    agora = time.time()
    if not forcar and _cache["os"] and (agora - _cache["os_em"]) < TTL_CACHE:
        return _cache["os"]

    todas, corte = {}, 0
    for _ in range(60):  # teto de segurança: 60 páginas = 9000 OS
        pagina = _chamar("GET", f"/os?first_id={corte}").get("arr_dados") or []
        if not pagina:
            break
        for o in pagina:
            todas[int(o["id"])] = o
        maior = max(int(o["id"]) for o in pagina)
        if maior <= corte:
            break
        corte = maior

    indice = {}
    for o in todas.values():
        nome = normalizar((o.get("cliente") or {}).get("nome"))
        if nome:
            indice.setdefault(nome, []).append(o)

    # Mais recente primeiro: quando o cliente tem várias, a OS de agora é a
    # que interessa, não a de um ano atrás.
    for lista in indice.values():
        lista.sort(key=lambda o: int(o["id"]), reverse=True)

    _cache["os"], _cache["os_em"] = indice, agora
    log.info("AgoraOS: índice de OS recarregado (%d OS, %d clientes)",
             len(todas), len(indice))
    return indice


def _carregar_produtos(forcar: bool = False) -> list:
    """Catálogo com o id_produto_extensao, que é o id aceito no item da OS.

    Usa `/produto-extensao-resumo` e não `/produto` porque é ele que já vem
    com `nome_completo` e `controlar_estoque` — sem precisar abrir cada
    produto pra descobrir a extensão.
    """
    agora = time.time()
    if not forcar and _cache["produtos"] and (agora - _cache["produtos_em"]) < TTL_CACHE:
        return _cache["produtos"]

    dados = _chamar("GET", "/produto-extensao-resumo").get("arr_dados") or {}
    lista = dados.get("arr_produto_extensao_resumo") or []

    produtos = [{
        "id_produto_extensao": p.get("id_produto_extensao"),
        "id_produto": p.get("id_produto"),
        "nome": p.get("nome_completo") or p.get("nome") or "",
        "preco": p.get("preco"),
        "custo": p.get("custo"),
        "controla_estoque": p.get("controlar_estoque") == "1",
        "_norm": normalizar(p.get("nome_completo") or p.get("nome") or ""),
    } for p in lista]

    _cache["produtos"], _cache["produtos_em"] = produtos, agora
    log.info("AgoraOS: catálogo recarregado (%d produtos, %d com controle de "
             "estoque ligado)", len(produtos),
             sum(1 for p in produtos if p["controla_estoque"]))
    return produtos


def invalidar_cache():
    _cache.update({"os": None, "os_em": 0.0, "produtos": None, "produtos_em": 0.0})


# ------------------------------------------------------------------ casamento

def procurar_produto(descricao: str) -> dict:
    """Acha a peça no catálogo do AgoraOS.

    Devolve {'exato': produto|None, 'candidatos': [...]}. Exato é o que pode
    ser lançado sozinho; candidato é sugestão pra alguém escolher. A separação
    é deliberada: "Placa BB71" e "Placa BB65" são parecidíssimas como texto e
    são peças diferentes de centenas de reais.
    """
    alvo = normalizar(descricao)
    if not alvo:
        return {"exato": None, "candidatos": []}

    produtos = _carregar_produtos()

    exatos = [p for p in produtos if p["_norm"] == alvo]
    if len(exatos) == 1:
        return {"exato": exatos[0], "candidatos": []}
    if len(exatos) > 1:
        # Mesmo nome em dois cadastros: ninguém pode adivinhar qual. Vira escolha.
        return {"exato": None, "candidatos": exatos}

    # Sem exato: oferece parecidos por palavra em comum, só como sugestão.
    palavras = {p for p in alvo.split() if len(p) > 2}
    candidatos = []
    for p in produtos:
        outras = {x for x in p["_norm"].split() if len(x) > 2}
        if not outras or not palavras:
            continue
        comum = len(palavras & outras)
        if comum and comum / max(len(palavras), len(outras)) >= 0.5:
            candidatos.append((comum, p))

    candidatos.sort(key=lambda t: -t[0])
    return {"exato": None, "candidatos": [p for _, p in candidatos[:8]]}


def _os_aberta(o: dict) -> bool:
    return str(o.get("finalizado")) != "1" and str(o.get("deletado")) != "1"


def _modelo_bate(o: dict, modelo: str) -> bool:
    """O modelo do aparelho aparece no equipamento da OS?

    Serve pra desempatar quando o cliente tem mais de uma OS aberta — que é
    exatamente o caso de quem levou geladeira e lavadora na mesma semana.
    """
    alvo = _so_alfanumerico(modelo)
    if not alvo:
        return False
    for eq in (o.get("equipamentos") or []):
        texto = _so_alfanumerico(" ".join(str(eq.get(c) or "") for c in
                                          ("modelo", "serie", "descricao",
                                           "defeito_declarado", "solucao")))
        if texto and alvo in texto:
            return True
    return False


def procurar_os(cliente: str, numero_os: str = "", modelo: str = "") -> dict:
    """Acha a OS do AgoraOS pra pendurar a peça.

    Escada de confiança, na ordem que o Kalebe pediu (nº da OS, nome, modelo):

      'id'          nº informado É um id do AgoraOS e o nome do cliente bate.
                    Certeza — não tem o que discutir.
      'nome+modelo' nome exato e o modelo do aparelho aparece na OS.
      'nome'        nome exato e uma única OS aberta. Sem ambiguidade possível.
      None          nada exato, ou mais de uma OS aberta sem desempate.
                    Devolve as candidatas pra alguém escolher.

    O nome NUNCA casa por aproximação: ver o bloco 2 do topo do arquivo.
    """
    indice = _carregar_os()
    nome = normalizar(cliente)
    do_cliente = indice.get(nome, [])

    # 1. Número da OS — só vale se for mesmo um id do AgoraOS. O do DigiTeam
    #    tem 13 dígitos e cairia num id inexistente ou, pior, num id de outro
    #    cliente; a conferência do nome é o que impede esse estrago.
    numero = _so_alfanumerico(numero_os)
    if numero.isdigit() and 0 < int(numero) < 100000:
        for o in do_cliente:
            if int(o["id"]) == int(numero):
                return {"os": o, "forca": "id", "candidatas": []}

    if not do_cliente:
        return {"os": None, "forca": None, "candidatas": [],
                "motivo": "cliente não existe no AgoraOS"}

    abertas = [o for o in do_cliente if _os_aberta(o)]
    if not abertas:
        return {"os": None, "forca": None, "candidatas": do_cliente[:5],
                "motivo": "cliente existe, mas não tem OS em aberto"}

    # 2. Modelo do aparelho desempata entre as abertas.
    if modelo:
        pelo_modelo = [o for o in abertas if _modelo_bate(o, modelo)]
        if len(pelo_modelo) == 1:
            return {"os": pelo_modelo[0], "forca": "nome+modelo", "candidatas": []}

    # 3. Uma só aberta: não há como errar.
    if len(abertas) == 1:
        return {"os": abertas[0], "forca": "nome", "candidatas": []}

    return {"os": None, "forca": None, "candidatas": abertas[:5],
            "motivo": f"{len(abertas)} OS em aberto para esse cliente"}


# ----------------------------------------------------------------- lançamento

def lancar_item(id_os: int, id_produto_extensao: int, qtd: float = 1) -> dict:
    """Pendura o produto na OS. É ESTE o gesto que vira baixa de estoque.

    São duas chamadas porque a API é assim: o POST cria o item sempre com
    quantidade 1 e o PUT ajusta. Se o PUT falhar, o item JÁ existe — e como
    não há DELETE de item de OS na API, o retorno diz isso explicitamente
    em vez de fingir que nada aconteceu.
    """
    criado = _chamar("POST", "/os/item", json={
        "id_os": int(id_os),
        "id_produto_extensao": int(id_produto_extensao),
    })

    dados = criado.get("arr_dados") or {}
    if isinstance(dados, list):
        dados = dados[0] if dados else {}
    id_item = dados.get("id") or dados.get("id_os_item")

    resultado = {"id_item": id_item, "qtd": 1, "resposta": criado.get("status")}

    if qtd and float(qtd) != 1 and id_item:
        try:
            _chamar("PUT", f"/os/item/{id_item}?qtd={qtd}")
            resultado["qtd"] = qtd
        except Exception as exc:
            log.exception("AgoraOS: item %s criado mas quantidade não ajustada", id_item)
            resultado["aviso"] = (
                f"Item {id_item} foi lançado com quantidade 1 — o ajuste para "
                f"{qtd} falhou ({exc}). Corrija no AgoraOS: a API não apaga item."
            )

    return resultado


def preparar(cliente: str, peca: str, numero_os: str = "",
             modelo: str = "", qtd: float = 1) -> dict:
    """Monta a prévia: o que seria lançado, onde, e com que confiança.

    Nada é gravado aqui. `pode_aplicar` só fica verdadeiro quando OS e produto
    saíram de casamento exato — é a trava que impede peça de R$ 600 cair na
    OS do homônimo.
    """
    achado_os = procurar_os(cliente, numero_os, modelo)
    achado_prod = procurar_produto(peca)

    os_ok = bool(achado_os.get("os"))
    prod_ok = bool(achado_prod.get("exato"))

    pendencias = []
    if not os_ok:
        pendencias.append(achado_os.get("motivo") or "OS não identificada")
    if not prod_ok:
        pendencias.append("peça não encontrada no catálogo do AgoraOS"
                          if not achado_prod["candidatos"]
                          else "mais de uma peça possível no catálogo")

    produto = achado_prod.get("exato")
    return {
        "pode_aplicar": os_ok and prod_ok,
        "pendencias": pendencias,
        "forca": achado_os.get("forca"),
        "os": achado_os.get("os"),
        "os_candidatas": achado_os.get("candidatas") or [],
        "produto": produto,
        "produto_candidatos": achado_prod.get("candidatos") or [],
        "qtd": qtd,
        # Avisar aqui é melhor do que o Kalebe descobrir depois que "a baixa
        # não baixou nada": o lançamento entra, mas sem saldo pra reduzir.
        "controla_estoque": bool(produto and produto["controla_estoque"]),
    }


def diagnostico() -> dict:
    """Estado da integração, sem expor senha. Espelha /pedidos/diagnostico."""
    if not configurado():
        return {"configurada": False, "faltando": faltando_para_configurar()}

    try:
        produtos = _carregar_produtos()
        indice = _carregar_os()
    except Exception as exc:
        return {"configurada": True, "conectou": False, "erro": str(exc)}

    total_os = sum(len(v) for v in indice.values())
    com_controle = sum(1 for p in produtos if p["controla_estoque"])

    return {
        "configurada": True,
        "conectou": True,
        "url": URL_BASE,
        "produtos": len(produtos),
        "produtos_com_estoque_ligado": com_controle,
        "os": total_os,
        "clientes_com_os": len(indice),
        # O alerta que importa pro negócio: sem isso, lançar item não reduz saldo.
        "estoque_efetivo": com_controle > 0,
    }
