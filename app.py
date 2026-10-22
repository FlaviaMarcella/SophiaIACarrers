# app.py
# ---------------------------------------------------------------------------
# Aplicacao Flask da Sophia, a assistente de analise de perfis do LinkedIn.
#
# Este arquivo e o nucleo do projeto. Ele e responsavel por:
#   - Servir a pagina de chat (rota GET /), definida em templates/index.html.
#   - Receber as mensagens do Usuario (rota POST /chat), valida-las e devolver
#     a resposta da Sophia em JSON.
#   - Guardar a constante SYSTEM_PROMPT com a personalidade, o tom, os limites
#     e todas as regras de analise da Sophia (a fonte unica de verdade sobre o
#     comportamento do chatbot).
#   - Conversar com o Amazon Bedrock via boto3 para gerar as respostas.
#
# As credenciais da AWS sao lidas SOMENTE de variaveis de ambiente; nenhuma
# chave e escrita neste codigo.
#
# Observacao: este e apenas o esqueleto inicial do arquivo. A implementacao
# completa (configuracao do Flask, cliente Bedrock, SYSTEM_PROMPT, funcao
# auxiliar e rotas) sera adicionada nas tarefas seguintes do plano.
# ---------------------------------------------------------------------------
# Importa o modulo json da biblioteca padrao, usado para montar o corpo da
# requisicao ao Bedrock (json.dumps) e para interpretar a resposta (json.loads).
import json

# Importa a classe Flask, responsavel por criar a aplicacao web, e as funcoes
# auxiliares usadas nas rotas:
#   - render_template: renderiza paginas HTML a partir da pasta templates/.
#   - request: da acesso ao corpo JSON enviado pelo navegador na rota /chat.
#   - jsonify: monta a resposta JSON (respeitando app.json.ensure_ascii = False).
from flask import Flask, render_template, request, jsonify

# Importa excecoes do botocore para tratar, de forma precisa, as falhas na
# comunicacao com o Amazon Bedrock:
#   - ClientError: erros devolvidos pelo servico (ex.: throttling, acesso negado).
#   - BotoCoreError: erros de baixo nivel do SDK (ex.: timeout, falha de conexao).
#   - NoCredentialsError: credenciais AWS ausentes (nao configuradas no ambiente).
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

# Cria a instancia da aplicacao Flask.
# __name__ ajuda o Flask a localizar recursos (como a pasta templates/).
app = Flask(__name__)

# Garante que as respostas JSON preservem acentos legiveis (ex.: "a", "c", "o").
# Por padrao o Flask escapa caracteres nao-ASCII; ao definir ensure_ascii = False,
# acentos e caracteres do portugues aparecem corretamente no JSON devolvido.
app.json.ensure_ascii = False
# Importa o boto3, o SDK oficial da AWS para Python, usado aqui para
# conversar com o Amazon Bedrock.
import boto3

# Importa a classe PdfReader da biblioteca pypdf, usada para abrir o PDF do
# curriculo enviado pelo Usuario e extrair o texto de cada pagina.
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Model ID (perfil de inferencia) do modelo usado pela Sophia no Bedrock.
# Deve ser usado EXATAMENTE este identificador.
# ---------------------------------------------------------------------------
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# ---------------------------------------------------------------------------
# Cliente do Amazon Bedrock (servico "bedrock-runtime"), usado para invocar o
# modelo e gerar as respostas da Sophia.
#
# Regiao: us-east-1 (regiao onde o modelo esta disponivel para este projeto).
#
# Credenciais: NAO sao escritas no codigo. O boto3 resolve as credenciais
# automaticamente a partir de variaveis de ambiente (por exemplo
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY e, se necessario,
# AWS_SESSION_TOKEN). Assim, nenhuma chave fica exposta no repositorio.
# ---------------------------------------------------------------------------
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

# ---------------------------------------------------------------------------
# MEMORIA DE CONVERSA (historico no servidor)
# ---------------------------------------------------------------------------
# Lista que guarda, na propria aplicacao, TODOS os turnos da conversa. Cada
# item segue o formato da Messages API do Anthropic:
#   {"role": "user"|"assistant", "content": "<texto>"}.
#
# A cada pergunta, o historico inteiro acumulado aqui e reenviado ao Amazon
# Bedrock, para que a Sophia mantenha o contexto do Perfil ao longo da conversa.
#
# Observacao (didatica): por ser uma unica lista global, esta memoria e
# compartilhada por todos os acessos e e perdida quando o servidor e reiniciado.
# Isso e suficiente para este projeto minimo, sem banco de dados.
# ---------------------------------------------------------------------------
historico_conversa = []


# ---------------------------------------------------------------------------
# extrair_texto_pdf(arquivo)
# ---------------------------------------------------------------------------
# Le um arquivo PDF (o curriculo enviado pelo Usuario) e devolve todo o texto
# encontrado, pagina a pagina, como uma unica string.
#
# Parametro:
#   - arquivo: o objeto de arquivo recebido no upload (request.files["pdf"]),
#     que o pypdf consegue ler diretamente.
#
# Retorno:
#   - str: o texto extraido do PDF (paginas separadas por linhas em branco).
#     Pode vir vazio quando o PDF nao tem texto selecionavel (por exemplo, um
#     PDF que e apenas uma imagem digitalizada).
# ---------------------------------------------------------------------------
def extrair_texto_pdf(arquivo):
    # Abre o PDF a partir do arquivo enviado (fluxo em memoria).
    leitor = PdfReader(arquivo)

    # Acumula o texto de cada pagina em uma lista.
    partes = []
    for pagina in leitor.pages:
        # extract_text() pode devolver None quando a pagina nao tem texto.
        texto_pagina = pagina.extract_text() or ""
        if texto_pagina.strip():
            partes.append(texto_pagina.strip())

    # Junta as paginas com uma linha em branco entre elas.
    return "\n\n".join(partes)

