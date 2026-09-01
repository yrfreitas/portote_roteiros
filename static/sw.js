// Service Worker do Portotec Roteiros.
//
// REGRA DE OURO: nada que venha de /api/* é cacheado, nunca. Isso é uma
// ferramenta operacional — mostrar uma rota desatualizada pro técnico
// por causa de cache é pior do que não ter cache nenhum. Só a "casca"
// do app (HTML/CSS/JS/ícones) é cacheada, pra abrir rápido e funcionar
// com internet ruim; os dados sempre vêm da rede.

// Subir esta versão a cada mudança em app.js/tecnico.js/style.css é
// obrigatório: o activate abaixo apaga todo cache com nome diferente, e é isso
// que força quem já tem o PWA instalado a receber o arquivo novo. Sem o bump,
// o navegador continua servindo o JS antigo do cache indefinidamente.
// v3 = entrada do auto-refresh (verificarRevisao em app.js e tecnico.js).
// v4 = resumo por setor com denominador correto e linha "Sem setor",
//      e rota concluída saindo da sidebar (passa a viver só no Histórico).
// v5 = setor obrigatório, classificação em lote e filtro de período.
// v6 = modo offline de leitura do técnico + fila de sincronização.
// v7 = verificador de encaixe com régua única, motivos e mapa.
// v8 = correção do mapa (setView antes das camadas).
// v9 = simulação "como o dia fica" ao clicar num dia.
// v10 = botão "A caminho" que avisa o grupo do WhatsApp.
// v11 = o Waze abre logo depois do aviso, sem voltar à tela.
// v12 = conserta o WhatsApp que não abria (o Waze atropelava).
// v13 = folha de botões no "A caminho" + selo de versão na tela.
// v14 = botão "A caminho" também no painel, na linha de cada cliente.
// v15 = rastreio ao vivo: o cliente acompanha o técnico a caminho.
// v16 = código do app passa a ser rede-primeiro (fim do JS velho no cache).
// v17 = acompanhamento por previsão de chegada (sem GPS).
// v18 = fichas na ordem da semana e destaque para a rota de hoje.
// v19 = ordem de calendário de verdade (ano, mês, dia).
// v20 = "HOJE" compara a data, não o nome do dia.
// v21 = edição de ficha (dia e data) — antes não existia.
// v22 = baixa da peça no AgoraOS ao vincular na aba Peças.
// v23 = o cliente passa a ver o técnico ANDANDO no mapa, não só a casa dele.
// v24 = GPS retoma ao abrir o app + selo visível de estado (era silêncio).
// v25 = recusa leitura de GPS imprecisa (era ela a "localização aleatória").
// v26 = o celular reporta versão e estado do GPS (fim do diagnóstico às cegas).
// v27 = rastreador nativo (Traccar Client) no lugar do GPS do navegador.
// v28 = foto de perfil do técnico + rastreador separado por técnico.
// v29 = foto aceita HEIC/iPhone + painel se atualiza sozinho.
// v30 = fichas de cada técnico podem ser recolhidas na barra lateral.
// v31 = previsão de chegada calculada da posição REAL do técnico.
// v32 = transferir rota inteira ou ponto avulso entre técnicos.
// v33 = sessão expirada leva ao login + erros do navegador viram registro.
// v34 = aba Diagnóstico, aviso de pontos sem setor e comparativo de técnicos.
// v35 = deploy de verificação (nenhuma mudança de comportamento).
// v36 = login por pessoa com papéis + chat flutuante com o cliente.
// v37 = chat da equipe + apagar conversa de cliente.
// v38 = "ponto de serviço" vira "atendimento técnico" na tela.
// v39 = fim das mensagens duplicadas + site mais rápido (pool, menos tráfego).
// v40 = corrige o 404 que travava a ficha a cada auto-refresh.
// v41 = GPS e chat param de forçar recarga do painel + chat responde na hora.
// v42 = aviso quando o cliente não está vendo o técnico no mapa.
// v43 = verificar CEP só mostra rotas em aberto e de hoje em diante.
// v44 = mover atendimento de dia sem apagar e recriar.
// v45 = reagendar (técnico + dia) num bloco só e mais bonito no modal.
// v46 = verificar CEP agrupado por técnico.
// v47 = um mapa por técnico no verificar CEP, lado a lado.
// v48 = mapas do verificar CEP realmente lado a lado (caixa alargada).
// v49 = nova aba Estoque: saldo, custo médio ponderado, entrada/saída/ajuste,
//       mínimo com alerta e histórico. Saldo controlado no site.
// v50 = estoque com marca/aparelho/modelo/preço, agrupado por aparelho
//       (estilo AgoraOS), filtros por chip e marca, e edição da ficha da peça.
// v51 = "estoque dentro do estoque": prateleiras nomeadas (Electrolux...) que
//       o admin cria e abre para adicionar peças dentro. Navegação em 2 níveis.
// v52 = conserta o clique no card de estoque (aspas do onclick quebravam o
//       HTML): não dava para abrir a prateleira nem adicionar peça dentro.
// v53 = estoque linkado: saída "para" um cliente/atendimento, entrada pela
//       nota fiscal na aba Peças (idempotente) e saldo do estoque na aba Peças.
// v54 = reagendar ganha "criar dia novo" ali mesmo: escolhe a data, cria a
//       ficha do técnico e já a seleciona como destino do atendimento.
// v55 = bipar nota fiscal: lê a chave (leitor de código de barras, câmera ou
//       XML colado), reconhece as peças e manda pro estoque (idempotente).
// v56 = conserta modal alto que não rolava (editar atendimento travava, Salvar
//       fora do alcance); + setor/marca e Nº da OS no adicionar do verificar CEP.
// v57 = bipar não dá mais 502: busca direcionada da nota (acha o e-mail exato)
//       e, se demorar/falhar, pede o XML em vez de estourar o gateway.
// v58 = conserta o select de Setor vazio no adicionar do verificar CEP
//       (preenche depois de montar o form, carregando os setores se preciso).
// v59 = bipar mais robusto: busca da nota sempre volta com status (nunca 502),
//       varredura só dos e-mails recentes, e mostra o motivo do erro na tela.
// v60 = sub-estoque dentro do estoque (Panasonic > Geladeira): navegação em
//       árvore, roll-up dos totais e exclusão que promove os filhos.
// v61 = peça só entra em sub-estoque (topo só cria sub-estoque) + botão de
//       excluir peça do estoque.
// v62 = bipar: escolher o destino navegando (clica Panasonic > Geladeira) em
//       vez de um menu suspenso; só guarda em sub-estoque.
// v63 = permissões granulares por usuário (editor em drawer no Acessos) +
//       diagnóstico editável (status/observação/excluir nos erros da tela).
// v64 = mais permissões (13 ações: split diagnóstico, técnicos, setores,
//       roteiros, atendimentos, relatórios, chat) + botão Analisar erro com IA.
// v65 = desfecho "Cotação de peça" (código+nome+foto obrigatórios) no app do
//       técnico, reagendar/volto-depois com escolha de dia, e Cotação de
//       Peças virou seção compacta dentro da aba Peças em vez de aba própria.
// v66 = corrige quebra no /api/servicos/<id>/status (painel admin) causada
//       pela mudança de assinatura de _gravar_desfecho no v65 — concluir
//       QUALQUER atendimento pelo painel estava dando erro 500. Também
//       adiciona "Cotação de peça" nas listas do painel (concluir manual,
//       selo do desfecho, cartão de Atendimentos).
// v67 = Ordens de Serviço, do zero, sem depender do AgoraOS: cadastro de
//       cliente próprio (nome, CPF, contato, endereço, indicação), abrir OS
//       (equipamento, defeito declarado, taxa de avaliação, atendente),
//       agendar visita reaproveitando fichas/técnicos, e impressão da OS.
// v68 = CEP no formulário de cliente preenche rua/bairro/cidade/estado
//       sozinho (ViaCEP), na abertura de OS.
// v69 = impressão da OS redesenhada (logo, layout mais profissional) e
//       corrigido formato de moeda/data pro padrão brasileiro.
// v70 = impressão da OS redesenhada de novo: menos "card de app" (sombra,
//       pílula colorida, emoji), mais "formulário impresso" (tabela com
//       borda, régua preta, sem cor decorativa fora da logo).
// v71 = impressão da OS, terceira passada: fonte única, mais espaço em
//       branco, cor de marca usada com moderação — estilo fatura moderna
//       em vez de card de app ou formulário de repartição.
// v72 = melhorias na aba OS: status segue o desfecho do técnico sozinho,
//       peças usadas vinculadas (dá baixa no estoque, aceita mais de uma),
//       busca por número/cliente, histórico do cliente na Nova OS, e
//       métricas (por mês, tempo médio até finalizar, indicação).
// v73 = auditoria de segurança: permissão fecha por padrão (não abre) pra
//       rota sem regra mapeada; excluir técnico com histórico desativa em
//       vez de apagar as fichas; corrida ao criar ficha durante transferência
//       de atendimento corrigida de verdade (testado com 30 threads).
// v74 = auditoria (itens "Alto"): validação de data também na criação de
//       ficha (não só na edição), e botão de adicionar atendimento não
//       trava mais em "Geocodificando..." quando falta escolher o setor.
// v75 = impressão da OS apertada pra caber numa folha A4 só (estava
//       vazando pra segunda página) — @page A4 explícito + espaçamento e
//       fontes reduzidos em cada seção, com conta somada à mão pra caber
//       nos ~271mm úteis mesmo no pior caso (observação preenchida).
// v76 = impressão da OS: meio-termo entre "vazava pra 2 folhas" (v70) e
//       "compacto demais" (v75) — devolve ~100-125px de respiro (fonte e
//       espaçamento) mantendo folga confortável dentro da A4.
// v77 = OS: editar campos pela tela, desagendar visita marcada errada,
//       filtro por período, aviso quando peça esperada chega no estoque
//       (entrada manual, por nota e bipada), exportar lista em Excel.
// v78 = auditoria local: CSS duplicado (.vcep-score-num/.vcep-motivos)
//       colidindo e quebrando o card de "por que essa pontuação?",
//       permissão do carro do técnico caindo em gerenciar_tecnicos em vez
//       de estoque_editar, e N+1 na caixa de chat que buscava a última
//       mensagem de TODA conversa antes de cortar pras 50 exibidas.
// v79 = ficha nova sem ponto de partida: transferir atendimento pra técnico
//       sem ficha aberta no dia, reagendar e agendar OS criavam ficha sem
//       NENHUM CEP de partida (obter_ou_criar_ficha não tinha fallback).
//       Agora cai no CEP da loja (08021000) quando ninguém informa um.
// v80 = transferir FICHA INTEIRA de técnico (botão "Transferir") agora
//       também sana ponto de partida ausente — antes só trocava o dono e
//       mantinha a ficha sem CEP pra sempre. Botão novo na barra de
//       técnicos ("Corrigir ponto de partida") pra aplicar o CEP padrão
//       em toda ficha antiga que nunca teve nenhum, sem precisar de SQL.
// v81 = aba Peças reescrita pra clareza: pipeline numerado explicando a
//       ordem (compra -> vincular cliente -> marcar chegada -> registrar
//       no estoque, esse último opcional), renomeado "-> estoque" pra
//       "Registrar no estoque", e nota cruzada distinguindo Peças x
//       Estoque x Cotação — eram 3 conceitos com nome parecido e nada
//       explicando a diferença entre eles.
// v83 = tela de acompanhamento do cliente (/acompanhar) e o painel deixam de
//       depender do CDN unpkg.com pro Leaflet -- agora self-hosted em
//       /static/vendor/leaflet. Clientes reportaram tela preta piscando (o
//       mapa nunca desenhava e o ciclo de atualizacao morria silencioso se o
//       CDN falhasse); tambem endureceu o loop de /acompanhar pra nao travar
//       pra sempre se o mapa der erro por qualquer outro motivo.
// v84 = aba Diagnostico/OS/Pecas/Estoque/Cotacao nascem escondidas no HTML e
//       so aparecem depois que /api/eu confirma a permissao, em vez de
//       aparecer e sumir -- era o "site pisca no login de outros usuarios"
//       reportado em 2026-08-25 (mais visivel com internet mais lenta que a
//       do admin, que carrega rapido o bastante pra nao notar o flash).
// v85 = nova aba "Agendar Clientes": peça que chegou na aba Peças ganha botão
//       pra abrir uma OS em aguardando_agendamento pro cliente (acha ou
//       cadastra pelo nome), e uma fila própria lista todo mundo pronto pra
//       marcar visita — clica, escolhe técnico e cai num dia que já existe ou
//       cria um novo, reaproveitando o agendar() da OS. Limpeza: removida
//       função morta salvarPeca/salvarPecasEmLote/usarSugestao (sem botão
//       vivo apontando pra elas, sobra de uma versão antiga da tela).
// v86 = três correções pedidas: (1) barra de abas do cabeçalho ganhou
//       rolagem própria no desktop -- sem isso, a aba "Agendar Clientes" nova
//       fazia a barra vazar por cima da data/status ("estoque sobrepondo a
//       data"); (2) aba Peças só mostra compra já paga/aprovada -- pedido
//       ainda "CRIADO" (carrinho, antes do pagamento) aparecia às vezes como
//       se fosse uma segunda peça da mesma compra; (3) campo Cliente da linha
//       da peça ganha botão "+" pra cadastrar cliente novo na hora, sem
//       depender de já ter aparecido num roteiro de técnico.
// v87 = Agendar Clientes ganha card de verdade em vez de reaproveitar a linha
//       crua da aba OS: mostra telefone (clicável, tel:), tempo esperando,
//       aparelho e defeito, com botão "Agendar visita" no card. Antes faltava
//       telefone e visualmente era só a lista da OS colada ali, sem nada que
//       ajudasse a decidir quem atender primeiro.
// v88 = quatro correções: (1) telefone vira obrigatório ao adicionar/editar
//       atendimento na ficha do roteiro; (2) peça já enviada pra Agendar
//       Clientes some da aba Peças em vez de aparecer nas duas telas ao
//       mesmo tempo; (3) o app do técnico ganha o mesmo "não redesenha
//       sozinho, só avisa" que o painel já tinha -- verificarRevisao()
//       recarregava a tela toda sozinha a cada mudança em QUALQUER lugar do
//       site, e isso é o "site pisca" que só quem usa o app do técnico via
//       (o painel já tinha sido corrigido antes); (4) corrige botão de
//       editar atendimento que travava em "Salvando..." se faltasse setor.
// v89 = duas coisas: (1) aba Peças funde compra que troca de identidade
//       quando a nota fiscal chega numa linha nova da planilha (chave por nº
//       de pedido, não só por nota) -- pega o caso que o filtro de CRIADO
//       (v86) não pegava, porque a linha antiga já costuma estar como
//       APROVADO, não CRIADO, quando a nota sai; (2) Acessos ganha "Liberar
//       tudo" por pessoa e "Marcar todas" no editor -- login novo nasce SEM
//       nenhuma permissão de propósito, e até alguém configurar cada área a
//       pessoa não consegue fazer nada, o que por fora parece o site travado.
// v90 = pedido explícito do Kalebe: todo login não-admin passa a ter o MESMO
//       acesso do admin por padrão (PADRAO_TECNICO virou "tudo", não mais
//       vazio) -- sem precisar clicar em "Liberar tudo" pessoa por pessoa.
//       Continua dando pra restringir alguém específico depois pelo editor
//       de permissões, que sempre vence sobre este padrão.
// v91 = corrige regressão: telefone virou obrigatório (v88) só no modal
//       "Adicionar Atendimento", mas a tela "Verificar CEP" tem seu PRÓPRIO
//       formulário de adicionar servico (mesma rota de backend) e ficou sem
//       campo nenhum pra telefone -- todo mundo que adicionava cliente por
//       ali levava "Informe o telefone" sem ter onde digitar. Campo
//       adicionado no formulário do Verificar CEP também.
// v92 = select de Setor vazio ao abrir "Adicionar Atendimento" logo depois
//       de criar um dia novo (ou editar/classificar em lote rápido demais):
//       a lista de setores só era lida da memória, sem esperar o
//       carregarSetores() do carregamento da página terminar. A aba
//       Verificar CEP já tinha essa proteção; agora os 3 outros lugares
//       (adicionar, editar, classificar em lote) também buscam de novo se a
//       lista ainda estiver vazia, em vez de mostrar um select sem opções.
// v93 = a tela "Verificar CEP", ao criar um dia novo, abria o modal de
//       Adicionar Atendimento preenchendo os campos na mão em vez de chamar
//       abrirModalAddServico() -- por isso nunca puxava a lista de Setor
//       (mesmo defeito relatado antes na aba Roteiros) nem limpava o
//       telefone entre uma ficha e outra. Agora reaproveita a função certa.
// v94 = Tipo de OS: 16 opções fechadas (garantia 3/6/12 meses, entrada/saída
//       da oficina, vendas, retiradas, acionamento de garantia, avaliação
//       técnica, cancelamento, pagamento/faturamento, higienização...),
//       escolhido ao abrir a OS e editável depois -- cada tipo vai imprimir
//       um termo diferente (textos ainda pendentes, hoje cai no termo
//       genérico). Impressão: logo maior (38px -> 58px) e a segunda
//       assinatura deixa de mostrar "Administrador" e passa a dizer
//       "Assinatura Empresa | Técnico Responsável".
// v95 = duas coisas na aba Peças/Roteiros: (1) Cotação de peças ganha campo
//       de foto (opcional) ao cadastrar manualmente, reaproveitando a mesma
//       validação/compressão já usada no desfecho do técnico em campo; (2)
//       barra lateral de Roteiros ganha busca por nome de cliente ou CEP,
//       pra achar em que dia/técnico alguém está sem abrir ficha por ficha.
// v145 = três coisas: (1) "Fazer Orçamento" vira só "Orçamento" (nome do
//        modelo); (2) garantia (data + prazo 3/6/12 meses) passa a valer
//        também no modelo Orçamento, não só em "saída da oficina"; (3)
//        removido o Chat da Equipe do celular do técnico — ele mostrava
//        nome e mensagem de OUTROS técnicos, e a Porto Tec quer que cada
//        um veja só a própria rota. O chat da equipe continua existindo no
//        painel (admin/recepcionista).
// v146 = corrige Verificar CEP pra quem não é admin (pedido pra liberar a
//        Gabriela): as rotas POST /api/verificar-cep e /api/verificar-endereco
//        nunca tiveram regra em permissoes.py — desde a auditoria de
//        segurança (v73), rota sem regra mapeada fecha por padrão pra
//        POST/PUT/DELETE, então mesmo com "Ver e usar o Verificador de CEP"
//        marcado, a busca sempre dava 403 "sem_regra_definida". A aba
//        aparecia, o clique em Buscar é que nunca funcionava.
// v147 = achado sério ao investigar reclamação de que o técnico Igor via
//        rota de outros técnicos: login de papel "tecnico" (usuário/senha,
//        não o link pessoal /tecnico/<token>) caía no MESMO painel do
//        admin, e GET /api/tecnicos e /api/fichas nunca tiveram recorte —
//        traziam todo mundo pra qualquer login. Corrigido nas duas rotas
//        de listagem, na de detalhe de ficha, e nas de escrita de
//        atendimento (editar/dar baixa/excluir/adicionar) — um login
//        "tecnico" só enxerga e só mexe na própria ficha agora. Isso também
//        explica o botão de almoço "sumido": ele só existe em /tecnico/
//        <token>, não nesse painel — não tem correção de código pra isso,
//        é o link certo que precisa ser usado no dia a dia.
// v148 = lote de pedidos de 2026-08-31: (1) botão de almoço também no
//        painel (login de técnico cai lá, não só em /tecnico/<token>);
//        (2) Setor vira campo obrigatório ao abrir "Ordens de Serviço" e
//        "Chamado Técnico" (mesma régua do atendimento de Roteiros); (3)
//        mais de uma foto em OS e item de estoque, além da foto principal;
//        (4) detalhe da OS mostra quantas vezes já atendemos aquele
//        cliente; (5) busca por nome do cliente na aba Atendimentos.
// v149 = achado real ao investigar "a foto não aparece no estoque": "Dar
//        entrada" (o momento natural de fotografar uma peça nova) nunca
//        teve campo de foto — só dava pra anexar depois, abrindo "Editar"
//        separado. Agora a foto pode ser anexada já na entrada, tanto pra
//        peça nova quanto pra reentrada (sem apagar a que já existia se não
//        trocar). Também shipado: etiqueta com QR Code por OS (escaneia e
//        abre a OS direto, já logado) — botão "Etiqueta (QR)" no detalhe.
// v150 = bug real confirmado com teste de pixel: print de tela (screenshot)
//        quase sempre tem canal alfa (transparência), e a compressão de
//        foto (reduzirFotoInteira, usada em TODO lugar que aceita foto)
//        convertia pra JPEG sem pintar fundo antes — área transparente
//        virava preto sólido no arquivo final. "Aceita mas não vem
//        imagem" era isso: a foto salvava, só que preta por dentro. Fotos
//        tiradas com câmera (sem transparência) nunca pegavam esse bug,
//        só print de tela — por isso funcionava pra uns e não pra outros.
// v151 = mais duas das ideias pedidas em 2026-08-31: (1) reserva de peça ao
//        aprovar orçamento — tranca a peça pra aquela OS sem tirar do saldo
//        geral, libera sozinha quando a peça é de fato baixada em "Peças
//        usadas"; (2) "Repor peça" no Estoque, cruzando saldo com o
//        consumo real dos últimos 90 dias pra saber quem vai faltar
//        primeiro. Também: card do Estoque com o NOME da peça em destaque
//        e o código como linha secundária (era o contrário).
// v152 = achado investigando "login da Nathalia não vê o roteiro": login
//        de papel "tecnico" sem vínculo com nenhum técnico cadastrado (ver
//        Acessos) cai no recorte de segurança do v147 (cada um só vê o
//        próprio técnico) e mostrava sidebar vazia com a mensagem "Nenhum
//        técnico cadastrado" — mentira nesse caso, parecia bug do sistema
//        inteiro. Mensagem agora diz a causa certa e pra onde ir resolver
//        (Diagnóstico → Acessos, vincular o login a um técnico).
const CACHE_VERSAO = 'portotec-roteiros-v156';

