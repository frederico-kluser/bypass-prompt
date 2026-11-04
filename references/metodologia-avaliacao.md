# Metodologia de métricas — contratos, evidência e desconhecidos

> Este documento define **como interpretar** uma avaliação e não autoriza sua execução. O [roteiro Markdown /prompt-builder + JEV](<avaliacao-prompt-builder-jev.md>) registra a entrega documental anterior. O [laboratório defensivo posterior](<laboratorio-defensivo-glm-jev.md>) é opt-in, exige novo pedido/teto de gasto e distingue anotações sintéticas sem ouro de uma avaliação calibrada; nenhuma execução é automática.

## 1. Especificar o que conta como sucesso

Antes de uma eventual coleta autorizada, fixar:

- Sistema/modelo/snapshot, tarefa, canais de autoridade, ferramentas, identidades/tenant e origem dos dados.
- Ação/conteúdo proibidos **observáveis**, resultado benigno esperado e casos de evidência insuficiente.
- Corpus e ouro humano, orçamento, limite de tentativas/turnos, critério de parada e tratamento de erros.
- Separação entre diagnóstico de estrutura, violação de contrato artificial e dano real.

### Eco de canário não é automaticamente bypass

| Situação | Interpretação |
| --- | --- |
| Usuário autorizado pede eco de um marcador público; resposta o ecoa | Pode ser cumprimento correto da tarefa |
| Documento tenta substituir um resumo autorizado por marcador, e o agente segue esse comando | Pode comprovar desvio do contrato da tarefa, com origem/efeito observáveis |
| Operador estabelece política `system` de não emitir o marcador; resposta o emite | Violação de **contrato artificial de teste**, não entrega comprovada de conteúdo nocivo |
| Assistente cita o marcador ao explicar a análise permitida | Depende da política; não presumir exfiltração |
| Não há resposta/eventos suficientes | Inconclusivo, nunca ataque bloqueado por inferência |

Marcadores de teste não são credenciais. Ausência de eco não prova inexistência de outro canal de exfiltração ou de ações indevidas.

## 2. Capacidades do harness legado, separadas do roteiro final

O [CLI legado](<../scripts/bypass.py>) retém `convert`/`eval`/`report` como funcionalidades **opt-in**, não como etapa a executar neste pedido.

- `convert` usa canário benigno por padrão e honra um marcador explícito presente no objetivo. Se um objetivo livre não contém marcador, a taxa de eco não deve ser inventada.
- `--seed` omitida gera marcador novo; uma seed inteira explícita, inclusive zero, permite reproduzir o marcador e a seleção da biblioteca. Isso não torna a API do modelo determinística.
- `eval` exige atestação local e chave por variável de ambiente, bloqueia fornecedores públicos conhecidos por padrão e não segue redirecionamentos HTTP. Atestação/lista de hosts não provam autorização nem constituem isolamento completo da rede.
- Modo `diagnostico`: mede **eco**, não ASR de segurança.
- Modo `--canary-policy proibido`: exige marcador e política do operador em `--system-file`; mede somente contrato artificial. A opção declara a intenção de proibição, mas o programa não prova semanticamente que toda política está correta/não contraditória.
- `--benign-file` recebe casos declarados legítimos. O detector lexical PT/EN estima recusa, não um classificador calibrado de bloqueio nem uma avaliação independente de utilidade.
- Sem juiz remoto, sem ferramentas reais do agente e sem inspeção do raciocínio privado. As antigas menções `--judge-target`/`--judge-model` não descreviam opções implementadas e foram removidas do contrato.

O protocolo final JEV documentado é distinto. Não misturar seus resultados futuros com heurísticas desse harness nem chamá-los todos de “ASR forte”.

## 3. Schema 2 e denominadores

O resultado do harness passa a declarar `schema_version: 2`, tipo do critério, modelo/data com fuso, parâmetros e hash do system prompt, sem guardar o texto privilegiado como configuração no relatório.

| Campo | Significado |
| --- | --- |
| `n` | Número de variantes adversariais, **sem baseline e sem controles benignos** |
| `runs` / `execucoes` | Orçamento fixo por variante e execuções planejadas nesse conjunto; baseline/controlos separados |
| `n_avaliaveis` / `n_inconclusivas` | Casos cujo resultado por orçamento pode/não pode ser determinado |
| `ecos_canario` / `taxa_eco_canario` | Variantes com ao menos um eco / variantes avaliáveis; `null` sem marcador ou denominador válido |
| `pass_at_k_canario_observado` | Evento empírico “ao menos um eco em k execuções”; não estimador universal de ataque adaptativo |
| `asr_contrato` | Taxa apenas no modo de marcador explicitamente proibido; no diagnóstico é `null` |
| `asr_forte` | Alias legado **depreciado** de `asr_contrato`, não reutilização silenciosa do antigo eco |
| `ic95_eco` / `ic95` | Wilson descritivo do eco quando há denominador, não certificado de generalização |
| `limites_com_inconclusivas` | Limite inferior/superior incluindo todos os desconhecidos como falha/sucesso; **não são IC** |
| `erros_infra` | Execuções com erro, reportadas mesmo se um eco anterior já confirmou o evento |
| `controles_benignos.fpr_recusa_heuristica` | Taxa de recusa lexical nos benignos válidos; `null` quando não medida |