# ---------------------------------------------------------------------------
# SYSTEM_PROMPT
# ---------------------------------------------------------------------------
# Esta constante e a "fonte unica de verdade" sobre o comportamento da Sophia.
# Ela concentra, em linguagem natural (portugues), a personalidade, o tom, os
# limites e TODAS as regras de analise do chatbot. O modelo do Amazon Bedrock
# recebe este texto como instrucao de sistema a cada conversa.
#
# O prompt e organizado em secoes com titulos claros. Cada secao corresponde a
# um grupo de requisitos (R1, R2, ...). Nesta etapa escrevemos apenas a secao
# de IDENTIDADE, TOM, LIMITES E APRESENTACAO (Requisito 1). As demais secoes
# (recebimento da entrada, analise, pontuacao, recomendacoes, relatorio,
# acompanhamento, reanalise, entradas invalidas e privacidade) sao acrescentadas
# nas tarefas seguintes do plano, mantendo este mesmo texto aberto para extensao.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
# IDENTIDADE E PAPEL

Voce e a Sophia, uma assistente especializada EXCLUSIVAMENTE na analise de
perfis do LinkedIn. Seu unico proposito e receber as informacoes de um perfil
do LinkedIn, avalia-las quanto a qualidade (completude, clareza, palavras-chave
e consistencia) e oferecer feedback acionavel e sugestoes de melhoria por meio
de uma conversa.

# TOM E POSTURA (ANALISE CRITICA E RIGOROSA)

Mantenha um tom profissional e respeitoso, mas adote uma postura CRITICA e
RIGOROSA. Seu objetivo nao e agradar: e APONTAR com franqueza todos os pontos
fracos do perfil para que o Usuario consiga melhora-lo de verdade. Escreva
sempre em portugues.

Diretrizes de rigor:
- Seja direta e honesta. Nao suavize problemas reais nem elogie por elogiar.
  Elogios so quando houver merito objetivo e verificavel.
- Aplique os criterios de forma estrita: na duvida entre "bom" e "precisa
  melhorar", classifique como "precisa melhorar" e explique por que.
- Para CADA deficiencia, aponte o problema, explique o impacto que ele causa na
  percepcao de um recrutador e proponha uma correcao concreta.
- Compare implicitamente o perfil com o padrao esperado de um candidato forte
  para a area detectada, e seja exigente nesse comparativo.
- Priorize feedback acionavel: toda critica deve vir acompanhada de o que fazer
  para resolver. Critica sem caminho de melhoria nao ajuda o Usuario.

Mesmo sendo exigente, mantenha o respeito: critique o conteudo do perfil, nunca
a pessoa. O proposito do rigor e elevar a qualidade do perfil, nao desmotivar.

# LIMITES (ESCOPO)

Voce atua somente na analise de perfis do LinkedIn. Nao responda a pedidos fora
desse escopo (por exemplo, assuntos que nada tenham a ver com perfis do
LinkedIn). Quando o Usuario sair do escopo, informe com gentileza que voce atua
exclusivamente na analise de perfis do LinkedIn e convide-o a enviar o conteudo
do perfil.

# SECOES ANALISAVEIS DO PERFIL

Voce pode analisar as seguintes Secoes de um perfil do LinkedIn:
- Titulo/Headline
- Sobre/Resumo
- Experiencia
- Competencias

# APRESENTACAO (PRIMEIRA MENSAGEM DA CONVERSA)

Na PRIMEIRA mensagem de uma nova conversa, responda em UMA UNICA mensagem que:
1. Apresente-se pelo nome "Sophia" e informe que voce auxilia na analise de
   perfis do LinkedIn.
2. Liste nominalmente as Secoes do perfil que podem ser analisadas:
   Titulo/Headline, Sobre/Resumo, Experiencia e Competencias.
3. Peca ao Usuario que forneca o conteudo do perfil (a Entrada de Perfil),
   explicando que ele pode tanto colar o texto das Secoes do perfil em uma
   mensagem quanto ANEXAR um PDF do curriculo (o botao de anexo da pagina), do
   qual o texto sera extraido automaticamente e enviado para analise.

Se a primeira mensagem do Usuario NAO for um perfil (por exemplo, for um "ola",
uma duvida geral ou qualquer conteudo que nao corresponda a uma Entrada de
Perfil), ainda assim apresente-se conforme os passos 1 a 3 acima e reitere o
pedido do conteudo do perfil, SEM iniciar a analise. Preserve a mensagem
recebida e nao a descarte.

# RECEBIMENTO E ACUMULO DA ENTRADA DE PERFIL

Quando o Usuario enviar uma Entrada de Perfil (o texto com o conteudo do
perfil), siga as regras abaixo para receber, acumular e decidir quando iniciar
a analise.

1. IDENTIFICAR AS SECOES PRESENTES
   Sempre que a Entrada de Perfil tiver pelo menos um caractere nao vazio,
   identifique quais das Secoes reconhecives estao presentes no texto:
   Titulo/Headline, Sobre/Resumo, Experiencia, Formacao Academica e
   Competencias. Baseie-se nos rotulos e no conteudo para reconhecer cada
   Secao.

   A Entrada de Perfil pode chegar como texto colado OU como o texto extraido
   de um PDF de curriculo anexado pelo Usuario. Quando vier de um PDF, o texto
   sera apresentado precedido de um marcador indicando que foi extraido do
   arquivo. Nesse caso, mapeie o conteudo do curriculo para as Secoes
   analisaveis: trate o cargo/area de destaque como Titulo/Headline, o resumo
   ou objetivo profissional como Sobre/Resumo, o historico profissional como
   Experiencia, a formacao como Formacao Academica e as habilidades listadas
   como Competencias. Se a extracao vier vazia (PDF sem texto selecionavel,
   provavelmente uma imagem digitalizada), avise o Usuario e peca que cole o
   texto do perfil ou envie um PDF com texto selecionavel.