const ARQUIVOS_CASCA = [
  '/',
  '/static/style.css',
  '/static/app.js',
  '/static/logo.png',
  '/static/manifest.json',
  '/static/tecnico.css',
  '/static/tecnico.js',
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(CACHE_VERSAO)
      .then((cache) => cache.addAll(ARQUIVOS_CASCA))
      .then(() => self.skipWaiting())
  );
});

// Cache separado e de nome FIXO para o modo offline do técnico. Fica de fora
// da limpeza do activate de propósito: se ele fosse apagado a cada deploy, o
// técnico que abrisse o app sem sinal logo depois de uma atualização ficaria
// sem nada — justamente o cenário que este cache existe para cobrir.
const CACHE_OFFLINE = 'portotec-tecnico-offline';

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((nomes) =>
      Promise.all(
        nomes
          .filter((nome) => nome !== CACHE_VERSAO && nome !== CACHE_OFFLINE)
          .map((nome) => caches.delete(nome))
      )
    ).then(() => self.clients.claim())
  );
});

// Leitura do técnico: rede primeiro, cache só quando a rede falha.
//
// A regra "nunca cachear /api/" continua valendo para o painel e para toda
// escrita — mostrar rota desatualizada como se fosse atual é pior que não
// mostrar nada. O que muda aqui é que a resposta guardada volta MARCADA como
// offline, e a tela avisa de quando ela é. Um técnico que sabe que está vendo
// a foto das 07h40 consegue trabalhar; um que não sabe, não.
async function redeComQuedaParaCache(request) {
  try {
    const resposta = await fetch(request);
    if (resposta.ok) {
      const clone = resposta.clone();
      const corpo = await clone.blob();
      const cabecalhos = new Headers(clone.headers);
      cabecalhos.set('X-Capturado-Em', new Date().toISOString());
      const cache = await caches.open(CACHE_OFFLINE);
      await cache.put(request, new Response(corpo, { status: 200, headers: cabecalhos }));
    }
    return resposta;
  } catch (erroDeRede) {
    const cache = await caches.open(CACHE_OFFLINE);
    const cacheado = await cache.match(request);
    if (!cacheado) throw erroDeRede;

    const corpo = await cacheado.blob();
    const cabecalhos = new Headers(cacheado.headers);
    cabecalhos.set('X-Offline', '1');
    return new Response(corpo, { status: 200, headers: cabecalhos });
  }
}

