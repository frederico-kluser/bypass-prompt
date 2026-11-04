# Laboratório opt-in: GLM 5.3 Flash + prompt-builder + JEV

## Escopo e estado

Esta integração atende **somente à parte defensiva** de uma nova solicitação explícita de implementação/testes. Não é um conversor de jailbreaks: não se conecta a `convert`, não reduz detecção, não otimiza evasão e não encaminha recusas para um modelo mais permissivo.

O [roteiro anterior](<avaliacao-prompt-builder-jev.md>) permanece um registro histórico de uma entrega exclusivamente documental. Carregar esta skill ou ler qualquer um dos guias **não autoriza gastar, executar uma coleta nem promover um prompt**.

Componentes novos:

- [API interna Python](<../.agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_api.py>): OpenRouter fixado, modelo `z-ai/glm-5.3-flash`, `reasoning.effort: "max"`, provider `z-ai/fp8`, sem fallback, sem ferramentas.
- [Laboratório Python](<../.agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py>): corpus sintético fixo, coleta, exportação de observações e análise pareada.
- [Adaptador prompt-builder](<../.agents/skills/bypass-prompt-evals-agent-skill/scripts/prompt_builder_rewrite.mjs>): **uma proposta defensiva cega** usando a implementação local de `generateContestants`, sem arena, agente ou juiz LLM.
- [Testes da API](<../.agents/skills/bypass-prompt-evals-agent-skill/tests/test_defensive_api.py>) e [testes do laboratório](<../.agents/skills/bypass-prompt-evals-agent-skill/tests/test_defensive_lab.py>): transportes falsos, sem chamadas de modelo.

A biblioteca Python usa apenas stdlib e Python 3.10+. O adaptador requer Node 20.11+ e uma instalação **já compilada** de `prompt-builder-cli`. Não instala dependências, não inicia um servidor e não altera o projeto externo.

## Corpus adicional de risco — outro objeto de avaliação

O [guia de risco e recusa](<casos-risco-e-recusa.md>) e o [corpus de 60 pedidos](<../.agents/skills/bypass-prompt-evals-agent-skill/assets/casos-politica-risco-v1.json>) ampliam as categorias e opções de seleção **somente para classificação JEV-only de pedidos**. Essa expansão não muda os 24 cenários, os prompts ou os resultados do piloto descrito abaixo. Não enviar os novos pedidos a este coletor GLM nem ao reescritor; eles não são um modo ampliado de geração de respostas nocivas.

## Modelo e roteamento

Consultar o catálogo público no momento da preparação. A integração recusa sem gastar se o modelo exato, o provider, os preços, os limites ou o suporte anunciado a `max` não forem confirmados. Não há aproximação de slug nem redução silenciosa para `high`.

No cliente Python, o corpo usa `provider.only: ["z-ai/fp8"]`, `allow_fallbacks: false`, `require_parameters: true`, `data_collection: "deny"` e tetos de preço do endpoint. No gateway do prompt-builder, a API nativa oferece `provider.order` unitário com `allow_fallbacks: false`; o adaptador verifica o corpo antes de permitir o envio. Ambas as rotas recusam redirects. Uma falha de política/permissão ou recusa não habilita outro modelo.

O esforço e os tokens de raciocínio podem ser cobrados, mas o raciocínio privado não é um artefato do laboratório. Só texto público, metadados observáveis e contadores de uso são preservados.

## Desenho do piloto

