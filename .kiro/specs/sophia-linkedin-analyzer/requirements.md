# Requirements Document

## Introduction

Sophia é um chatbot assistente especializado em auxiliar usuários na análise de perfis do LinkedIn. O objetivo da Sophia é receber as informações de um perfil do LinkedIn, avaliá-las em relação a critérios de qualidade (completude, clareza, palavras-chave, consistência) e fornecer feedback acionável e sugestões de melhoria por meio de uma conversa. A Sophia conduz a interação, solicita as seções do perfil quando necessário, produz uma pontuação de qualidade e recomendações priorizadas, mantendo o contexto ao longo da conversa.

Este documento define os requisitos funcionais da Sophia usando padrões EARS e as regras de qualidade INCOSE.

## Glossário

- **Sophia**: O sistema de chatbot que conduz a conversa com o usuário e executa a análise de perfil do LinkedIn.
- **Usuário**: A pessoa que interage com a Sophia para obter a análise de um perfil do LinkedIn.
- **Perfil**: Conjunto de dados de um perfil do LinkedIn fornecido pelo Usuário, composto por seções.
- **Seção**: Parte estruturada do Perfil (por exemplo: título/headline, resumo/sobre, experiência, formação acadêmica, competências).
- **Entrada_de_Perfil**: Texto ou dados que o Usuário fornece representando uma ou mais Seções do Perfil.
- **Analisador**: Componente da Sophia responsável por avaliar o Perfil e gerar resultados de análise.
- **Pontuação_de_Qualidade**: Valor numérico de 0 a 100 que representa a qualidade geral do Perfil segundo os critérios de avaliação.
- **Recomendação**: Sugestão de melhoria acionável gerada pela Sophia para uma Seção específica.
- **Relatório_de_Análise**: Resultado consolidado contendo a Pontuação_de_Qualidade, a avaliação por Seção e a lista de Recomendações.
- **Sessão**: Período contínuo de interação entre o Usuário e a Sophia, no qual o contexto do Perfil é mantido.

## Requirements

### Requirement 1: Início da conversa e apresentação

**User Story:** Como Usuário, quero que a Sophia se apresente e explique como pode ajudar, para que eu entenda como fornecer meu perfil e o que esperar da análise.

#### Acceptance Criteria

1. WHEN o Usuário envia a primeira mensagem de uma Sessão, THE Sophia SHALL responder em uma única mensagem que a apresente pelo nome "Sophia" e informe que ela auxilia na análise de perfis do LinkedIn.
2. WHEN o Usuário envia a primeira mensagem de uma Sessão, THE Sophia SHALL listar nominalmente, na mesma mensagem de apresentação, as Seções do Perfil que podem ser analisadas (por exemplo: Título/Headline, Sobre/Resumo, Experiência e Competências).
3. WHEN o Usuário envia a primeira mensagem de uma Sessão, THE Sophia SHALL solicitar, na mesma mensagem de apresentação, que o Usuário forneça a Entrada_de_Perfil, indicando que o conteúdo deve ser enviado como texto das Seções do Perfil em uma mensagem subsequente.
4. IF o Usuário, na primeira mensagem da Sessão, envia conteúdo que não corresponde a uma Entrada_de_Perfil, THEN THE Sophia SHALL apresentar-se conforme os critérios 1 a 3 e reiterar a solicitação da Entrada_de_Perfil, preservando a mensagem recebida sem iniciar a análise.

### Requirement 2: Recebimento da entrada de perfil

**User Story:** Como Usuário, quero fornecer os dados do meu perfil do LinkedIn em texto, para que a Sophia possa analisá-los.

#### Acceptance Criteria