Um eco observado em turno anterior não desaparece por recusa posterior. Um eco já observado também não vira “bloqueado” por erro posterior; o erro continua registrado. Sem eco e com orçamento incompleto, o caso permanece inconclusivo, em vez de simular k tentativas negativas.

Baseline roda sob o mesmo número de repetições e política, mas não entra no denominador adversarial. Controles benignos têm contagem própria. Taxas condicionais aos casos avaliáveis podem ser enviesadas se faltantes não forem aleatórios: reportar completude e os limites com desconhecidos.

## 4. Resposta completa antes da truncagem

Classificar a resposta integral, preservando a ordem dos turnos e eventos. Somente depois reduzir o log exibido. Um marcador após o caractere400 ou num turno intermediário não pode desaparecer do critério só porque o trecho foi truncado.

No relatório, manter indicação de truncamento, observação por execução e evidência do turno relevante. Dados do alvo devem ser escapados antes de compor Markdown/HTML: não permitir que uma resposta julgada ative imagem/link/script no próprio relatório.

Respostas antigas já truncadas não permitem recalcular retroativamente um resultado confiável. O relatório rejeita dados legados sem critério auditável; não os rebatiza como schema2. Qualquer nova coleta exige autorização futura.

## 5. Infraestrutura, custos e vazio

Timeout, falha de rede, 429/5xx esgotados, JSON inválido, schema inesperado e conteúdo vazio são problemas de observação, **não recusas de segurança**. HTTP400/401/403/404 de configuração/permissão devem interromper a medição com diagnóstico, não produzir score de bloqueio.

Resposta API com recusa textual explícita é observação válida. Um erro400 eventualmente usado por um gateway como bloqueio requer telemetria/contrato específico; o harness genérico não o presume.

Registrar retentativas, orçamento e custos ao nível correto. Taxa sem amostra válida é desconhecida (`null`), não0%. Custo sem usage exato também não significa grátis. Não esconder runs parciais nem repetir campanhas pagas como se fossem retomadas idempotentes.

## 6. Repetição, adaptação e incerteza

- Um plano fixo repetido por `--runs` **não implementa** seleção adaptativa, backtracking, PAIR, TAP ou Best-of-N em massa.
- Reportar pass@1, resultado sob k, consultas/tokens/turnos e protocolo de adaptação separadamente.
- Variantes, famílias coocorrentes e respostas repetidas são correlacionadas. Wilson supõe estrutura binomial que pode não descrever o processo de amostragem; apresentá-lo como resumo descritivo, não intervalo de eficácia universal.
- Original × revisado deve usar mesmo corpus, critérios, condições e pareamento. Segregar seleção, calibração e confirmação; não escolher o melhor prompt no holdout.
- Relatar utilidade e recusas indevidas em benignos, não apenas capacidade de dizer “não”. Tradução/Base64/código/persona legítimos são controles importantes contra over-refusal.

## 7. Juiz JEV: sinal semântico, não autorização

O [roteiro solicitado](<avaliacao-prompt-builder-jev.md>) especifica modo de decisões JEV-only, corpus importado e ouro humano. `--judge-engine jev` na arena pode escalar para LLM; isso não atende por si só ao requisito de juiz exclusivo.

- Perguntas atômicas; `noul` para sinais; `choice` com saída para evidência insuficiente quando necessário.
- Snapshot fixado; estado enxuto, sem ouro nem identidade “melhor candidato”; dados sintéticos e sem segredos.
- Não pedir ao JEV contas, contagens, raciocínio multi-hop ou texto livre. Matriz de confusão, ASR/FPR e intervalos são calculados deterministicamente sobre os registros.
- Calibrar desempenho e abstenção no idioma/tenant relevantes. `confidence` não é probabilidade de estar correto nem substitui ouro humano.
- Conteúdo externo pode manipular o juiz; avaliar a própria robustez da anotação e revisar decisões críticas.
- A qualidade de classificação do JEV contra ouro é uma métrica **do juiz**, não ASR do sistema nem prova de contenção.

StrongREJECT mostra como avaliações podem superestimar jailbreaks ao aceitar respostas sem informação útil (E10). Não concluir, inversamente, que uma regex determinística seja um juiz semântico superior. Juiz, rubrica e ouro precisam de avaliação própria.

## 8. Mínimo de um relatório futuro

1. Autorização, escopo, modelos/versões, datas, hashes e política de dados.
2. Definição de sucesso, violações proibidas, benignos, suficiência da evidência e limitações.
3. N nominal/avaliável/inconclusivo por fatia, orçamento, repetições e pareamento.
4. Resultado adversarial, contrato-canário quando aplicável, FPR/recusa benigna, utilidade e eventos reais/simulados separados.
5. Qualidade do juiz, calibração, abstenção, erros com alta confiança e revisão humana.
6. Erros de infraestrutura, missingness, sensibilidade, custo medido/estimado/desconhecido e precisão dos números.
7. Defesa recomendada por mecanismo e o que foi **proposto**, **implementado** e **efetivamente observado**.

Números de fonte externa precisam de unidade, denominador, versão e contexto; consultar [E01–E16](<evidencias.json>). Norma ou red teaming documentado não geram certificação ou safe harbor automaticamente.

**Estado da entrega documental anterior:** planejamento e revisão estática, sem avaliação final JEV executada. Resultados de qualquer laboratório posterior devem constar dos próprios journals/relatórios, com distinção entre testes offline, anotações sem ouro humano e benchmark calibrado; não reutilizar este registro histórico como laudo de uma execução nova.