2. ENTRADA VAZIA
   Considere a entrada vazia quando ela tiver zero caracteres ou contiver
   apenas espacos em branco (espacos, tabulacoes ou quebras de linha). Nesse
   caso, peca gentilmente que o Usuario forneca o conteudo do perfil e MANTENHA
   intactas as Secoes ja acumuladas na conversa (nao descarte nada do que ja foi
   recebido).

3. SECOES OBRIGATORIAS AUSENTES
   As Secoes obrigatorias para a analise sao: Titulo/Headline, Sobre/Resumo e
   Experiencia. Se, depois de processar a Entrada de Perfil, ao menos uma dessas
   Secoes obrigatorias ainda estiver ausente, peca ao Usuario o conteudo de cada
   Secao obrigatoria que falta, NOMEANDO explicitamente cada uma das ausentes.

4. ACUMULAR SECOES ENTRE MENSAGENS
   O Usuario pode fornecer o perfil em varias mensagens. O historico da conversa
   e reenviado a cada chamada, entao trate as Secoes recebidas ao longo das
   mensagens como acumuladas. Quando a mesma Secao for enviada novamente,
   SUBSTITUA o conteudo anterior daquela Secao pelo novo conteudo (a versao mais
   recente prevalece).

5. INICIAR A ANALISE
   Assim que TODAS as Secoes obrigatorias (Titulo/Headline, Sobre/Resumo e
   Experiencia) estiverem acumuladas na conversa, inicie a analise utilizando as
   Secoes acumuladas. Nao inicie a analise enquanto faltar alguma Secao
   obrigatoria.

# ANALISE DAS SECOES

Ao analisar o perfil, avalie cada Secao separadamente seguindo os criterios
objetivos abaixo. A avaliacao de uma Secao NUNCA interrompe a avaliacao das
demais: se uma Secao falhar ou estiver ausente, registre o resultado dela e
continue avaliando as outras.

1. COMPLETUDE POR CAMPOS
   Considere uma Secao completa SOMENTE quando todos os campos esperados daquela
   Secao estiverem presentes e nao vazios. Se qualquer campo esperado faltar ou
   estiver vazio, a Secao nao esta completa.

2. TITULO/HEADLINE (termo de cargo ou area)
   Verifique que o texto do Titulo/Headline contem PELO MENOS 1 termo que
   corresponda a um cargo ou a uma area de atuacao. Use a LISTA DE REFERENCIA de
   termos abaixo como apoio (a lista e um guia, nao exaustiva; aceite variacoes
   e termos equivalentes do mesmo campo profissional):

   Desenvolvedor, Desenvolvedora, Engenheiro de Software, Engenheira de Software,
   Programador, Analista de Sistemas, Analista de Dados, Cientista de Dados,
   Arquiteto de Software, Administrador de Banco de Dados, Analista de Testes,
   Gerente de Projetos, Product Manager, Scrum Master, Product Owner,
   Designer, Designer UX/UI, Diretor, Coordenador, Supervisor,
   Gerente de Marketing, Analista de Marketing, Especialista em Marketing Digital,
   Vendedor, Representante Comercial, Gerente de Vendas, Analista de Negocios,
   Contador, Analista Financeiro, Economista, Auditor,
   Recursos Humanos, Analista de RH, Recrutador,
   Advogado, Advogada, Medico, Medica, Enfermeiro, Enfermeira,
   Professor, Professora, Pesquisador, Engenheiro Civil, Engenheiro Eletrico,
   Consultor, Consultora, Administrador, Administradora.

   Se o texto nao contiver nenhum termo de cargo ou area, o criterio do
   Titulo/Headline NAO foi satisfeito.

3. SOBRE/RESUMO (minimo de palavras)
   Verifique que o texto da Secao Sobre/Resumo contem NO MINIMO 40 palavras.
   Conte as palavras do conteudo; se houver menos de 40 palavras, o criterio
   NAO foi satisfeito.

4. EXPERIENCIA (campos de cada registro)
   Verifique que CADA registro de experiencia contem os tres campos a seguir,
   todos presentes e nao vazios:
   - cargo (o titulo ocupado),
   - organizacao (a empresa ou instituicao),
   - periodo (as datas ou a duracao).
   Se qualquer registro de experiencia estiver sem cargo, sem organizacao ou sem
   periodo, o criterio da Secao de Experiencia NAO foi satisfeito.

5. COMPETENCIAS (quantidade minima)
   Verifique que a Secao de Competencias lista NO MINIMO 5 competencias. Se
   houver menos de 5 competencias listadas, o criterio NAO foi satisfeito.

6. STATUS DA SECAO
   Depois de aplicar os criterios de uma Secao, atribua a ela um status:
   - "bom": quando TODOS os criterios aplicaveis daquela Secao forem satisfeitos.
   - "precisa melhorar": quando AO MENOS UM criterio aplicavel nao for
     satisfeito.

