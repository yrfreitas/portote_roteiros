"""Smoke test pós-deploy (item #7 da lista de melhorias, 2026-09-28).

Até aqui, "confirmar que o deploy funcionou" era eu (Bia) rodando
`curl .../static/sw.js` e conferindo a versão na mão a cada subida --
confirma que o código NOVO chegou, mas nunca confirmou que ele FUNCIONA.
Este script faz a segunda parte: loga de verdade e bate nos endpoints que
mais importam, confirmando 200 e um formato de resposta minimamente são.

DELIBERADAMENTE só LEITURA (GET) -- nenhum POST/PUT/DELETE contra
produção. Testar o fluxo de ESCRITA completo (criar OS, agendar, concluir)
teria mais valor de verdade, mas rodar isso automaticamente contra o banco
de produção é arriscado demais pra um script sem supervisão (dado de teste
minturado com dado real). Fica documentado como próximo passo, não como
"não pensamos nisso".

Uso:
    SITEROTEIRO_URL=https://portotecroteiros.com.br \
    SMOKE_TEST_SENHA=<senha do admin-mestre> \
    python scripts/smoke_test.py [versao_esperada]

Sem SMOKE_TEST_SENHA, roda só a parte que não precisa de login (health).
Sai com código 0 se tudo passou, 1 se algo falhou -- dá pra rodar depois
de cada deploy (na mão, ou um dia numa Action/agendador) e checar o
retorno em vez de reler log.
"""
import os
import sys

import requests


def main() -> int:
    url_base = os.environ.get("SITEROTEIRO_URL", "https://portotecroteiros.com.br").rstrip("/")
    senha = os.environ.get("SMOKE_TEST_SENHA", "")
    versao_esperada = sys.argv[1] if len(sys.argv) > 1 else None

    falhas = []

    def checar(nome, condicao, detalhe=""):
        status = "OK  " if condicao else "FALHOU"
        print(f"[{status}] {nome}{' -- ' + detalhe if detalhe and not condicao else ''}")
        if not condicao:
            falhas.append(nome)

    # 1) Saúde básica -- não precisa de login, é o mínimo que já checávamos
    #    via curl. Falha aqui é fatal: nem vale tentar o resto.
    try:
        r = requests.get(f"{url_base}/api/health", timeout=15)
        dados = r.json()
        checar("GET /api/health responde 200", r.status_code == 200)
        checar("resposta tem status=ok", dados.get("status") == "ok", str(dados))
        if versao_esperada:
            checar(f"versão é {versao_esperada}", dados.get("app") == versao_esperada,
                  f"veio {dados.get('app')}")
    except Exception as exc:
        checar("GET /api/health responde 200", False, str(exc))
        print("\nServidor não respondeu -- parando aqui, o resto depende disso.")
        return 1

    if not senha:
        print("\nSMOKE_TEST_SENHA não definida -- pulando os testes que exigem login.")
        return 1 if falhas else 0

    s = requests.Session()
    r = s.post(f"{url_base}/login", data={"usuario": "", "senha": senha}, allow_redirects=False, timeout=15)
    checar("login com senha responde 302 (sucesso)", r.status_code == 302, f"veio {r.status_code}")
    if r.status_code != 302:
        print("\nLogin falhou -- parando aqui, o resto exige sessão.")
        return 1

    # 2) Endpoints de leitura que mais importam no dia a dia -- os que, se
    #    quebrarem, um técnico ou a recepção percebe na hora.
    endpoints = [
        ("/api/eu", lambda d: "papel" in d),
        ("/api/ordens-servico?status=aguardando_agendamento", lambda d: "ordens" in d),
        ("/api/estoque", lambda d: "itens" in d),
        ("/api/cotacoes", lambda d: "itens" in d),
        ("/api/tecnicos", lambda d: isinstance(d, (list, dict))),
        ("/api/diagnostico/geral", lambda d: "app" in d),
    ]
    for caminho, valida in endpoints:
        try:
            r = s.get(f"{url_base}{caminho}", timeout=20)
            ok = r.status_code == 200 and valida(r.json())
            checar(f"GET {caminho}", ok, f"status={r.status_code}")
        except Exception as exc:
            checar(f"GET {caminho}", False, str(exc))

    print(f"\n{len(falhas)} falha(s)." if falhas else "\nTudo certo.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
