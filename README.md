# Portotec Roteiros

Sistema de gestão de uma assistência técnica autorizada em São Paulo: nasceu
como roteirização de técnicos em campo e cresceu para cobrir o ciclo
inteiro — Ordem de Serviço, orçamento, estoque, venda de balcão e
acompanhamento do cliente em tempo real.

Cada dia um técnico atende de 6 a 10 clientes espalhados pela cidade. A ordem
em que ele passa em cada um muda a quilometragem total, o tempo em trânsito e
quantos atendimentos cabem no dia. O sistema monta essa rota, acompanha a
execução em campo e fecha o ciclo administrativo depois — e, em paralelo,
sustenta o atendimento de balcão (cliente que traz o aparelho na loja) e a
venda de peças/produtos, que não passam por rota nenhuma.

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

**Ordem de Serviço, Orçamento e Chamado Técnico**
- Três documentos que compartilham o mesmo cadastro de itens/valores e a
  mesma agenda de visita, mudando só o que cada um exige e imprime
- Cliente próprio (nome, CPF, telefone, endereço), sem depender de nenhum
  sistema externo para existir
- Três origens visíveis em abas: peça chegando da Panasonic, aberta pela
  equipe com técnico agendado, e cliente de balcão (nunca passa por rota)
- Impressão com campos que a própria equipe escolhe mostrar ou ocultar,
  termos de garantia por tipo de OS, foto do produto e mais fotos por
  registro (tabela única para OS, estoque e cotação)

**Estoque e venda de balcão**
- Saldo, custo médio ponderado e mínimo com alerta são controlados pelo
  próprio site — a API do fornecedor (AgoraOS) lê estoque mas não permite
  escrever, então o saldo real mora aqui
- Entrada por leitura da nota fiscal (chave de acesso, câmera ou XML colado),
  idempotente: bipar a mesma nota duas vezes não duplica o estoque
- Sub-estoques navegáveis (ex: Panasonic → Geladeira) e venda de balcão com
  busca visual por foto, carrinho e nota de venda para impressão

**Atendimentos, peças e cotações**
- Painel de tudo que aconteceu em campo — resolvido, precisa de peça,
  reagendou, virou OS — com foto anexada pelo técnico e baixa (marcar
  "já pedi") que pode ser desfeita se o comprovante errado for anexado
- Cotação de preço da Panasonic B2B integrada à busca de código
  substituído: como o site não abre aquele portal sozinho (login por
  e-mail, sessão de navegador), um robô local do computador do
  responsável consulta o preço e o site só lê o cache, com a tela se
  atualizando sozinha enquanto o robô não responde

**Permissões e comunicação**
- Acesso por pessoa, com papel (admin/técnico/recepcionista) e permissões
  granulares por ação — quem vê o quê é auditável, não é só "logado ou não"
- Chat entre a equipe e o cliente pelo mesmo link de acompanhamento que ele
  já usa para ver o técnico chegando, sem precisar criar conta

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
trazer um ORM inteiro para um schema que já passa de setenta tabelas.

**Estoque é dono do próprio saldo, não do fornecedor.**
A API do AgoraOS (ERP da loja) lê estoque mas não deixa escrever nele — testado
exaustivamente antes de confiar. Construir saldo, custo médio e baixa aqui
dentro, e não lá, é a única forma de o número bater com o que aconteceu de
verdade.

**Ordem de Serviço não depende de nenhum sistema externo para existir.**
Cliente, equipamento e status moram no próprio site. A OS só se liga à agenda
de técnico que já existia (`servicos`/`fichas`), em vez de duplicar agenda —
mas nasce, vive e imprime mesmo se toda integração externa cair.

**Cotação de preço de fornecedor por robô local, não pelo servidor.**
O portal B2B da Panasonic exige login por e-mail com sessão de navegador —
inviável de automatizar num servidor sem interação humana. Em vez disso, um
processo separado, rodando no computador de quem tem a sessão logada,
consulta o preço e escreve num cache; o site só lê esse cache e mostra o
estado ("consultando", "sem preço disponível", ou o valor) sem nunca tentar
abrir o portal sozinho.

---

## Stack

| Camada | Escolha |
|---|---|
| Backend | Python, Flask |
| Banco | PostgreSQL (produção), SQLite (local) |
| Frontend | JavaScript sem framework, Leaflet, SortableJS |
| Integrações | Google Sheets, Web Push (VAPID), IMAP, NF-e (XML), AgoraOS (ERP da loja), Claude (análise de erro) |
| Infra | Railway, PWA com service worker |

Sem framework no frontend segue sendo decisão consciente mesmo com o sistema
tendo crescido bem além do escopo original: o estado de cada tela é local a
ela, sem necessidade real de estado compartilhado complexo entre módulos tão
diferentes (rota, estoque, venda, chat). O custo de build, dependências e
atualização de um framework ainda não se pagaria aqui — reavaliar se isso
mudar.

---

## Estrutura

```
app.py                 # bootstrap, blueprints, autenticação e permissões
database.py            # conexão, migrações idempotentes, SQLite/Postgres
routes/
  auth.py              # login por pessoa, papéis e permissões granulares
  fichas.py            # rotas do dia, otimização, conciliação
  servicos.py          # pontos de atendimento
  tecnicos.py          # técnicos e análise de encaixe por CEP
  tecnico_api.py       # API escopada pelo token do técnico
  tecnico_view.py      # tela do técnico (PWA)
  setores.py           # marcas / frentes de negócio
  clientes.py          # cadastro de cliente próprio (CPF, endereço...)
  ordens_servico.py    # OS, Orçamento e Chamado Técnico
  estoque.py           # saldo, custo médio, entrada por NF-e, sub-estoques
  vendas.py            # venda de balcão (POS simples) sobre o estoque
  substituicoes.py     # catálogo de código substituído + preço Panasonic B2B
  cotacoes.py          # fila de peças aguardando cotação de fornecedor
  pedidos.py           # compras de peça (planilha) e pedido direto na OS
  relatorios.py        # atendimentos/desfechos, exportação e métricas
  rastreio.py          # acompanhamento do técnico pelo cliente, ao vivo
  chat.py              # conversa cliente ↔ equipe pelo link de acompanhamento
services/
  otimizador.py        # Nearest Neighbor + 2-opt, Haversine
  geo.py               # geocodificação em cascata com fallback
  rota_tempo.py        # tempo de viagem real entre dois pontos
  planilha.py          # conciliação com Google Sheets
  nfe.py               # leitura dos itens da NF-e
  push.py              # notificações Web Push
  agoraos.py           # leitura do catálogo/OS do ERP da loja (AgoraOS)
  fotos_extra.py       # múltiplas fotos por registro (OS, estoque, cotação)
  ia.py                # análise de erro do Diagnóstico com Claude
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
| `AGORAOS_LOGIN`, `AGORAOS_SENHA` | Leitura do catálogo/OS do ERP da loja |
| `PANASONIC_SYNC_TOKEN` | Autentica o robô local que consulta preço de fornecedor (fora deste repositório) |

Cada integração é opcional: faltando a variável, aquele recurso fica desligado
e o resto do sistema continua funcionando.
