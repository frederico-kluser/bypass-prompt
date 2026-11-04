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

## 3. Juízes: o elo fraco

- LLM judges em segurança concordam com humanos em apenas **47–78% por categoria**
  (62–71% global), com vieses de posição/verbosidade [S74].
- O MLCommons trocou LLM-as-judge por **classificador determinístico** verificado
  contra julgamento humano [S75]; o JailbreakBench **bane** submissões que usem o
  juiz do benchmark (anti-overfitting) e publica dataset de calibração [S71].
- **Regra da skill:** classificação determinística (lexicon + canário) por omissão;
  juiz LLM opcional (`--judge-target/--judge-model`) e SEMPRE reportado como
  estimativa, nunca como veredito.

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
| garak [S72] | scanner de vulnerabilidades (NVIDIA) | sucesso por sonda × detetor |
| PyRIT [S69] | orquestração de red-team (Microsoft) | converters/scorers composíveis |
| EasyJailbreak [S73] | composição de ataques académicos | Selector/Mutator/Constraint/Evaluator |

**Quando usar esta skill vs os frameworks:** esta skill cobre o ciclo rápido
autorização→variantes→eval→relatório→defesa com canários; para campanhas longas de
otimização automática (GCG/PAIR/TAP/AutoDAN-Turbo) use garak/PyRIT — e lembre a
contra-evidência: multi-turn automatizado ≈ reamostragem de single-turn [S42].

## 6. Reprodutibilidade

- Fixe `--seed` (canário e ordem determinísticos), temperatura 0, e a versão do
  modelo; registre o `AUTH-…`, timestamps e latências (o `results.json` traz tudo).
- Benchmarks quebram comparações quando mudam de versão (AgentDojo 629→949 casos) —
  congele a versão do alvo e do corpus de variantes por campanha.

## 7. Ética e disclosure

- Autorização prévia; minimização de dano (canários); objetividade; transparência
  com stakeholders; disclosure coordenado ao responsável do alvo antes de qualquer
  partilha externa [S76].
- Um finding sem recomendação de defesa está incompleto: o relatório da skill
  exige o mapeamento ataque→defesa por técnica.
- Nunca publique variantes contra alvos de terceiros; nunca publique ASRs sem n,
  critério de sucesso e baseline.