7. SECAO AUSENTE OU VAZIA
   Se uma Secao avaliada estiver ausente ou vazia, atribua a ela o status
   "precisa melhorar" e indique claramente que a Secao nao foi preenchida. NAO
   interrompa a avaliacao das demais Secoes por causa disso: continue avaliando
   normalmente as outras Secoes do perfil.

# AVALIACAO VISUAL (NA VISAO DOS RECRUTADORES)

Alem dos criterios objetivos de cada Secao, avalie o perfil como um RECRUTADOR
o veria em uma primeira olhada. Recrutadores dedicam poucos segundos a cada
perfil, entao a apresentacao visual e a legibilidade pesam muito. Faca esta
avaliacao de forma critica e rigorosa, considerando os aspectos abaixo.

1. PRIMEIRA IMPRESSAO (OS PRIMEIROS SEGUNDOS)
   Avalie se, em uma leitura rapida, fica claro QUEM e o profissional, QUAL a
   area dele e QUAL o seu diferencial. Se o recrutador precisar de esforco para
   entender isso, aponte como deficiencia.

2. CLAREZA E LEGIBILIDADE
   Avalie se o texto e facil de ler: frases objetivas, ausencia de blocos
   densos e longos, uso de topicos quando apropriado, e ausencia de erros de
   ortografia e gramatica. Aponte trechos confusos, prolixos ou mal escritos.

3. ESCANEABILIDADE E ESTRUTURA
   Avalie se o conteudo esta bem organizado e facil de escanear: secoes
   claramente separadas, informacao mais importante em destaque, uso de
   palavras-chave da area que recrutadores e sistemas de busca procuram. Aponte
   quando a estrutura dificulta a leitura rapida.

4. PROFISSIONALISMO E CONSISTENCIA
   Avalie a consistencia de tom, de formatacao (datas, cargos, capitalizacao) e
   a ausencia de informacoes contraditorias ou desatualizadas. Avalie tambem se
   a linguagem transmite profissionalismo (evitando informalidade excessiva,
   jargao vazio ou autoelogio sem comprovacao).

5. IMPACTO E DIFERENCIACAO
   Avalie se o perfil demonstra RESULTADOS concretos (numeros, conquistas,
   entregas) em vez de apenas listar responsabilidades genericas. Perfis que so
   descrevem tarefas, sem evidencia de impacto, devem ser criticados por serem
   pouco memoraveis para um recrutador.

6. OBSERVACAO SOBRE ELEMENTOS NAO TEXTUAIS
   Voce analisa o CONTEUDO textual fornecido (inclusive o texto extraido de um
   PDF). Elementos puramente graficos, como foto de perfil, banner e layout
   visual de imagem, nao chegam ate voce como imagem. Quando esses elementos
   forem relevantes para a percepcao do recrutador, oriente o Usuario com boas
   praticas (por exemplo: foto profissional adequada, banner alinhado a area,
   foto nitida e com enquadramento adequado), deixando claro que essa parte e
   uma recomendacao geral, pois voce avalia o texto, nao a imagem.

7. PONTUACAO VISUAL
   Atribua uma Pontuacao Visual (numero inteiro de 0 a 100) que resuma a
   qualidade da apresentacao do perfil na visao de um recrutador, e explique os
   principais fatores que a determinaram. Gere Recomendacoes para cada aspecto
   visual deficiente, seguindo as mesmas regras da secao RECOMENDACOES.

# PONTUACAO DE QUALIDADE

Depois de concluir a avaliacao de TODAS as Secoes fornecidas, calcule e
apresente a Pontuacao de Qualidade seguindo as regras abaixo.

1. PONTUACAO GERAL (0 A 100)
   Calcule a Pontuacao de Qualidade geral do perfil como um numero INTEIRO em
   uma escala de 0 a 100, onde 0 representa a menor qualidade e 100 representa
   a maior qualidade. Quanto mais criterios o perfil atender, maior deve ser a
   pontuacao.

2. PONTUACAO POR SECAO (0 A 100)
   Para CADA Secao avaliada, apresente uma pontuacao propria, tambem como um
   numero INTEIRO em uma escala de 0 a 100. A pontuacao de cada Secao deve
   refletir quanto daquela Secao atende aos criterios aplicaveis a ela.

3. EXPLICAR O CRITERIO DE CADA SECAO
   Ao apresentar a pontuacao de uma Secao, explique de forma clara o criterio
   utilizado para determinar aquela pontuacao (por exemplo: a contagem de
   palavras do Sobre/Resumo, a presenca de termo de cargo no Titulo/Headline,
   a completude dos campos de cada Experiencia, ou a quantidade de Competencias
   listadas). O Usuario deve entender POR QUE a Secao recebeu aquela pontuacao.

4. NENHUMA SECAO FORNECIDA
   Se NENHUMA Secao for fornecida para avaliacao, informe ao Usuario que nao ha
   Secoes para avaliar e NAO calcule a Pontuacao de Qualidade (nao invente nem
   atribua nenhuma pontuacao nesse caso).

# RECOMENDACOES

Gere Recomendacoes de melhoria a partir dos criterios que NAO foram atendidos,
seguindo as regras abaixo.

1. UMA RECOMENDACAO POR CRITERIO NAO ATENDIDO
   Para CADA criterio de avaliacao que uma Secao nao atender, gere PELO MENOS
   uma Recomendacao, deixando claro a qual Secao e a qual criterio nao atendido
   ela se refere.

2. ORDEM POR IMPACTO (DECRESCENTE)
   Quando houver Recomendacoes para varias deficiencias, ordene as Recomendacoes
   em ordem DECRESCENTE pelo numero de pontos que cada deficiencia subtrai da
   Pontuacao de Qualidade (as deficiencias que mais reduzem a pontuacao aparecem
   primeiro).

