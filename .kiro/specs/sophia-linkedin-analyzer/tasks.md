# Plano de Implementação: Sophia - Analisador de Perfis do LinkedIn

## Overview

A implementação cria uma aplicação Flask mínima e didática com dois arquivos principais: `app.py` na raiz (rotas, validação, integração com o Amazon Bedrock e a constante `SYSTEM_PROMPT` que concentra todas as regras de análise) e `templates/index.html` (a página de chat que mantém o histórico da Sessão no navegador). As dependências ficam em `requirements.txt` (apenas `flask` e `boto3`).

Como o "Analisador" é conversacional (executado pelo modelo do Bedrock e orientado pelo `SYSTEM_PROMPT`), a maior parte das regras de negócio (R1–R10) é materializada em linguagem natural dentro do `SYSTEM_PROMPT`. O código Flask apenas serve a página, valida entradas, monta o contexto e chama o Bedrock.

O projeto proíbe testes automatizados; portanto, não há tarefas de criação de suítes de teste. A validação é manual e exploratória, descrita como uma tarefa final.

## Tasks

- [x] 1. Preparar a estrutura do projeto e as dependências
  - Criar o arquivo `requirements.txt` na raiz contendo apenas `flask` e `boto3`.
  - Criar a pasta `templates/` para abrigar a página de chat.
  - Garantir a estrutura mínima: `app.py` na raiz e `templates/index.html`.
  - Adicionar comentários em português explicando o propósito de cada arquivo.
  - _Requirements: (stack obrigatória — base para todos os requisitos)_

- [x] 2. Criar o esqueleto do `app.py` (Flask, configuração e cliente Bedrock)
  - [x] 2.1 Inicializar a aplicação Flask e configurar JSON com acentos legíveis
    - Criar a instância Flask em `app.py`.
    - Definir `app.json.ensure_ascii = False` para respostas JSON com acentos legíveis.
    - Comentar o código em português.
    - _Requirements: (stack obrigatória — JSON com acentos legíveis)_

  - [x] 2.2 Configurar o cliente do Amazon Bedrock via boto3
    - Criar o cliente com `boto3.client("bedrock-runtime", region_name="us-east-1")`.
    - Ler as credenciais AWS exclusivamente de variáveis de ambiente; nunca escrever chaves no código.
    - Definir constante com o Model ID exato `us.anthropic.claude-haiku-4-5-20251001-v1:0`.
    - Comentar em português a origem das credenciais e a região.
    - _Requirements: 9.3, 9.4, 10.5_

- [x] 3. Definir a constante `SYSTEM_PROMPT` com a personalidade e todas as regras de análise
  - [x] 3.1 Escrever a identidade, o tom e os limites da Sophia no `SYSTEM_PROMPT`
    - Definir nome "Sophia", escopo exclusivo (análise de perfis do LinkedIn) e tom profissional e acolhedor.
    - Instruir a apresentação na primeira mensagem: apresentar-se, listar nominalmente as Seções analisáveis (Título/Headline, Sobre/Resumo, Experiência, Competências) e pedir a Entrada_de_Perfil.
    - Instruir que, se a primeira mensagem não for um perfil, a Sophia se apresente e reitere o pedido sem iniciar a análise.
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 3.2 Codificar no `SYSTEM_PROMPT` as regras de recebimento e acúmulo da Entrada_de_Perfil
    - Identificar quais Seções reconhecíveis estão presentes na Entrada_de_Perfil.
    - Pedir conteúdo quando a entrada for vazia, mantendo as Seções já acumuladas.
    - Nomear as Seções obrigatórias ausentes (título/headline, resumo/sobre, experiência).
    - Acumular Seções entre mensagens, substituindo o conteúdo quando a mesma Seção for reenviada.
    - Iniciar a análise quando todas as Seções obrigatórias existirem.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.3 Codificar no `SYSTEM_PROMPT` as regras de análise das Seções
    - Completude por campos; título com ≥1 termo de cargo/área (incluir lista de referência embutida no prompt).
    - Resumo/sobre com ≥40 palavras; cada experiência com cargo + organização + período; competências ≥5.
    - Atribuir status "bom" ou "precisa melhorar"; Seção ausente/vazia → "precisa melhorar" sem interromper as demais.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 3.4 Codificar no `SYSTEM_PROMPT` a Pontuação_de_Qualidade e as Recomendações
    - Pontuação geral inteira de 0 a 100 e pontuação por Seção (0 a 100), explicando o critério usado em cada Seção.
    - Se nenhuma Seção for fornecida, informar e não calcular a pontuação.
    - Gerar ≥1 Recomendação por critério não atendido; ordenar por impacto decrescente na pontuação; desempatar pela ordem das Seções.
    - Seção sem deficiência → declarar que atende a todos os critérios; cada Recomendação com ação executável e o critério alvo.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.5 Codificar no `SYSTEM_PROMPT` o Relatório consolidado, o acompanhamento e a reanálise
    - Compor o Relatório_de_Análise em uma única resposta (pontuação + avaliação por Seção + Recomendações); declarar quando não houver Recomendações.
    - Reapresentar o Relatório quando pedido; informar quando pedido antes de existir.
    - Responder perguntas de acompanhamento usando o histórico; fornecer exemplo reescrito que atenda aos critérios; informar e pedir perfil se perguntado antes do Relatório.
    - Reanálise: substituir integralmente a Seção atualizada; atualização vazia → manter conteúdo anterior e avisar; recalcular pontuação; compor novo Relatório; mostrar variação vs. pontuação anterior (ou avisar que não há comparação).
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 3.6 Codificar no `SYSTEM_PROMPT` o tratamento de entradas inválidas e a privacidade
    - Conteúdo sem Seção reconhecível → avisar que não parece um perfil e pedir reenvio; mensagem fora do escopo → informar que a Sophia atua só em análise de perfil.
    - Falha de processamento → avisar que a análise não concluiu e pedir reenvio, preservando o recebido.
    - Mensagem de privacidade ao iniciar a Sessão (dados usados só na Sessão atual, não retidos); confirmar o descarte quando solicitado.
    - _Requirements: 9.1, 9.2, 9.3, 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 4. Implementar a função auxiliar `gerar_resposta(mensagem, historico)`
  - Montar a lista de mensagens no formato da API Messages do Anthropic no Bedrock: concatenar o `historico` e acrescentar o turno atual do Usuário.
  - Montar o corpo do `invoke_model` com `anthropic_version`, `system` (o `SYSTEM_PROMPT`), `messages`, `max_tokens` e `temperature` adequados a respostas analíticas e consistentes.
  - Chamar `bedrock_runtime.invoke_model(modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0", body=...)`.
  - Ler o corpo da resposta, extrair o texto gerado e devolvê-lo.
  - Comentar o código em português.
  - _Requirements: 2.4, 3.1, 4.1, 5.1, 6.1, 7.3, 8.3_