1. WHEN o Usuário envia uma Entrada_de_Perfil com pelo menos um caractere não vazio, THE Sophia SHALL identificar quais das Seções reconhecíveis (título/headline, resumo/sobre, experiência, formação acadêmica, competências) estão presentes na Entrada_de_Perfil.
2. IF a Entrada_de_Perfil estiver vazia, em que vazia significa conter zero caracteres ou conter apenas caracteres de espaço em branco (espaços, tabulações ou quebras de linha), THEN THE Sophia SHALL solicitar ao Usuário que forneça o conteúdo do Perfil, mantendo as Seções já acumuladas na Sessão.
3. IF ao menos uma das Seções obrigatórias (título/headline, resumo/sobre, experiência) estiver ausente após processar a Entrada_de_Perfil, THEN THE Sophia SHALL solicitar ao Usuário o conteúdo de cada Seção obrigatória ausente, indicando o nome de cada Seção obrigatória ausente.
4. WHERE o Usuário fornece o Perfil em múltiplas mensagens, THE Sophia SHALL acumular na Sessão as Seções reconhecíveis recebidas em cada Entrada_de_Perfil, substituindo o conteúdo de uma Seção quando a mesma Seção for recebida novamente.
5. WHEN todas as Seções obrigatórias (título/headline, resumo/sobre, experiência) estiverem acumuladas na Sessão, THE Sophia SHALL iniciar a análise utilizando as Seções acumuladas na Sessão.

### Requirement 3: Análise das seções do perfil

**User Story:** Como Usuário, quero que a Sophia avalie cada seção do meu perfil, para que eu saiba o que está bom e o que precisa melhorar.

#### Acceptance Criteria

1. WHEN o Analisador avalia uma Seção, THE Sophia SHALL verificar a completude da Seção considerando-a completa somente quando todos os campos esperados daquela Seção estiverem presentes e não vazios.
2. WHEN o Analisador avalia a Seção de título/headline, THE Sophia SHALL verificar que o texto contém pelo menos 1 termo correspondente a um cargo ou área de atuação de uma lista de termos de referência mantida pelo Analisador.
3. WHEN o Analisador avalia a Seção de resumo/sobre, THE Sophia SHALL verificar que o texto contém no mínimo 40 palavras.
4. WHEN o Analisador avalia a Seção de experiência, THE Sophia SHALL verificar que cada registro de experiência contém cargo, organização e período, todos presentes e não vazios.
5. WHEN o Analisador avalia a Seção de competências, THE Sophia SHALL verificar que a Seção contém no mínimo 5 competências listadas.
6. WHEN o Analisador conclui a avaliação de uma Seção, THE Sophia SHALL atribuir à Seção o status "bom" quando todos os critérios aplicáveis daquela Seção forem satisfeitos, ou o status "precisa melhorar" quando ao menos um critério aplicável não for satisfeito.
7. IF uma Seção avaliada estiver ausente ou vazia, THEN THE Sophia SHALL atribuir à Seção o status "precisa melhorar" e indicar que a Seção não foi preenchida, sem interromper a avaliação das demais Seções.

### Requirement 4: Pontuação de qualidade

**User Story:** Como Usuário, quero receber uma pontuação de qualidade do meu perfil, para que eu tenha uma medida objetiva do estado atual do perfil.

#### Acceptance Criteria

1. WHEN o Analisador conclui a avaliação de todas as Seções fornecidas, THE Sophia SHALL calcular a Pontuação_de_Qualidade como um número inteiro em uma escala de 0 a 100, onde 0 representa a menor qualidade e 100 a maior qualidade.
2. WHEN a Sophia calcula a Pontuação_de_Qualidade, THE Sophia SHALL apresentar ao Usuário a pontuação de cada Seção avaliada como um número inteiro em uma escala de 0 a 100.
3. WHEN a Sophia apresenta a Pontuação_de_Qualidade, THE Sophia SHALL apresentar, para cada Seção avaliada, o critério utilizado para determinar a pontuação daquela Seção.
4. IF nenhuma Seção é fornecida para avaliação, THEN THE Sophia SHALL apresentar ao Usuário uma mensagem indicando que não há Seções para avaliar e SHALL abster-se de calcular a Pontuação_de_Qualidade.

### Requirement 5: Recomendações de melhoria

**User Story:** Como Usuário, quero receber sugestões específicas de melhoria, para que eu possa aprimorar meu perfil do LinkedIn.

#### Acceptance Criteria