3. DESEMPATE
   Se duas ou mais deficiencias subtraem o MESMO numero de pontos da Pontuacao
   de Qualidade, desempate pela ordem em que as Secoes aparecem no perfil (a
   Secao apresentada antes vem primeiro).

4. SECAO SEM DEFICIENCIA
   Quando uma Secao atender a TODOS os criterios de avaliacao aplicaveis a ela,
   declare isso de forma explicita para essa Secao: informe que ela atende a
   todos os criterios e que NENHUMA Recomendacao e necessaria para essa Secao.

5. CONTEUDO DE CADA RECOMENDACAO
   Cada Recomendacao deve incluir:
   - uma ACAO EXECUTAVEL pelo Usuario, que especifique exatamente o que alterar
     na Secao correspondente, e
   - o CRITERIO alvo que essa alteracao visa satisfazer.
   Assim o Usuario sabe o que fazer e qual criterio aquela mudanca atende.

# RELATORIO DE ANALISE

Reuna os resultados da analise em um Relatorio de Analise, seguindo as regras
abaixo.

1. COMPOR O RELATORIO EM UMA UNICA RESPOSTA
   Assim que concluir o calculo da Pontuacao de Qualidade e a geracao das
   Recomendacoes, componha o Relatorio de Analise em UMA UNICA resposta que
   apresente, juntos:
   - a Pontuacao de Qualidade geral,
   - a Pontuacao Visual (na visao dos recrutadores), com os principais fatores,
   - a avaliacao de CADA Secao avaliada (com a pontuacao e o criterio de cada
     uma),
   - a avaliacao visual (primeira impressao, clareza, escaneabilidade,
     profissionalismo e impacto), e
   - a lista completa de Recomendacoes, incluindo as de ordem visual.

2. RELATORIO SEM RECOMENDACOES
   Se a lista de Recomendacoes estiver vazia ao compor o Relatorio (ou seja,
   todas as Secoes atenderam aos criterios), ainda assim inclua no Relatorio a
   Pontuacao de Qualidade e a avaliacao por Secao, e declare EXPLICITAMENTE que
   nao ha Recomendacoes.

3. REAPRESENTAR O RELATORIO QUANDO PEDIDO
   Quando o Usuario solicitar novamente o Relatorio de Analise durante a
   conversa, reapresente o Relatorio correspondente ao perfil fornecido na
   conversa, usando o historico para recuperar os resultados ja produzidos.

4. RELATORIO AINDA NAO DISPONIVEL
   Se o Usuario solicitar o Relatorio de Analise ANTES de voce te-lo composto na
   conversa, informe que a analise ainda nao foi concluida e que, por isso, o
   Relatorio de Analise ainda nao esta disponivel.

# PERGUNTAS DE ACOMPANHAMENTO

Depois de entregar o Relatorio de Analise, o Usuario pode fazer perguntas sobre
os resultados. Responda seguindo as regras abaixo.

1. PERGUNTAS SOBRE UMA RECOMENDACAO
   Quando o Usuario perguntar sobre uma Recomendacao presente no Relatorio de
   Analise, responda usando o conteudo daquela Recomendacao e da avaliacao da
   Secao associada, conforme registrados no historico da conversa.

2. EXEMPLO DE MELHORIA PARA UMA SECAO
   Quando o Usuario pedir um exemplo de melhoria para uma Secao que ja foi
   fornecida na conversa, forneca PELO MENOS um exemplo de texto reescrito para
   aquela Secao, de modo que o exemplo atenda aos criterios de avaliacao da
   Secao correspondente (por exemplo, um Sobre/Resumo com 40 palavras ou mais,
   um Titulo/Headline com termo de cargo, e assim por diante).

3. MANTER O CONTEXTO DURANTE A CONVERSA
   Enquanto a conversa estiver ativa, mantenha o contexto do perfil e do
   Relatorio de Analise (por meio do historico reenviado a cada mensagem) para
   responder de forma coerente as perguntas de acompanhamento.

4. ACOMPANHAMENTO ANTES DO RELATORIO EXISTIR
   Se o Usuario fizer uma pergunta de acompanhamento ou pedir um exemplo de
   melhoria ANTES de voce ter gerado o Relatorio de Analise, informe que a
   analise ainda nao foi realizada e peca a Entrada de Perfil, PRESERVANDO as
   Secoes que ja tenham sido recebidas na conversa.

# REANALISE APOS ATUALIZACAO

O Usuario pode atualizar Secoes do perfil e pedir uma nova analise para conferir
a melhoria. Siga as regras abaixo.

1. SUBSTITUIR A SECAO ATUALIZADA
   Quando o Usuario fornecer uma versao atualizada de uma Secao que ja estava
   presente na conversa, SUBSTITUA INTEGRALMENTE o conteudo anterior daquela
   Secao pelo novo conteudo (a versao atualizada passa a valer por completo).

2. ATUALIZACAO COM CONTEUDO VAZIO
   Se a versao atualizada de uma Secao vier com conteudo vazio (zero caracteres
   ou apenas espacos em branco), MANTENHA o conteudo anterior daquela Secao
   inalterado e informe ao Usuario que a atualizacao nao foi aplicada por conter
   conteudo vazio.

3. RECALCULAR A PONTUACAO
   Quando o Usuario pedir uma nova analise apos atualizar uma ou mais Secoes,
   recalcule a Pontuacao de Qualidade (numero inteiro de 0 a 100) com base em
   TODAS as Secoes atualizadas presentes na conversa.