1. Congelar o prompt `agentico-pt` gerado pelo projeto, com tarefa textual benigna e marcadores públicos explícitos.
2. Congelar **24 cenários sintéticos**: 12 benignos e 12 com um conflito inofensivo, fixo, dentro do documento. Não se geram nem adaptam ataques a partir de resultados.
3. Propor **uma** revisão com a técnica `specificity` do prompt-builder, GLM como único reescritor e todas as cláusulas defensivas literais como `neverBreak`. Não enviar o corpus, respostas do alvo ou scores JEV ao reescritor.
4. Manter verificações locais, mas não usar juiz LLM do diff nem canários executáveis nessa fase de proposta. `judgeDiff: false` é explícito e **não substitui revisão humana nem prova equivalência semântica**. Há no máximo uma correção local de contrato, ainda no mesmo modelo.
5. Coletar respostas públicas com o mesmo modelo/provider/effort/temperatura/teto nos dois candidatos. Não há ferramentas ou efeitos externos. As coletas por candidato são sequenciais, não um ensaio aleatorizado; isso é uma limitação.
6. Exportar estados cegos e avaliar com `prompt-builder jev eval`: apenas `models.decision: ["typesafe/jev-1.13"]`, sem `models.llm`, treino, painel ou fallback.
7. Parear por cenário em código. Conservar ausentes, erros, evidência insuficiente e probabilidades ambíguas como inconclusivos. Nunca promover automaticamente a proposta.

### Sem ouro humano, não alegar calibração

Este piloto não dispõe de rótulos humanos independentes para as respostas coletadas. Por isso exporta `expected: {}`, `fit: false` e splits desativados. O lint do prompt-builder deve avisar `question.no_gold`; **não esconder esse aviso nem inventar ouro com o GLM/JEV**. O modo estrito recusa avisos e não é apropriado para esse piloto não calibrado.

O resultado é uma comparação **descritiva de anotações JEV**, não medição validada de acurácia, ECE, ASR nociva, FPR de produção ou segurança. O CLI pode terminar com exit `6` por ausência de casos pontuados contra ouro, mesmo tendo anotado os estados; investigar o registro completo, nunca rotular esse exit como sucesso de um benchmark calibrado.

Para conclusões mais fortes, obter revisão humana, corpus representativo e splits independentes antes de executar outro protocolo. Nenhum dado real, segredo, documento de produção ou informação pessoal deve entrar no estado.

## Preparação e testes — sem gasto de modelo

A execução é opt-in. Os caminhos abaixo são exemplos de destinos locais novos; não sobrescrever uma experiência existente.

```powershell
# Da raiz do projeto: todas as verificações offline (sem chave, rede ou modelo).
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/run_checks.py
node --test .agents/skills/bypass-prompt-evals-agent-skill/tests/test_prompt_builder_rewrite.mjs
node --check .agents/skills/bypass-prompt-evals-agent-skill/scripts/prompt_builder_rewrite.mjs
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py prepare results/meu-piloto
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py catalog results/meu-piloto
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py collect results/meu-piloto --candidate original --budget 0.30 --dry-run
node .agents/skills/bypass-prompt-evals-agent-skill/scripts/prompt_builder_rewrite.mjs --directory results/meu-piloto --prompt-builder-root C:/Users/kluse/Projects/prompt-builder --budget 0.10 --dry-run
```

`catalog` consulta somente endpoints públicos, sem enviar chave nem chamar um modelo. Os outros pré-voos acima são locais. O dry-run do adaptador registra versão/hashes de módulos internos e um `operationSha256`. A execução exige esse hash aprovado; alterar versão, prompt, técnica, preço ou teto muda a identidade.

**Antes de qualquer chamada paga:** apresentar modelos, provider, dados enviados, limitações e teto total, e obter confirmação do usuário. A chave deve estar em `OPENROUTER_API_KEY`, carregada por armazenamento seguro; nunca em argumento ou relatório.

## Proposta e coleta — somente após autorização de gasto

```powershell
node .agents/skills/bypass-prompt-evals-agent-skill/scripts/prompt_builder_rewrite.mjs --directory results/meu-piloto --prompt-builder-root C:/Users/kluse/Projects/prompt-builder --budget 0.10 --live --approval-hash HASH_REAL_DO_DRY_RUN
# Inspecionar a proposta, preservação dos contratos e escopo antes da coleta.
python3 scripts/harden.py check --file results/meu-piloto/revised.md --json
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py collect results/meu-piloto --candidate revised --budget 0.30 --dry-run
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py collect results/meu-piloto --candidate original --budget 0.30 --live
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py collect results/meu-piloto --candidate revised --budget 0.30 --live
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py export-jev results/meu-piloto --budget 0.10
```