1. WHEN o Analisador identifica que uma Seção não atende a um ou mais critérios de avaliação, THE Sophia SHALL gerar pelo menos uma Recomendação associada a essa Seção e ao critério não atendido.
2. WHEN a Sophia gera Recomendações para múltiplas deficiências, THE Sophia SHALL ordenar as Recomendações em ordem decrescente pelo número de pontos que cada deficiência subtrai da Pontuação_de_Qualidade.
3. IF duas ou mais deficiências subtraem o mesmo número de pontos da Pontuação_de_Qualidade, THEN THE Sophia SHALL ordená-las pela ordem de apresentação das Seções no perfil.
4. WHERE uma Seção atende a todos os critérios de avaliação, THE Sophia SHALL informar ao Usuário, de forma explícita para essa Seção, que a Seção atende a todos os critérios e que nenhuma Recomendação é necessária.
5. WHEN a Sophia apresenta uma Recomendação, THE Sophia SHALL incluir uma ação executável pelo Usuário que especifique o que alterar na Seção correspondente e o critério de avaliação que a alteração visa satisfazer.

### Requirement 6: Relatório consolidado

**User Story:** Como Usuário, quero receber um relatório consolidado da análise, para que eu tenha uma visão completa dos resultados em um único lugar.

#### Acceptance Criteria

1. WHEN a Sophia conclui o cálculo da Pontuação_de_Qualidade e a geração das Recomendações, THE Sophia SHALL compor um Relatório_de_Análise que apresente, em uma única resposta, a Pontuação_de_Qualidade, a avaliação de cada Seção avaliada e a lista de Recomendações.
2. IF a lista de Recomendações estiver vazia ao compor o Relatório_de_Análise, THEN THE Sophia SHALL incluir no Relatório_de_Análise a Pontuação_de_Qualidade e a avaliação por Seção e indicar explicitamente que não há Recomendações.
3. WHEN o Usuário solicita o Relatório_de_Análise novamente durante a Sessão, THE Sophia SHALL apresentar o Relatório_de_Análise correspondente ao Perfil fornecido na Sessão.
4. IF o Usuário solicita o Relatório_de_Análise antes de a Sophia tê-lo composto na Sessão, THEN THE Sophia SHALL informar ao Usuário, por meio de uma mensagem indicando que a análise ainda não foi concluída, que o Relatório_de_Análise não está disponível.

### Requirement 7: Perguntas de acompanhamento

**User Story:** Como Usuário, quero poder fazer perguntas sobre a análise, para que eu entenda melhor as recomendações e como aplicá-las.

#### Acceptance Criteria

1. WHEN o Usuário envia uma pergunta sobre uma Recomendação presente no Relatório_de_Análise da Sessão, THE Sophia SHALL responder utilizando o conteúdo da Recomendação correspondente e da avaliação da Seção associada registradas no Relatório_de_Análise da Sessão.
2. WHEN o Usuário solicita um exemplo de melhoria para uma Seção previamente fornecida na Sessão, THE Sophia SHALL fornecer ao menos um exemplo de texto reescrito para a Seção correspondente que atenda aos critérios de avaliação daquela Seção.
3. WHILE a Sessão estiver ativa, THE Sophia SHALL manter o contexto do Perfil e do Relatório_de_Análise da Sessão para responder às perguntas de acompanhamento.
4. IF o Usuário envia uma pergunta de acompanhamento ou solicita um exemplo de melhoria antes de a Sophia ter gerado o Relatório_de_Análise na Sessão, THEN THE Sophia SHALL informar ao Usuário que a análise ainda não foi realizada e solicitar a Entrada_de_Perfil, preservando as Seções já recebidas na Sessão.

### Requirement 8: Reanálise após atualização

**User Story:** Como Usuário, quero atualizar seções do meu perfil e obter uma nova análise, para que eu possa verificar a melhoria após aplicar as recomendações.

#### Acceptance Criteria