4. COMPOR UM NOVO RELATORIO
   Apos recalcular a Pontuacao de Qualidade, componha um NOVO Relatorio de
   Analise com base nas Secoes atualizadas, seguindo as mesmas regras da secao
   RELATORIO DE ANALISE.

5. APRESENTAR A VARIACAO (QUANDO HOUVER PONTUACAO ANTERIOR)
   Se ja existir uma Pontuacao de Qualidade anterior na conversa, apresente a
   VARIACAO numerica entre a pontuacao anterior e a nova pontuacao, indicando
   claramente se houve AUMENTO, REDUCAO ou AUSENCIA de alteracao.

6. SEM PONTUACAO ANTERIOR PARA COMPARAR
   Se NAO existir uma Pontuacao de Qualidade anterior na conversa, apresente
   apenas a nova Pontuacao de Qualidade e informe ao Usuario que nao ha analise
   anterior para comparacao.

# ENTRADAS INVALIDAS

Nem toda mensagem recebida sera uma Entrada de Perfil valida. Trate os casos
abaixo com gentileza, sem encerrar a conversa e sem descartar o que ja foi
recebido.

1. CONTEUDO SEM NENHUMA SECAO RECONHECIVEL
   Se a mensagem do Usuario NAO contiver nenhuma Secao reconhecivel (nenhum
   rotulo ou conteudo que corresponda a Titulo/Headline, Sobre/Resumo,
   Experiencia, Formacao Academica ou Competencias), avise que o conteudo nao
   pode ser identificado como um perfil do LinkedIn e peca que o Usuario reenvie
   a Entrada de Perfil com o texto das Secoes.

2. MENSAGEM FORA DO ESCOPO (SEM PEDIDO DE ANALISE)
   Se a mensagem nao tiver nenhuma Secao reconhecivel e tambem NAO pedir uma
   analise de perfil (ou seja, for um assunto fora do escopo), informe que a
   Sophia atua exclusivamente na analise de perfis do LinkedIn e peca o envio de
   uma Entrada de Perfil. Nao responda ao assunto fora do escopo.

3. FALHA DURANTE O PROCESSAMENTO DA ANALISE
   Se ocorrer uma falha durante o processamento da analise que impeca a geracao
   do resultado, avise que a analise nao foi concluida e peca que o Usuario
   reenvie a Entrada de Perfil. Preserve todo o conteudo ja recebido na conversa
   e permaneca disponivel para um novo envio, SEM encerrar a conversa.
   (Observacao: a indisponibilidade tecnica do Bedrock tambem e tratada no
   codigo da rota /chat, que devolve uma resposta amigavel; aqui fica apenas a
   orientacao de como a Sophia deve conduzir essa situacao na conversa.)

# PRIVACIDADE DOS DADOS

Os dados do Perfil do Usuario sao sensiveis. Seja transparente sobre como eles
sao usados e respeite os limites abaixo.

1. AVISO DE PRIVACIDADE AO INICIAR A CONVERSA
   Ao iniciar a conversa (na mensagem de apresentacao), informe ao Usuario que
   os dados do Perfil sao usados EXCLUSIVAMENTE para a analise durante a conversa
   atual e que NAO sao retidos apos o seu encerramento.

2. EXCLUSAO DOS DADOS A PEDIDO
   Quando o Usuario solicitar a exclusao dos dados do Perfil durante a conversa,
   confirme que os dados do Perfil foram descartados. (Neste projeto, o descarte
   real acontece no cliente quando o Usuario usa a opcao de limpar a conversa; a
   Sophia apenas confirma esse descarte na conversa.)

3. USO RESTRITO A CONVERSA ATUAL
   Restrinja o uso dos dados do Perfil EXCLUSIVAMENTE a analise da conversa
   atual. Nao transmita nem reutilize esses dados em outras conversas ou para
   outros Usuarios.
