# Defesa em profundidade para LLMs e agentes (estudo definitivo)

> Compilado do dossiê de pesquisa profunda. Premissa: **guardrails de camada única
> são sempre contornáveis** — a robustez vem da sobreposição de camadas
> independentes, cada uma com métrica publicada e limite conhecido.

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
  orçamento de sessão, escopo de tarefa. Verifique com `bypass.py check` (12 controlos).
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
- **Deriva de tópico:** janelas deslizantes são derrotáveis espalhando o ataque além
  do horizonte [S88]; prefira estado cumulativo com re-scoring amostrado (custo
  quadrático — amortize).
- **Honeypots:** instruções-armadilha no contexto (ex.: "se leres isto, responde
  VIOLAÇÃO") — a sua ativação prova que o contexto foi usado como instrução.
- **Payloads condicionais:** instruções "quando vires X, faz Y" vindas de dados são
  sempre recusadas (MITRE ATLAS AML.T0051.002) [S66].

## 4. Camada de saída (validar antes de entregar/executar)

- **Controlo de egress:** a lição do EchoLeak (CVE-2025-32711, CVSS 9,3) — links
  reference-style + auto-fetch de imagem + proxy Teams transformaram um e-mail em
  canal de exfiltração; sanitize markdown/imagens e restrinja destinos de rede [S48].
- **Validação de esquema e filtros de PII** antes de executar ações ou responder
  (sem métrica pública robusta; trate como requisito de conformidade).
- **Deteção de prompt leaking:** qualquer eco/parafraseia do system prompt é
  violação (protocolo fixo de resposta).
- **Verificação de canário:** o `eval` da skill classifica `canario-ecoado` —
  replique este sinal em produção com canários por sessão.

## 5. Camada de arquitetura (o que sobrevive a um prompt vencido)

| Princípio | Porquê (evidência) |
| --- | --- |
| Menor privilégio por ferramenta/sessão | consenso OpenAI/Anthropic [S63][S64]; MITRE ATLAS: o controlo de maior alavancagem é identidade/autorização [S66] |
| Human-in-the-loop para ações irreversíveis | consenso [S63][S64]; tool poisoning exfiltraria mesmo com prompts perfeitos [S44] |
| Dual-LLM (gerador vs verificador) | Willison: o verificador critica a saída contra a política [S67] |
| Quarantena de conteúdo não confiável | IPI em RAG/ferramentas é o vetor dominante em produção [S43][S44] |
| Segurança de MCP | tool poisoning/shadowing/rug-pulls (CVE-2025-54136) exigem telemetria de raciocínio, enforcement de schemas e pinning de servidores — controlos convencionais (SAST/CI-CD) não apanham, o vetor é DADO [S44][S46] |
| Memória com proveniência | memory poisoning persiste cross-session [S51] |

## 6. Defesas de pesquisa (fronteira, com cautela)

- **Constitutional Classifiers (Anthropic):** ASR 86%→4,4% (~95% bloqueados) em
  Claude 3.5 Sonnet; 1 jailbreak universal no bug bounty público (~3.700 h) — forte,
  não absoluta; por agora é tecnologia do fornecedor [S80].
- **Re-alinhamento pós-quantização (Q-resafe):** recupera segurança degradada pela
  quantização sem perda de utilidade — teste SEMPRE o artefacto quantizado em
  produção, não só o full-precision [S58].

## 7. Mapeamento às normas

- **NIST AI 600-1 (26/7/2024):** perfil do AI RMF para IA generativa — 12 riscos GAI (Confabulation = 2.2; Information Security = 2.9, onde entra a injeção de prompts) com ~212 ações sugeridas por subcategoria RMF; alinha com as camadas D1–D5 [S91][S92].
- **MITRE ATLAS:** AML.T0051 LLM Prompt Injection (.000 Direct, .001 Indirect, .002 Triggered), AML.T0020 Training Data Poisoning, AML.T0070 RAG Poisoning, AML.T0080 AI Agent Context Poisoning, AML.T0115 Publish Poisoned AI Artifacts (v2026.07 renumerou T0019/T0058/T0104 — atenção a citações antigas), jailbreak = AML.T0054 — use como vocabulário de deteção/logs [S66][S97].
- **OWASP Top 10 2025:** LLM01 Prompt Injection ← F7; LLM02 Sensitive Information Disclosure ← exfiltração; LLM04 Data and Model Poisoning ← RAG/MCP poisoning; LLM05 Improper Output Handling ← camada D4; LLM06 Excessive Agency ← tool poisoning/confused deputy; LLM07 System Prompt Leakage ← T303; LLM08 Vector Weaknesses ← RAG poisoning; LLM10 Unbounded Consumption ← Best-of-N orçamento [S96].