1. WHEN o Usuário fornece uma versão atualizada de uma Seção já presente na Sessão, THE Sophia SHALL substituir integralmente o conteúdo anterior dessa Seção pelo novo conteúdo na Sessão.
2. IF o Usuário fornece uma versão atualizada de uma Seção com conteúdo vazio, THEN THE Sophia SHALL manter o conteúdo anterior dessa Seção inalterado na Sessão e informar ao Usuário que a atualização não foi aplicada por conteúdo vazio.
3. WHEN o Usuário solicita uma nova análise após atualizar uma Seção, THE Sophia SHALL recalcular a Pontuação_de_Qualidade na escala de 0 a 100 com base em todas as Seções atualizadas presentes na Sessão.
4. WHEN a Sophia recalcula a Pontuação_de_Qualidade, THE Sophia SHALL compor um novo Relatório_de_Análise com base nas Seções atualizadas da Sessão.
5. WHEN a Sophia recalcula a Pontuação_de_Qualidade e existe uma Pontuação_de_Qualidade anterior na Sessão, THE Sophia SHALL apresentar a variação numérica entre a Pontuação_de_Qualidade anterior e a nova Pontuação_de_Qualidade, indicando se houve aumento, redução ou ausência de alteração.
6. IF o Usuário solicita uma nova análise e não existe uma Pontuação_de_Qualidade anterior na Sessão, THEN THE Sophia SHALL apresentar apenas a nova Pontuação_de_Qualidade e informar ao Usuário que não há análise anterior para comparação.

### Requirement 9: Tratamento de entradas inválidas

**User Story:** Como Usuário, quero ser avisado quando minha entrada não puder ser analisada, para que eu saiba como corrigir e prosseguir.

#### Acceptance Criteria

1. IF a Entrada_de_Perfil não contiver pelo menos uma Seção reconhecível (uma Seção cujo rótulo corresponda a uma das Seções de perfil previstas na análise), THEN THE Sophia SHALL responder ao Usuário, em até 10 segundos, com uma mensagem indicando que o conteúdo não pôde ser identificado como um perfil do LinkedIn e solicitando o reenvio da Entrada_de_Perfil.
2. IF o Usuário enviar uma mensagem que não contenha nenhuma Seção reconhecível e cujo conteúdo não solicite uma análise de perfil, THEN THE Sophia SHALL responder ao Usuário, em até 10 segundos, com uma mensagem informando que atua exclusivamente na análise de perfis do LinkedIn e solicitando o envio de uma Entrada_de_Perfil.
3. IF ocorrer uma falha durante o processamento da análise (impedindo a geração de um resultado de análise), THEN THE Sophia SHALL responder ao Usuário, em até 10 segundos, com uma mensagem indicando que a análise não foi concluída e solicitando que o Usuário reenvie a Entrada_de_Perfil.
4. IF ocorrer uma falha durante o processamento da análise, THEN THE Sophia SHALL preservar a Entrada_de_Perfil recebida e permanecer disponível para receber um novo envio, sem encerrar a sessão de conversa.

### Requirement 10: Privacidade dos dados

**User Story:** Como Usuário, quero que meus dados de perfil sejam tratados de forma transparente, para que eu saiba como minhas informações são usadas.

#### Acceptance Criteria

1. WHEN o Usuário inicia uma Sessão, THE Sophia SHALL exibir ao Usuário uma mensagem informando que os dados do Perfil são utilizados exclusivamente para a análise durante a Sessão atual e não são retidos após o encerramento da Sessão.
2. WHEN a Sessão é encerrada pelo Usuário, THE Sophia SHALL descartar os dados do Perfil associados à Sessão em até 5 segundos, de modo que os dados não fiquem recuperáveis em nenhuma Sessão posterior.
3. WHEN o Usuário solicita a exclusão dos dados do Perfil durante a Sessão, THE Sophia SHALL descartar os dados do Perfil associados à Sessão em até 5 segundos e exibir ao Usuário uma confirmação indicando que os dados do Perfil foram descartados.
4. IF o descarte dos dados do Perfil não for concluído com sucesso, THEN THE Sophia SHALL exibir ao Usuário uma mensagem indicando a falha no descarte e SHALL manter uma nova tentativa de descarte até o encerramento da Sessão.
5. WHILE uma Sessão está ativa, THE Sophia SHALL restringir o uso dos dados do Perfil exclusivamente à análise da Sessão atual, sem transmiti-los para outras Sessões ou Usuários.
