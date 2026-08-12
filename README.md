# Portotec Roteiros

Sistema de roteirização e gestão de atendimentos técnicos, em produção numa
assistência técnica autorizada em São Paulo.

Cada dia um técnico atende de 6 a 10 clientes espalhados pela cidade. A ordem
em que ele passa em cada um muda a quilometragem total, o tempo em trânsito e
quantos atendimentos cabem no dia. Este sistema monta essa rota, acompanha a
execução em campo e fecha o ciclo administrativo depois.

> Aplicação privada — o acesso é autenticado. Este repositório existe como
> registro técnico do projeto.

---

## O problema

Antes: a ordem das visitas era decidida no olho, os endereços iam no papel ou
no WhatsApp, e o controle de peça x atendimento era feito manualmente numa
planilha. Três consequências práticas: rota mais longa que o necessário,
atendimento esquecido sem ninguém notar, e peça comprada sem registro de em
qual cliente foi usada.

## O que o sistema faz

**Planejamento**
- Otimização de rota com Nearest Neighbor + refinamento 2-opt, sobre distância
  de Haversine
- Reordenação manual arrastando os pontos, que recalcula a distância **sem**
  re-otimizar (senão o ajuste do usuário seria desfeito na hora)
- Geocodificação em cascata: ViaCEP → Google Geocoding → Nominatim
- "Em qual rota esse CEP encaixa?" — pontua as rotas existentes por
  proximidade, zona da cidade e lotação

**Execução em campo**
- Cada técnico tem um link próprio, sem senha, que abre só a rota dele
- PWA instalável; abre pelo ícone como um app
- Conclusão por ponto e por rota
- Navegação ponto a ponto no Waze ou Google Maps
- Notificação push quando uma rota nova é atribuída

**Fechamento administrativo**
- Ao concluir a rota, os atendimentos são conciliados com a planilha de
  compras de peça: dá baixa no que casar e registra o resto à parte
- As peças são identificadas lendo o XML da NF-e recebida por e-mail — o
  documento fiscal oficial, não uma descrição aproximada
- Histórico, exportação em XLSX e métricas por técnico e por marca

---

## Decisões de projeto

Algumas escolhas que valem explicação, porque a alternativa óbvia era pior.

**A API nunca é cacheada pelo service worker.**
O app funciona offline para a "casca" (HTML, CSS, JS), mas requisições de
dados sempre vão à rede. Mostrar uma rota desatualizada para um técnico em
campo é pior do que não ter cache nenhum.

**O link do técnico não tem senha.**
O modelo de ameaça aqui é "esse link não pode vazar para um estranho", não
"precisa resistir a alguém que já tem o link". Exigir login de quem está na
rua, de moto, entre um atendimento e outro, criaria atrito diário para
proteger contra um cenário que não é o real.

**Autenticação num `before_request` central, não decorator por rota.**
Com decorator, uma rota nova criada distraidamente nasce desprotegida. Com um
ponto único de verificação e uma lista explícita de exceções, o padrão é
seguro e a exceção é que precisa ser justificada.

**Conciliação sempre mostra prévia antes de gravar.**
A planilha é da equipe e usada todo dia. Escrever nela sem mostrar o que vai
mudar é o tipo de automação que ninguém perdoa quando erra uma vez.

**Setor pertence ao ponto, não à rota.**
A mesma rota do dia pode ter uma geladeira de uma marca e uma lavadora de
outra. Classificar no nível da rota forçaria rotas de marca única ou
produziria número errado.

**Compatibilidade SQLite/Postgres em uma camada fina.**
Produção usa Postgres; o desenvolvimento local roda em SQLite descartável. Um
tradutor de placeholder e listas de migração idempotentes resolvem isso sem
trazer um ORM inteiro para um schema de seis tabelas.

---

## Stack

| Camada | Escolha |
|---|---|
| Backend | Python, Flask |
| Banco | PostgreSQL (produção), SQLite (local) |
| Frontend | JavaScript sem framework, Leaflet, SortableJS |
| Integrações | Google Sheets, Web Push (VAPID), IMAP, NF-e (XML) |
| Infra | Railway, PWA com service worker |

Sem framework no frontend é decisão consciente: a aplicação tem meia dúzia de
telas e nenhuma necessidade de estado compartilhado complexo. O custo de
build, dependências e atualização de um framework não se pagaria aqui.

---

## Estrutura

```
app.py                 # bootstrap, blueprints, autenticação central
database.py            # conexão, migrações idempotentes, SQLite/Postgres
routes/
  auth.py              # login de administrador
  fichas.py            # rotas do dia, otimização, conciliação
  servicos.py          # pontos de atendimento
  tecnicos.py          # técnicos e análise de encaixe por CEP
  tecnico_api.py       # API escopada pelo token do técnico
  setores.py           # marcas / frentes de negócio
  pedidos.py           # compras de peça
  relatorios.py        # exportação e métricas
services/
  otimizador.py        # Nearest Neighbor + 2-opt, Haversine
  geo.py               # geocodificação em cascata com fallback
  planilha.py          # conciliação com Google Sheets
  nfe.py               # leitura dos itens da NF-e
  push.py              # notificações Web Push
static/
  app.js               # painel administrativo
  tecnico.js           # visão do técnico em campo
  sw.js                # service worker
```

## Rodando localmente

```bash
pip install -r requirements.txt

# SQLite temporário; DATABASE_URL vazio evita cair no Postgres de produção
DATABASE_URL="" SQLITE_PATH=/tmp/dev.db python app.py
```

Variáveis de ambiente:

| Variável | Para quê |
|---|---|
| `DATABASE_URL` | Postgres. Vazio = SQLite local |
| `SECRET_KEY` | Sessão |
| `ADMIN_PASSWORD_HASH` | Senha do painel (hash scrypt) |
| `GOOGLE_MAPS_KEY` | Geocodificação (opcional; há fallback) |
| `PLANILHA_ID`, `GOOGLE_CREDENTIALS_JSON` | Integração com a planilha |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | Notificações push |
| `IMAP_USER`, `IMAP_PASSWORD` | Leitura das notas fiscais |

Cada integração é opcional: faltando a variável, aquele recurso fica desligado
e o resto do sistema continua funcionando.
