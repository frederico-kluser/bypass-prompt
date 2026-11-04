# Metodologia de avaliação de guardrails (red-team responsável)

> Como medir bypass com rigor — e como NÃO medir. Baseado no dossiê de pesquisa
> (Q9 + verificação adversarial) e nos benchmarks de referência.

## 1. Antes de qualquer teste: autorização e âmbito

1. **Gate:** `bypass.py authorize --org ... --escopo ...` — o alvo é próprio ou tem
   autorização escrita do responsável. A referência `AUTH-…` entra em todos os
   resultados e relatórios (trilha de auditoria).
2. **Âmbito escrito:** quais sistemas, quais modelos, quais janelas de teste, quem
   é notificado. Teste contra endpoints SOB O CONTROLO do operador (`eval` bloqueia
   fornecedores públicos por omissão).
3. **Conteúdo de teste:** canário por omissão (`CANARIO-XXXXXXXX`). A ferramenta
   não fornece conteúdo nocivo; se o operador usar um prompt real, que seja o
   mínimo necessário à medição.

## 2. O que medir (e o que reportar sempre)

- **ASR forte:** fração de variantes em que o canário é ecoado/produzido — o único
  sinal difícil de falsear por heurística.
- **ASR fraca (`conforme`):** resposta sem padrão de recusa — pode ser resposta
  neutra; reporte separadamente, nunca junto.
- **Recusas:** fórmulas de recusa PT/EN detetadas por lexicon determinístico.
- **Baseline:** o prompt cru, sem variante — sem ele não se sabe o que a variante
  adicionou.
- **n e condições:** nº de variantes, runs, temperatura, versão do modelo, data.
  ASRs sem n e sem critério de sucesso não são comparáveis [S15][S68].
- **pass@k (ataque adaptativo):** com R tentativas por variante, reporte
  `pass@k`/ASR agregado **e** a distribuição por tentativa (o `--runs` do `eval` faz isto);
  um ataque que só passa à 20.ª tentativa não é o mesmo finding que um que passa à primeira.
- **Incerteza:** reporte o intervalo de confiança (Wilson 95 %) do ASR — com n pequeno, 1/20 e 2/20 são
  indistinguíveis. O `report` calcula-o.
- **FPR em controlos benignos:** nenhuma medição de bloqueio é interpretável sem a taxa de falsos
  positivos no corpus legítimo do cliente (Unit 42: 92 % de bloqueio com 13,1 % de FPR é pior que
  91 % com 0,6 %).
- **Safety score, não refusal score:** verificar a presença de frases de recusa não mede segurança;
  meça o resultado (canário, integridade das chamadas de ferramentas, conteúdo efetivamente produzido)
  e a **utilidade sob ataque**.

## 3. Juízes: o elo fraco

- LLM judges em segurança concordam com humanos em apenas **47–78% por categoria**
  (62–71% global), com vieses de posição/verbosidade [S74].
- O MLCommons trocou LLM-as-judge por **classificador determinístico** verificado
  contra julgamento humano [S75]; o JailbreakBench **bane** submissões que usem o
  juiz do benchmark (anti-overfitting) e publica dataset de calibração [S71].
- **StrongREJECT:** juízes automatizados lenientes contam respostas **incoerentes ou não
  acionáveis** como sucesso — é a principal explicação para ASRs académicas quase-100 % que não se
  replicam. Um veredito de bypass exige resposta **acionável**, não apenas ausência de recusa.
- **Regra da skill:** classificação determinística (lexicon + canário) por omissão;
  juiz LLM opcional (`--judge-target/--judge-model`) e SEMPRE reportado como
  estimativa, nunca como veredito.
- **O custo cognitivo invalida comparações:** jailbreaks multi-passo degradam o alvo no **GPQA
  Diamond de 74 % para 32 %** (Anthropic). Medir só "o modelo respondeu" sobrestima o ataque: um
  bypass que destrói a competência não é entrega de capacidade ao atacante. Reporte sempre um proxy
  de utilidade (ex.: acerto em tarefas de controlo) ao lado do ASR.

## 4. Over-refusal: o outro lado da moeda