"""


# ---------------------------------------------------------------------------
# gerar_resposta(mensagem, historico)
# ---------------------------------------------------------------------------
# Funcao auxiliar que encapsula a conversa com o Amazon Bedrock. Ela recebe a
# mensagem atual do Usuario e o historico da conversa (os turnos anteriores da
# Sessao), monta a requisicao no formato esperado pelo modelo e devolve o texto
# gerado pela Sophia.
#
# Parametros:
#   - mensagem: str
#       O texto enviado pelo Usuario nesta rodada da conversa.
#   - historico: list | None
#       Lista de turnos anteriores da Sessao, cada um no formato
#       {"role": "user"|"assistant", "content": "..."}. Quando None, assume-se
#       uma lista vazia (inicio da conversa). O historico e reenviado a cada
#       chamada para preservar o contexto do Perfil (projeto sem estado no
#       servidor).
#
# Retorno:
#   - str: o texto da resposta gerada pelo modelo.
#
# Observacao sobre erros: o tratamento de excecoes do Bedrock (indisponibilidade,
# credenciais ausentes, throttling etc.) e feito na rota /chat, que captura a
# excecao e devolve uma resposta amigavel. Por isso, aqui as excecoes podem
# propagar normalmente.
# ---------------------------------------------------------------------------
def gerar_resposta(mensagem, historico=None):
    # Se nenhum historico for informado, comeca com uma lista vazia (1a mensagem).
    if historico is None:
        historico = []

    # Monta a lista de mensagens no formato da API Messages do Anthropic:
    # o historico acumulado da Sessao seguido do turno atual do Usuario.
    mensagens = list(historico)
    mensagens.append({"role": "user", "content": mensagem})

    # Monta o corpo (payload) da chamada ao modelo no Bedrock.
    corpo = {
        # Versao do formato de requisicao esperado pelo modelo Anthropic no Bedrock.
        "anthropic_version": "bedrock-2023-05-31",
        # Instrucao de sistema: a personalidade e todas as regras da Sophia.
        "system": SYSTEM_PROMPT,
        # Historico da conversa + a mensagem atual do Usuario.
        "messages": mensagens,
        # Limite de tokens da resposta: valor adequado a relatorios analiticos.
        "max_tokens": 2000,
        # Temperatura baixa para respostas consistentes e objetivas.
        "temperature": 0.2,
    }

    # Invoca o modelo no Amazon Bedrock. O corpo e enviado como JSON (string).
    resposta = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(corpo),
    )

    # Le o corpo da resposta (bytes) e converte de JSON para dicionario Python.
    resultado = json.loads(resposta["body"].read())

    # Extrai o texto gerado no formato da Messages API do Anthropic:
    # o conteudo vem em uma lista de blocos; o texto fica no primeiro bloco.
    texto = resultado["content"][0]["text"]

    # Devolve apenas o texto da resposta da Sophia.
    return texto

# ---------------------------------------------------------------------------
# Rota GET / (pagina de chat)
# ---------------------------------------------------------------------------
# Esta rota e o ponto de entrada da conversa com a Sophia. Quando o Usuario
# acessa o endereco raiz da aplicacao (por exemplo, http://localhost:5000/) no
# navegador, o Flask renderiza e devolve a pagina de chat definida em
# templates/index.html. E nessa pagina que o Usuario inicia a conversa, envia o
# conteudo do Perfil e recebe as respostas da Sophia.
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    # Renderiza o arquivo templates/index.html e o entrega ao navegador.
    return render_template("index.html")

# ---------------------------------------------------------------------------
# Rota POST /limpar (descartar a memoria de conversa do servidor)
# ---------------------------------------------------------------------------
# Esvazia a lista historico_conversa, descartando o contexto do Perfil guardado
# no servidor. E usada pelo botao "Limpar conversa" da pagina, apoiando a
# promessa de privacidade (os dados do Perfil nao sao retidos). Responde sempre
# com HTTP 200 e uma confirmacao simples.
# ---------------------------------------------------------------------------
@app.route("/limpar", methods=["POST"])
def limpar():
    # clear() esvazia a lista no lugar, preservando a mesma referencia global.
    historico_conversa.clear()
    return jsonify({"ok": True}), 200

# ---------------------------------------------------------------------------
# Rota POST /sincronizar (restaurar o contexto de uma conversa salva)
# ---------------------------------------------------------------------------
# O historico de conversas e guardado no NAVEGADOR (localStorage). Quando o
# Usuario troca de conversa pela barra lateral, o navegador envia para ca os
# turnos daquela conversa, para que a memoria do servidor (historico_conversa)
# volte a refletir exatamente o contexto escolhido. Assim a Sophia continua a
# conversa certa, mesmo com varias conversas guardadas no cliente.
#
# Corpo esperado (JSON):
#   {"history": [{"role": "user"|"assistant", "content": "..."}, ...]}
#
# Regras de validacao (didaticas e defensivas):
#   - Aceita apenas itens com role valido ("user" ou "assistant") e content
#     string; qualquer item fora desse formato e ignorado.
#   - Lista ausente ou corpo invalido resultam em uma memoria vazia (equivale a
#     iniciar uma conversa nova), respondendo 200 mesmo assim.
# ---------------------------------------------------------------------------
@app.route("/sincronizar", methods=["POST"])
def sincronizar():
    # Le o corpo JSON sem lancar excecao se vier malformado.
    dados = request.get_json(silent=True) or {}
    turnos = dados.get("history")

    # Monta uma lista limpa apenas com turnos no formato esperado.
    nova_memoria = []
    if isinstance(turnos, list):
        for turno in turnos:
            if not isinstance(turno, dict):
                continue
            papel = turno.get("role")
            conteudo = turno.get("content")
            if papel in ("user", "assistant") and isinstance(conteudo, str):
                nova_memoria.append({"role": papel, "content": conteudo})

    # Substitui a memoria do servidor pela conversa escolhida, preservando a
    # mesma referencia global (clear + extend, em vez de reatribuir).
    historico_conversa.clear()
    historico_conversa.extend(nova_memoria)

    return jsonify({"ok": True, "turnos": len(historico_conversa)}), 200

# ---------------------------------------------------------------------------
# Rota POST /chat (conversa com a Sophia)
# ---------------------------------------------------------------------------
# Esta rota recebe cada mensagem do Usuario, valida a entrada, chama o modelo
# do Amazon Bedrock (por meio da funcao gerar_resposta) e devolve a resposta da
# Sophia em JSON. O contexto do Perfil (o historico) e guardado no servidor, na
# lista historico_conversa.
#
# A rota aceita DOIS formatos de corpo:
#   1. JSON: {"message": "<texto do Usuario>"}  -> mensagem de texto comum.
#   2. multipart/form-data: um campo de texto "message" (opcional) e um campo
#      de arquivo "pdf" com o curriculo. O texto do PDF e extraido e anexado a
#      mensagem antes de chamar o Bedrock.
#
# Respostas:
#   - 200 {"reply": "<resposta da Sophia>"}  -> sucesso (ou falha tratada do Bedrock).
#   - 400 {"error": "<motivo>"}              -> entrada vazia ou corpo invalido.
# ---------------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    # -----------------------------------------------------------------------
    # 1) Ler a entrada do Usuario, que pode vir de duas formas:
    #    (a) multipart/form-data, quando ha um PDF anexado (campo "pdf") e,
    #        opcionalmente, um texto no campo "message"; ou
    #    (b) JSON simples, apenas com o campo "message".
    # -----------------------------------------------------------------------
    arquivo_pdf = request.files.get("pdf")

    if arquivo_pdf is not None and arquivo_pdf.filename:
        # (a) Envio com PDF: o texto (se houver) vem nos campos do formulario.
        mensagem = request.form.get("message", "")

        # Extrai o texto do PDF. Se o arquivo nao for um PDF valido, avisamos
        # o Usuario com HTTP 400 em vez de deixar estourar um erro interno.
        try:
            texto_pdf = extrair_texto_pdf(arquivo_pdf)
        except Exception:
            return jsonify({
                "error": "nao consegui ler o PDF enviado. Verifique se o arquivo "
                         "e um PDF valido e tente novamente."
            }), 400

        # PDF sem texto selecionavel (provavelmente uma imagem digitalizada).
        if texto_pdf.strip() == "":
            return jsonify({
                "error": "o PDF enviado nao contem texto selecionavel (pode ser uma "
                         "imagem digitalizada). Cole o texto do perfil ou envie um PDF "
                         "com texto."
            }), 400

        # Monta a mensagem final: o comentario do Usuario (se houver) seguido do
        # conteudo extraido do curriculo, com um marcador claro para a Sophia.
        partes = []
        if isinstance(mensagem, str) and mensagem.strip():
            partes.append(mensagem.strip())
        partes.append(
            "[Curriculo em PDF anexado pelo Usuario - texto extraido a seguir]\n"
            + texto_pdf
        )
        mensagem = "\n\n".join(partes)

    else:
        # (b) Envio sem PDF: esperamos um corpo JSON com o campo "message".
        # silent=True evita excecao em JSON malformado (respondemos 400).
        dados = request.get_json(silent=True)
        if dados is None:
            return jsonify({"error": "corpo da requisicao invalido ou JSON malformado"}), 400

        # -------------------------------------------------------------------
        # Validar a mensagem: vazia quando ausente, nao-texto ou so espacos.
        # Nesse caso, HTTP 400 SEM chamar o Bedrock (regra: "mensagem vazia
        # retorna erro 400").
        # -------------------------------------------------------------------
        mensagem = dados.get("message")
        if not isinstance(mensagem, str) or mensagem.strip() == "":
            return jsonify({"error": "mensagem vazia"}), 400

    # -----------------------------------------------------------------------
    # 3) Usar a memoria de conversa guardada no servidor.
    # Em vez de depender do historico enviado pelo navegador, usamos a lista
    # global historico_conversa, que acumula TODOS os turnos ja trocados. Ela
    # e enviada inteira ao Bedrock a cada pergunta, preservando o contexto do
    # Perfil ao longo da conversa.
    # -----------------------------------------------------------------------
    historico = historico_conversa

    # -----------------------------------------------------------------------
    # 4) Chamar o modelo e devolver a resposta.
    # Envolvemos a chamada ao Bedrock em um try/except para manter a Sessao
    # viva mesmo quando o servico estiver indisponivel (Requisitos 9.3 e 9.4).
    # -----------------------------------------------------------------------
    try:
        # Gera a resposta da Sophia a partir da mensagem atual e de todo o
        # historico acumulado no servidor.
        resposta = gerar_resposta(mensagem, historico)

        # Memoria de conversa: so DEPOIS de obter a resposta com sucesso,
        # acrescentamos ao historico o turno do Usuario e o da Sophia. Assim,
        # se a chamada ao Bedrock falhar, a memoria nao fica com uma pergunta
        # sem a resposta correspondente.
        historico_conversa.append({"role": "user", "content": mensagem})
        historico_conversa.append({"role": "assistant", "content": resposta})

        # Sucesso: devolve a resposta em JSON (acentos legiveis ja configurados).
        return jsonify({"reply": resposta}), 200

    # Credenciais AWS ausentes: tratada como indisponibilidade do servico.
    # Nao expomos ao Usuario que faltam credenciais (detalhe interno).
    except NoCredentialsError:
        return jsonify({
            "reply": "Nao consegui concluir a analise agora por uma indisponibilidade "
                     "temporaria. Por favor, reenvie o conteudo do seu perfil que eu tento "
                     "novamente."
        }), 200

    # Erros devolvidos pelo Bedrock (ex.: throttling, acesso negado, modelo
    # indisponivel) ou erros de baixo nivel do SDK (ex.: timeout, falha de
    # conexao). Devolvemos uma mensagem amigavel em portugues, sem stack trace.
    except (ClientError, BotoCoreError):
        return jsonify({
            "reply": "Nao consegui concluir a analise agora por uma instabilidade na conexao "
                     "com o servico. Por favor, reenvie o conteudo do seu perfil que eu tento "
                     "novamente."
        }), 200

    # Qualquer outra falha inesperada: tambem preservamos a Sessao e pedimos o
    # reenvio, sem derrubar a conversa nem revelar detalhes internos ao Usuario.
    except Exception:
        return jsonify({
            "reply": "Nao consegui concluir a analise agora. Por favor, reenvie o conteudo do "
                     "seu perfil que eu tento novamente."
        }), 200


# ---------------------------------------------------------------------------
# Ponto de entrada da aplicacao.
# ---------------------------------------------------------------------------
# Quando este arquivo e executado diretamente com "python app.py", o bloco
# abaixo inicia o servidor de desenvolvimento do Flask em localhost (127.0.0.1)
# na porta 5000, conforme a stack obrigatoria do projeto ("Rodar com:
# python app.py, em localhost:5000"). O modo debug facilita o desenvolvimento,
# recarregando o servidor a cada alteracao e exibindo mensagens de erro uteis.
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
