# -*- coding: utf-8 -*-
import requests
B="http://127.0.0.1:5000"
s=requests.Session(); s.post(B+"/login", data={"senha":"teste123"}, allow_redirects=False, timeout=20)
s.post(B+"/api/tecnicos", json={"nome":"Pedro"}, timeout=20)
P=[t for t in s.get(B+"/api/tecnicos", timeout=20).json() if t["nome"]=="Pedro"][0]
f=s.post(B+"/api/fichas", json={"tecnico_id":P["id"],"dia_semana":"Terça-feira","data_referencia":"2026-08-18","ponto_partida_cep":"01310100"}, timeout=90).json()
fid=f.get("id") or f.get("ficha",{}).get("id")
s.post(B+f"/api/fichas/{fid}/servicos", json={"cep":"04101300","numero":"10","cliente":"Maria","tipo_aparelho":"Geladeira","setor_id":1}, timeout=90)
det=s.get(B+f"/api/fichas/{fid}", timeout=60).json()
sid=(det.get("servicos") or (det.get("ficha") or {}).get("servicos"))[-1]["id"]
rt=s.post(B+f"/api/t/{P['token']}/servicos/{sid}/rastreio", timeout=30).json()["token"]
rev=lambda: s.get(B+"/api/versao", timeout=20).json()["revisao"]

print("=== O QUE NAO PODE MAIS FAZER O PAINEL RECARREGAR ===")
for rotulo, fn in [
    ("posicao do OwnTracks", lambda: requests.post(B+f"/api/t/{P['token']}/rastreador", json={"_type":"location","lat":-23.5,"lon":-46.6,"acc":10}, timeout=20)),
    ("posicao do navegador", lambda: requests.post(B+f"/api/t/{P['token']}/rastreio/{rt}/posicao", json={"lat":-23.51,"lng":-46.61,"precisao":12}, timeout=20)),
    ("mensagem do cliente",  lambda: requests.post(B+f"/api/chat/{rt}", json={"texto":"oi"}, timeout=20)),
    ("mensagem da equipe",   lambda: s.post(B+"/api/equipe/mensagens", json={"texto":"oi equipe"}, timeout=20)),
    ("erro de navegador",    lambda: requests.post(B+"/api/erro-cliente", json={"mensagem":"teste"}, timeout=20)),
]:
    antes=rev(); fn(); depois=rev()
    print("  %-24s revisao %s -> %s  %s"%(rotulo, antes, depois, "OK (nao mexeu)" if antes==depois else "AINDA RECARREGA"))

print("\n=== O QUE AINDA DEVE recarregar (mudanca de verdade na rota) ===")
antes=rev(); s.post(B+f"/api/fichas/{fid}/servicos", json={"cep":"01310100","numero":"20","cliente":"Novo","tipo_aparelho":"Geladeira","setor_id":1}, timeout=90); depois=rev()
print("  %-24s revisao %s -> %s  %s"%("adicionar atendimento", antes, depois, "OK (recarrega)" if depois>antes else "FALHOU"))
antes=rev(); s.put(B+f"/api/servicos/{sid}/status", json={"status":"concluido"}, timeout=30); depois=rev()
print("  %-24s revisao %s -> %s  %s"%("concluir atendimento", antes, depois, "OK (recarrega)" if depois>antes else "FALHOU"))