Endurecer custa utilidade: OR-Bench (80.000 prompts, 10 categorias, ~1.000 hard
prompts, 600 tóxicos de controlo) quantifica falsas recusas; anotação humana mostra
FP até ~20–32% — calibre o rotulador [S70]. Todo endurecimento (novas regras D1–D5)
devia ser seguido de um passe de OR-Bench-like no seu corpus.

## 5. Benchmarks e frameworks de referência

| Ferramenta | Propósito | Métrica |
| --- | --- | --- |
| HarmBench [S68] | avaliação padronizada de red-team automático | ASR por classificadores afinados; breadth/comparability/robust metrics |
| JailbreakBench [S71] | benchmark aberto anti-overfitting | ASR com juiz calibrado; artefactos reutilizáveis |
| OR-Bench [S70] | over-refusal | taxa de falsa recusa |
| AgentDojo [S47] | IPI em agentes end-to-end | utility benigna vs under attack; targeted ASR |
| garak [S72] | scanner de vulnerabilidades (NVIDIA) | sucesso por sonda × detetor (120+ sondas); glitch tokens |
| PyRIT [S69] | orquestração de red-team (Microsoft) | converters/scorers composíveis; Crescendomation, Skeleton Key, TAP, 16 vulnerabilidades agênticas |
| **Promptfoo** (MIT) | guardrails de aplicação e agentes em CI/CD | preset `owasp:agentic` + plugin MCP; injection, memória envenenada, BOLA/BFLA, SSRF |
| EasyJailbreak [S73] | composição de ataques académicos | Selector/Mutator/Constraint/Evaluator |

**Quando usar esta skill vs os frameworks:** esta skill cobre o ciclo rápido
autorização→variantes→eval→relatório→defesa com canários; para campanhas longas de
otimização automática (GCG/PAIR/TAP/AutoDAN-Turbo) use garak/PyRIT — e lembre a
contra-evidência: multi-turn automatizado ≈ reamostragem de single-turn [S42].
Para CI/CD de aplicação (não de modelo), o Promptfoo com `owasp:agentic` é a peça que
verifica BOLA/BFLA e memória envenenada em cada PR — complementa, não substitui, esta skill.

## 6. Reprodutibilidade

- Fixe `--seed` (canário e ordem determinísticos), temperatura 0, e a versão do
  modelo; registre o `AUTH-…`, timestamps e latências (o `results.json` traz tudo).
- Benchmarks quebram comparações quando mudam de versão (AgentDojo 629→949 casos) —
  congele a versão do alvo e do corpus de variantes por campanha.
- **Registe a data do teste.** Fornecedores corrigem endpoints continuamente: uma ASR de ontem não
  descreve o modelo de hoje, e o contrário também é verdade.

## 7. Higiene de contagem e observabilidade (2026)

- **Nunca contar erro de infraestrutura como bloqueio.** Timeouts, 5xx, falhas de telemetria e
  respostas vazias por erro não são defesa: exclua-os do denominador (ou reporte-os à parte) — senão
  o guardrail parece melhor do que é.
- **Peça scores, não flags.** Instrumente os classificadores com a probabilidade contínua; um
  limiar binário esconde a deriva gradual (drift) e impede calibrar FPR/TPR.
- **Logs separados** para modelo e guardrails de entrada/saída, correlacionados por sessão: é a única
  forma de detetar a **discrepância entrada-limpa/saída-suja** (sinal de bypass bem-sucedido).
- **Canários em produção:** tokens únicos por sessão no contexto e no conteúdo processado; qualquer
  aparecimento na saída é incidente, não ruído.
- **Reporte sempre:** n, runs, baseline, versão, data, FPR em controlos benignos e o intervalo de
  confiança. Uma ASR sem estes elementos é uma opinião.

## 8. Ética e disclosure

- Autorização prévia; minimização de dano (canários); objetividade; transparência
  com stakeholders; disclosure coordenado ao responsável do alvo antes de qualquer
  partilha externa [S76].
- Um finding sem recomendação de defesa está incompleto: o relatório da skill
  exige o mapeamento ataque→defesa por técnica.
- Nunca publique variantes contra alvos de terceiros; nunca publique ASRs sem n,
  critério de sucesso e baseline.