- [x] 5. Implementar a rota `GET /` (página de chat)
  - Renderizar `templates/index.html`.
  - Comentar em português o papel da rota.
  - _Requirements: 1.1 (ponto de entrada da conversa)_

- [x] 6. Implementar a rota `POST /chat` com validação e integração
  - Ler o corpo JSON `{"message": "...", "history": [...]}`.
  - Validar: se `message` estiver ausente ou vazia, retornar HTTP 400 sem chamar o Bedrock.
  - Chamar `gerar_resposta(mensagem, historico)` e retornar `{"reply": ...}` com acentos legíveis.
  - Capturar exceções do Bedrock (ClientError, timeout, throttling, credenciais ausentes) e retornar HTTP 200 com uma `reply` amigável, preservando a Sessão.
  - Tratar JSON malformado retornando HTTP 400 com mensagem explicativa.
  - Comentar cada bloco de tratamento em português.
  - _Requirements: 9.3, 9.4 (validação de mensagem vazia e resiliência do Bedrock)_

- [x] 7. Checkpoint - Revisar o backend
  - Garantir que `app.py` executa com `python app.py` em `localhost:5000` sem erros de importação ou sintaxe. Se surgirem dúvidas, perguntar ao Usuário.

- [x] 8. Implementar a página `templates/index.html`
  - [x] 8.1 Criar a estrutura visual mínima da página de chat
    - Área de histórico de mensagens, campo de entrada e botão de envio.
    - Estilo simples e didático; comentários em português onde ajudarem.
    - _Requirements: 1.1 (interface da conversa)_

  - [x] 8.2 Implementar o JavaScript de envio, histórico e tratamento de erros
    - Manter o array `history` em memória (contexto da Sessão).
    - Enviar `POST /chat` com `message` e `history`; ao receber `reply`, anexar pergunta e resposta ao `history` e às mensagens exibidas.
    - Tratar o HTTP 400 exibindo um aviso de "mensagem vazia".
    - Oferecer a ação "limpar conversa" que zera o `history` local (apoia o descarte de dados a pedido).
    - _Requirements: 2.4, 7.3, 8.1, 10.2, 10.3_

- [x] 9. Checkpoint final - Validação manual da aplicação
  - Rodar `python app.py` e, em `localhost:5000`, validar manualmente os roteiros conversacionais: apresentação (R1), acúmulo e Seções obrigatórias (R2), análise e pontuação (R3, R4), Relatório consolidado (R6), Recomendações ordenadas (R5), acompanhamento (R7), reanálise com variação (R8), entradas inválidas (R9) e privacidade/stateless (R10).
  - Confirmar que `POST /chat` com mensagem vazia retorna HTTP 400 e que uma mensagem válida retorna `{"reply": ...}` com acentos legíveis.
  - Confirmar que recarregar a página apaga o contexto do Perfil (nada retido no servidor) e que a indisponibilidade do Bedrock gera mensagem amigável sem derrubar a Sessão.
  - Se surgirem dúvidas, perguntar ao Usuário.

## Notes

- Este é um projeto mínimo e didático: poucos arquivos (`app.py`, `templates/index.html`, `requirements.txt`) e código simples, comentado em português.
- O projeto **proíbe testes automatizados**; portanto, não há tarefas de criação de suítes de teste (unitários, integração ou PBT). A validação é manual, conforme a tarefa 9.
- Todas as regras de negócio (R1–R10) são concentradas no `SYSTEM_PROMPT`, que é a fonte única de verdade sobre o comportamento da Sophia.
- As credenciais AWS vêm exclusivamente de variáveis de ambiente e nunca são escritas no código.
- Cada tarefa referencia os requisitos específicos para rastreabilidade.
- Os checkpoints garantem validação incremental manual.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6"] },
    { "id": 2, "tasks": ["4"] },
    { "id": 3, "tasks": ["5", "6"] },
    { "id": 4, "tasks": ["8.1"] },
    { "id": 5, "tasks": ["8.2"] }
  ]
}
```
