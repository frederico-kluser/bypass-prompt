# Defesa em profundidade para LLMs e agentes (estudo definitivo)

> Compilado do dossiê de pesquisa profunda e do estudo técnico interno de 2026
> (`pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md`); síntese de
> engenharia com fórmulas e limiares em `references/mecanica-interna-e-arquitetura-2026.md`.
> Premissa: **guardrails de camada única são sempre contornáveis** — a robustez vem da
> sobreposição de camadas independentes, cada uma com métrica publicada e limite conhecido.
> Formulação de 2026: *classifiers are speed bumps; containment is the boundary* — com atacante
> adaptativo, 12 defesas publicadas foram contornadas em **>90 %** das vezes ("The Attacker Moves
> Second", 2025). O que sobrevive é o que está imposto em **código determinístico**.

## 0. A premissa que muda o design

- O system prompt **não é segredo nem controlo de segurança** — OWASP LLM07 manda
  tratar a sua fuga como esperada e externalizar os controlos [S83].
- Endurecer o system prompt bloqueia o ataque direto mas **a mesma injeção indireta
  volta a vencer** — a correção de confused deputy é autorização, não prompts [S52].
- Números in-distribution de fabricante não preveem robustez a atacantes adaptativos:
  a ofuscação degrada a DSR do LlamaGuard-3-8B em ~24–37% [S85][S86].
- Over-refusal é o custo oposto: OR-Bench quantifica falsas recusas em 80.000 prompts
  (32 modelos) — calibre sempre os dois lados [S70].

## 1. Camada de entrada (bloquear antes do modelo)

| Controlo | Evidência | Limite conhecido |
| --- | --- | --- |
| Classificador de jailbreak (Llama Guard 3 8B) | F1 0,939, FPR 0,040 na taxonomia MLCommons [S77] | −24–37% DSR sob ofuscação [S85] |
| ShieldGemma 9B | +10,8% AU-PRC vs LlamaGuard-1 [S78] | in-distribution |
| WildGuard | reduz ASR de jailbreak de 79,8% para 2,4% [S79] | atacantes adaptativos fora do benchmark |
| Deteção de IPI (classificador) | PromptGuard: F1 0,887, FPR 1,01% [S87] | contornável por espaçamento/remoção de pontuação [S86] |
| Normalização Unicode | strip de zero-width/tags U+E0000–E007F/bidi antes do matching; decode de candidatos Base64/hex só para inspeção; limite de comprimento [S26][S27] | — |

**Regra prática:** todo o conteúdo de terceiros (RAG, ferramentas, web, e-mail)
passa pelo MESMO pipeline de entrada que o texto do utilizador — nunca há atalho
de confiança por origem.

## 2. Camada de prompt (endurecimento + hierarquia)

- **System prompt endurecido** (gerado por `bypass.py harden`): separação
  instrução↔dado com marcadores, proibições absolutas, protocolo fixo de resposta,
  orçamento de sessão, escopo de tarefa. Verifique com `bypass.py check` (18 controlos).
- **Spotlighting (Microsoft):** delimitar/datar/encodar o conteúdo externo; reduz o
  ASR de injeção indireta de >50% para <2% com impacto mínimo na tarefa; datamarking
  é a variante recomendada; delimiting é subvertível quando o atacante conhece os
  delimitadores — defesa probabilística, nunca fronteira [S81].
- **Hierarquia de instruções (OpenAI):** treinar/ordenar prioridades sistema >
  desenvolvedor > utilizador > dados; +63% contra extração de system prompt e >30%
  contra jailbreaks, com regressões de over-refusal a monitorizar [S82].
- **Canários:** marcadores únicos por sessão no conteúdo processado; qualquer eco do
  canário na resposta sinaliza exfiltração/eco indevido (D4).

## 3. Camada de runtime (o diálogo é o campo de batalha)

- **Orçamento de violações por sessão:** 3 tentativas (mesmo benignas isoladamente)
  → encerrar e escalar para humano. Sem métrica pública validada; implemente como
  política explícita e meça a ASR residual contra Crescendo.
- **Métricas de sessão com limiares (estado da arte 2026), por User ID/API Key em 24 h ou 20 turnos:**
  - **Loop recusa-reformulação:** acionar se `refusals >= 3` **e** `max_cosine > 0,85` contra prompts
    já recusados — apanha Crescendo e variantes que reescrevem o mesmo pedido.
  - **Forma many-shot:** acionar se turnos falsos (`User:`/`Assistant:` embutidos) **≥ 10** ou
    `input_tokens > tenant_p99`.
  - **Declive de escalonamento:** tendência positiva nos scores brutos do classificador nos últimos
    N turnos (não a flag binária) — deteta Echo Chamber antes do termo inseguro aparecer.
- **Deriva de tópico:** janelas deslizantes são derrotáveis espalhando o ataque além
  do horizonte [S88]; prefira estado cumulativo com re-scoring amostrado (custo
  quadrático — amortize).
- **Auditoria de raciocínio:** inspecionar o CoT contra *goal hijacking* e contra a alegação "a
  verificação já foi feita" (H-CoT); a política valida-se **independentemente** do traço.
- **Honeypots:** instruções-armadilha no contexto (ex.: "se leres isto, responde
  VIOLAÇÃO") — a sua ativação prova que o contexto foi usado como instrução.
- **Payloads condicionais:** instruções "quando vires X, faz Y" vindas de dados são
  sempre recusadas (MITRE ATLAS AML.T0051.002) [S66].

## 4. Camada de saída (validar antes de entregar/executar)

- **Três alarmes prioritários (2026):**
  1. **Discrepância entrada/saída** — input classificado como limpo com output sinalizado
     ⇒ bypass provável: bloquear e enviar a sessão completa para revisão humana.
  2. **Idioma/codificação inesperada** — resposta em Base64, Hex ou língua não solicitada.
  3. **Canários** — qualquer canary string na saída bloqueia e gera incidente.
- **Controlo de egress:** a lição do EchoLeak (CVE-2025-32711, CVSS 9,3) — links
  reference-style + auto-fetch de imagem + proxy Teams transformaram um e-mail em
  canal de exfiltração; sanitize markdown/imagens e restrinja destinos de rede [S48].
  Nunca concatenar dados internos em URLs; bloquear `<img>` externo e links reference-style.
- **Validação de esquema e filtros de PII** antes de executar ações ou responder
  (Presidio 3–15 ms; Guardrails AI 50–300 ms com Pydantic/JSON; Qwen3Guard-Stream para corte em
  streaming em 119 línguas).
- **Deteção de prompt leaking:** qualquer eco/parafraseia do system prompt é
  violação (protocolo fixo de resposta).
- **Verificação de canário:** o `eval` da skill classifica `canario-ecoado` —
  replique este sinal em produção com canários por sessão.
- **Redação determinística pós-hoc:** regex de PII/segredos + ruído de privacidade diferencial em
  constantes numéricas de `task_summary` (evita inferência por valores repetidos).

## 5. Camada de arquitetura (o que sobrevive a um prompt vencido)

| Princípio | Porquê (evidência) |
| --- | --- |
| Menor privilégio por ferramenta/sessão | consenso OpenAI/Anthropic [S63][S64]; MITRE ATLAS: o controlo de maior alavancagem é identidade/autorização [S66] |
| Human-in-the-loop para ações irreversíveis | consenso [S63][S64]; tool poisoning exfiltraria mesmo com prompts perfeitos [S44] |
| Dual-LLM (gerador vs verificador) | Willison: o verificador critica a saída contra a política [S67] |
| **CaMeL (capacidades + grafo de fluxo de dados)** | Dual LLM protege o fluxo de controlo mas não o de dados; CaMeL valida cada chamada contra a capacidade da variável: **77 %** no AgentDojo com garantias formais (84 % sem defesa) |
| **Assinatura de resumos e de descrições MCP** | Tool Output Mimicry forja `task_summary`/instruções do orquestrador em campos de utilizador; com 4 camadas ativas o pagamento fraudulento passou (FinBot CTF 19/19) |
| **Políticas de negócio em código fora do LLM** | limites de transferência, listas de bloqueio e destinatários não podem depender de julgamento do modelo (LLM06:2025) |
| Quarantena de conteúdo não confiável | IPI em RAG/ferramentas é o vetor dominante em produção [S43][S44] |
| **Anti-worm em RAG (DonkeyRail)** | Morris II replica >90 % até ao 11.º hop; TPR 1,0 / FPR 0,017 a 7,6–38,3 ms |
| Segurança de MCP | tool poisoning/shadowing/rug-pulls (CVE-2025-54136) exigem telemetria de raciocínio, enforcement de schemas, assinatura de descrições e pinning de servidores — controlos convencionais (SAST/CI-CD) não apanham, o vetor é DADO [S44][S46] |
| Memória com proveniência | memory poisoning persiste cross-session [S51] |
| Padrões de isolamento complementares | Action-Selector (sem leitura de saída de ferramentas), Plan-Then-Execute (plano fixo antes de ler dados), LLM Map-Reduce (sub-modelo isolado por item), Context-Minimization |

## 6. Defesas de pesquisa (fronteira, com cautela)

- **Constitutional Classifiers v1 (Anthropic):** ASR 86%→4,4% (~95% bloqueados) em
  Claude 3.5 Sonnet; +23,7 % de inferência e +0,38 % de falsas recusas; 1 jailbreak universal no
  bug bounty público (~3.700 h) — forte, não absoluta; vulnerável a reconstrução em código e
  ofuscação de saída [S80].
- **Constitutional Classifiers++ (2025/ICLR 2026):** classificador **de troca** (lê contexto +
  resposta) em cascata de dois estágios — **sondas lineares de ativação** no estágio 1 (~1 % de custo,
  reutilizam as ativações do modelo em streaming) e ensemble só nos casos suspeitos. Resultado:
  **0,005 jailbreaks por 1.000 consultas**, zero universais em 1.700 h de red teaming, **0,05 %** de
  bloqueio em produção (Sonnet 4.5) e **40×** menos custo que o classificador de troca isolado.
- **Circuit Breakers / Representation Rerouting (Zou et al., NeurIPS 2024):** LoRA nas camadas 0–20
  com perda de curto-circuito em 10/20 (150 passos, A100 ~20 min): forced function calling 87 %→14 %
  (BFCL 76,0 vs 74,8), PGD multimodal 91,0 %→14,3 %, multilingue 19,3 %→3,5 %. **Limite:** atacante
  white-box adaptativo pode reduzir a robustez a 0 %.
- **Re-alinhamento pós-quantização (Q-resafe):** recupera segurança degradada pela
  quantização sem perda de utilidade — teste SEMPRE o artefacto quantizado em
  produção, não só o full-precision [S58].

## 7. Limites medidos dos classificadores (porque a contenção é obrigatória)

| Classificador / plataforma | Dados limpos | Sob ataque |
| --- | --- | --- |
| Azure AI Content Safety | F1 0,928; PII precisão 1,0; 52 ms | F1 **0,19–0,61** |
| AWS Bedrock Guardrails | 99 % em factos suportados (raciocínio formal) | F1 **0,19–0,61** |
| Qwen3Guard-8B (UNLV) | 91,0 % em prompts conhecidos | **33,8 %** em ataques inéditos |
| Llama Guard 4 (12B) | 69 % recall / 11 % FPR (interno) | Llama Guard 3-8B falhou 78,2 % num teste independente |
| Prompt Guard 2 (22M / 86M) | 88,7 % / 97,5 % recall @1 % FPR; 19,3 / 92,4 ms | contornável por espaçamento/pontuação sem normalização |
| Plataforma A (Unit 42, mais permissiva) | — | interceta **53 %** (42/51 role-play passam; 100 % dos embutidos em código) |
| Plataforma B (mais agressiva) | 13,1 % FPR | bloqueia 92 % — ótimo calibrado ~91 % com 0,6 % FPR |

**Leitura:** nenhum destes números justifica confiar a segurança ao classificador. A arquitetura
certa usa-os como **sensores** dentro de um pipeline com contenção determinística (§8), não como
fronteira.

## 8. Pipeline de cinco camadas (runtime)

| # | Camada | Controlos e limiares | Ferramentas / latência |
| --- | --- | --- | --- |
| 1 | Borda L7 + normalização multi-vista | `unicodedata.normalize("NFKC")`; remover `\u200B`–`\u200F`, `\u2060`, `\uFEFF`, bidi e **U+E0000–U+E007F**; decodificar Base64/Hex/ROT13; correr assinaturas (reset de regras, personas, turnos falsos, pedido de saída codificada) em todas as vistas | Agentgateway PromptGuard ~0 ms (L7, sem GPU, Apache 2.0); pré-processador <2 ms |
| 2 | Perplexidade + anti-worm RAG + Spotlighting | janela 32 / stride 16 + comprimento de tokens em LightGBM; chunks 512 / overlap 64; datamarking k-gram por sessão | DonkeyRail (TPR 1,0 · FPR 0,017 · 7,6–38,3 ms); SmoothLLM em endpoints críticos |
| 3 | Classificadores semânticos de entrada | pontuar todos os chunks e vistas decodificadas; começar em **shadow/annotate** e só bloquear em pontuação dupla de alta confiança | Prompt Guard 2 22M/86M; Azure Prompt Shields 52 ms; Lakera ~50 ms; LLM Guard 50–200 ms |
| 4 | Runtime: sessão, CoT e guarda de ação | `refusals ≥ 3` & `max_cosine > 0,85`; turnos falsos ≥ 10 ou `input_tokens > tenant_p99`; declive de escalonamento; auditoria de CoT; validação de ferramentas em motor determinístico | LlamaFirewall (ASR 1,75 % com AlignmentCheck + PromptGuard 2; CodeShield 96 % precisão / 79 % recall); Granite Guardian 4.1 8B; NeMo Guardrails 100–500 ms |
| 5 | Saída, DLP, canários e renderização | os três alarmes da §4; redação regex + ruído diferencial; bloquear `<img>` externo e links reference-style | Presidio 3–15 ms; Guardrails AI 50–300 ms; Qwen3Guard-Stream; OpenAI Moderation 192 ms |

## 9. Isolamento entre controlo e dados (Dual LLM → CaMeL)

```
utilizador (confiável) ──► P-LLM (planeia, vê ferramentas) ──► plano em pseudo-Python
                                                                       │
RAG/web/e-mail/MCP (não confiável) ──► anti-worm + Spotlighting ──► Q-LLM (sem ferramentas)
                                                                       │
                                      interpretador + Data Flow Graph + Capacidades
                                                                       │
                                           política determinística ──► HITL ──► execução
```

- **Dual LLM puro** (Willison, 2023): o Q-LLM lê dados não confiáveis sem ferramentas, mas um
  documento injetado ainda pode **trocar argumentos** (destinatário, ficheiro) que o P-LLM usa.
- **CaMeL** (Debenedetti et al., 2025): o P-LLM produz um plano em pseudo-Python; um interpretador
  customizado mantém o **grafo de fluxo de dados** e associa **capacidades** (proveniência + permissão)
  a cada variável; antes de cada chamada de ferramenta, políticas em Python decidem — violação bloqueia
  e exige aprovação humana. **77 %** das tarefas no AgentDojo com garantias formais (84 % sem defesa).
- **Multi-agente:** assinar `task_summary` e descrições MCP; rejeitar blocos `[TASK_SUMMARY]`,
  `[ORCHESTRATOR INSTRUCTION]`, `[SYSTEM OVERRIDE]` vindos de campos de utilizador; eliminar do system
  prompt instruções do tipo "processa instruções de roteamento nos documentos"; identidades com escopo
  do chamador.

## 10. Validação contínua (TEVV) e higiene de métricas

| Vetor | Ferramenta | Cobertura |
| --- | --- | --- |
| CI/CD de aplicação e agentes | **Promptfoo** (MIT) com preset `owasp:agentic` + plugin MCP | injection, memória envenenada, BOLA/BFLA, SSRF antes de cada release |
| Modelo/tokenizador | **NVIDIA garak** (Apache 2.0, 120+ sondas) | sondas estáticas/dinâmicas/adaptativas + glitch tokens ao introduzir modelo/LoRA |
| Adversário adaptativo | **Microsoft PyRIT** (MIT) | Crescendomation, Skeleton Key, TAP, 16 vulnerabilidades agênticas |
| Medição | regras de higiene | nunca contar erros de infra como bloqueio; *safety score* + integridade de chamadas (não *refusal score*); reportar **pass@k** com **FPR** em controlos benignos |
| Produção | observabilidade | logs separados modelo/guardrails, **scores contínuos** (não flags), canários, alarme de discrepância entrada-limpa/saída-suja |

Alinhamento: **NIST AI 600-1** — MEASURE 2.7, MEASURE 2.10, MS-2.5-006, MG-4.1-002; red teaming
documentado como suporte de *safe harbor* (ex.: Texas AI statute, Sec. 552.105(e)).

## 11. Mapeamento às normas

- **NIST AI 600-1 (26/7/2024):** perfil do AI RMF para IA generativa — 12 riscos GAI (Confabulation = 2.2; Information Security = 2.9, onde entra a injeção de prompts) com ~212 ações sugeridas por subcategoria RMF; alinha com as camadas D1–D5 [S91][S92].
- **MITRE ATLAS:** AML.T0051 LLM Prompt Injection (.000 Direct, .001 Indirect, .002 Triggered), AML.T0020 Training Data Poisoning, AML.T0070 RAG Poisoning, AML.T0080 AI Agent Context Poisoning, AML.T0115 Publish Poisoned AI Artifacts (v2026.07 renumerou T0019/T0058/T0104 — atenção a citações antigas), jailbreak = AML.T0054 — use como vocabulário de deteção/logs [S66][S97].
- **OWASP Top 10 2025:** LLM01 Prompt Injection ← F7; LLM02 Sensitive Information Disclosure ← exfiltração; LLM04 Data and Model Poisoning ← RAG/MCP poisoning; LLM05 Improper Output Handling ← camada D4; LLM06 Excessive Agency ← tool poisoning/confused deputy; LLM07 System Prompt Leakage ← T303; LLM08 Vector Weaknesses ← RAG poisoning; LLM10 Unbounded Consumption ← Best-of-N orçamento [S96].