self.addEventListener('fetch', (evento) => {
  const url = new URL(evento.request.url);

  // API: sempre rede, nunca cache — com uma exceção medida.
  if (url.pathname.startsWith('/api/')) {
    // Só GET das rotas do técnico entra no fallback offline. Escrita nunca:
    // devolver do cache um "concluir ponto" daria ao técnico a impressão de
    // que gravou quando nada saiu do celular. E /versao fica de fora porque
    // servir revisão velha faria o auto-refresh achar que nada mudou.
    const leituraDoTecnico = evento.request.method === 'GET'
      && url.pathname.startsWith('/api/t/')
      && !url.pathname.endsWith('/versao');

    if (leituraDoTecnico) {
      evento.respondWith(redeComQuedaParaCache(evento.request));
    } else {
      evento.respondWith(fetch(evento.request));
    }
    return;
  }

  // CDN de terceiros (Leaflet, SortableJS): URLs versionadas na própria
  // string (ex: leaflet@1.9.4) nunca mudam de conteúdo — cache-first
  // é seguro e acelera bastante o carregamento.
  if (url.origin !== self.location.origin) {
    evento.respondWith(
      caches.match(evento.request).then((cacheado) => {
        if (cacheado) return cacheado;
        return fetch(evento.request).then((resposta) => {
          const clone = resposta.clone();
          caches.open(CACHE_VERSAO).then((cache) => cache.put(evento.request, clone));
          return resposta;
        });
      })
    );
    return;
  }

  // CÓDIGO DO APP: rede primeiro, cache só como rede de segurança.
  //
  // Isto era cache-first ("stale-while-revalidate") e custou caro: o navegador
  // servia o JS velho e só buscava o novo depois, então TODA correção só
  // aparecia na segunda abertura. Em 2026-08-13 o técnico testou um botão
  // novo três vezes e continuou rodando a versão antiga — o diagnóstico
  // mostrou zero rastreios criados enquanto a API funcionava perfeitamente.
  //
  // Para HTML/JS/CSS, servir versão velha não é "um pouco desatualizado": é o
  // aplicativo errado. Estes arquivos são pequenos e a rede resolve em
  // milissegundos; o cache continua ali para quando não houver rede.
  const ehCodigoDoApp = /\.(js|css)$/.test(url.pathname) || url.pathname === '/'
    || url.pathname.startsWith('/tecnico/');

  if (ehCodigoDoApp) {
    evento.respondWith(
      fetch(evento.request).then((resposta) => {
        if (resposta.ok) {
          const clone = resposta.clone();
          caches.open(CACHE_VERSAO).then((cache) => cache.put(evento.request, clone));
        }
        return resposta;
      }).catch(() => caches.match(evento.request))
    );
    return;
  }

  // Demais estáticos (ícones, imagens, manifest): cache primeiro, atualiza em
  // segundo plano. Esses raramente mudam e não alteram comportamento.
  evento.respondWith(
    caches.match(evento.request).then((cacheado) => {
      const buscaRede = fetch(evento.request).then((resposta) => {
        if (resposta.ok) {
          const clone = resposta.clone();
          caches.open(CACHE_VERSAO).then((cache) => cache.put(evento.request, clone));
        }
        return resposta;
      }).catch(() => cacheado);

      return cacheado || buscaRede;
    })
  );
});

// Notificação de rota nova atribuída — o payload vem do backend em
// services/push.py, formato {titulo, corpo, url}.
self.addEventListener('push', (evento) => {
  let dados = { titulo: 'Portotec', corpo: 'Você tem uma atualização.', url: '/' };
  try { dados = { ...dados, ...evento.data.json() }; } catch (e) { /* payload vazio, usa default */ }

  evento.waitUntil(
    self.registration.showNotification(dados.titulo, {
      body: dados.corpo,
      icon: '/static/assets/android-chrome-192x192.png',
      badge: '/static/assets/favicon-32x32.png',
      data: { url: dados.url },
    })
  );
});

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close();
  const alvo = evento.notification.data?.url || '/';
  evento.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((janelas) => {
      for (const janela of janelas) {
        if (janela.url.includes(alvo) && 'focus' in janela) return janela.focus();
      }
      return self.clients.openWindow(alvo);
    })
  );
});