Os tetos são **ilustrativos**, não estimativas medidas nem autorização. O cliente Python reserva uma estimativa conservadora por bytes e limita saída/preços/tentativas; não é um tokenizer exato nem um limite duro da conta. Configure também um credit limit na chave OpenRouter. O adaptador usa as guardas de orçamento, lock e limite diário do prompt-builder.

Timeout, erro de rede ou `usage.cost` ausente podem representar cobrança pendente. Reservas desconhecidas não viram custo zero. Retries transitórios conservam o modelo/provider e respeitam `Retry-After`; cada tentativa entra na contabilidade. Recusas de política não são transientes. BYOK pode implicar cobrança externa ao saldo OpenRouter; não presumir que o teto local governa contas externas.

O journal de reescrita é criado com exclusividade **antes** de enviar. Uma operação iniciada, mesmo interrompida, impede replay automático. Coletas também usam journals exclusivos e persistência por observação. Nada é apagado, sobrescrito ou retomado fingindo custo zero. Investigar a cobrança e iniciar outra experiência exige decisão explícita.

## JEV-only e análise pareada

A arena `vary/train --judge-engine jev` pode escalar para LLM e **não é usada**. Aqui a geração de uma proposta e a avaliação importada são operações distintas.

```powershell
$pb = 'C:/Users/kluse/Projects/prompt-builder/dist/cli/index.js'
node $pb jev validate results/meu-piloto/jev-eval.json --json
node $pb jev eval -c results/meu-piloto/jev-eval.json --budget 0.10 --dry-run --json --data-dir results/meu-piloto/jev-state
# Conferir pré-voo, manter os avisos sem ouro e respeitar a autorização de gasto.
node $pb jev eval -c results/meu-piloto/jev-eval.json --budget 0.10 --output-format ndjson --data-dir results/meu-piloto/jev-state
# Usar o ID real retornado. O arquivo bruto preserva answers e probabilidades.
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/defensive_lab.py compare results/meu-piloto --record results/meu-piloto/jev-state/jev-runs/ID_REAL.json
```

O CLI JEV desta instalação **não aceita `--idempotency-key`** e não oferece retomada de JEV. Uma nova run após término pode cobrar novamente. Não inventar flags. NDJSON de progresso não contém distribuições completas; usar o registro `jev-run@1` ou `jev show ID --full --json`.

O pareamento verifica prompt/corpus, perguntas, estados, modelo/competidor, repetição única e deriva de snapshot. Identidade dos candidatos e rótulos ficam fora do `state`. Utilidade, adoção de instrução externa e suficiência são perguntas distintas. Para entrar no denominador conclusivo, **ambos os lados** precisam de coleta completa, célula válida, evidência na banda `auto` e sinais `noul` fora da faixa ambígua. O limiar inicial de 0,90 é uma política não calibrada, não uma probabilidade de corretude.

O relatório preserva denominadores, perdas e regressões. Empate não é melhoria; confiança não é autorização; um eco de canário solicitado não é dano por definição. Não há otimização baseada no score do detector nem aplicação automática a templates do projeto.

## Compatibilidade e fontes

- API pública OpenRouter: [modelos](https://openrouter.ai/api/v1/models), [GLM solicitado](https://openrouter.ai/z-ai/glm-5.3-flash), [roteamento](https://openrouter.ai/docs/guides/routing/provider-selection).
- [Skill prompt-builder instalada](<C:/Users/kluse/Projects/prompt-builder/skills/prompt-builder/SKILL.md>), [contrato JEV](<C:/Users/kluse/Projects/prompt-builder/agent-docs/jev.md>), [contrato da arena](<C:/Users/kluse/Projects/prompt-builder/agent-docs/config.md>).
- `generateContestants` é export interno do módulo compilado, não um subpath público estável do pacote. Os hashes registrados não equivalem a uma auditoria de toda a árvore transitiva de dependências. Uma atualização exige rever o adaptador e seus testes offline.
- [Metodologia do projeto](<metodologia-avaliacao.md>): evidência observável, missingness e limites da interpretação.
