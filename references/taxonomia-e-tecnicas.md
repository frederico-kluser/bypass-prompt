# Taxonomia de gatilhos e técnicas de bypass de guardrails de LLM (estudo definitivo)

> Compilado do dossiê de pesquisa profunda (`pesquisas/2026-11-04-bypass-guardrails-llm.md`).
> Cada técnica traz: mecanismo causal, evidência quantitativa publicada, deteção e defesa.
> **Nota de honestidade métrica:** ASRs publicadas são frequentemente exageradas [S15];
> juízes LLM concordam com humanos só em 47–78% dos casos em segurança [S74]. Use esta
> taxonomia para TESTAR defesas, não como catálogo de "ataques garantidos".

## 1. Causas-raiz (porque é que jailbreaks existem)

Wei et al. (NeurIPS 2023) reduzem o fenómeno a dois modos de falha do safety
training [S2], adotados como fundamento pelas taxonomias posteriores [S1]:

1. **Competing objectives** — capacidade e segurança são objetivos que conflituam;
   qualquer prompt que amplie a capacidade ("faz tudo") degrada a segurança.
2. **Mismatched generalization** — a segurança generaliza pior que a capacidade:
   contextos novos (personas, ficção, cifras, línguas raras, formatos) saem da
   distribuição em que a recusa foi treinada.

A falha em **separar instrução de dados** é causa transversal nomeada em revisão
sistemática de 128 estudos [S7] e é o mecanismo central das injeções indiretas [S3].

## 2. Taxonomia de gatilhos (7 famílias)

«Guarding the Guardrails» (2025) organiza 50 estratégias em 7 famílias por
mecanismo [S1], que absorvem os 3 tipos de Liu et al. [S4] e cruzam com o eixo
direto/indireto da indústria [S5]:

| # | Família | Mecanismo primário | Técnicas na skill |
| --- | --- | --- | --- |
| F1 | Impersonação/persona | desloca o modelo para fora do "modo assistente" onde a recusa não é acionada | T101–T104 |
| F2 | Persuasão | falácias e apelos convencem o modelo de que é permitido | T201–T204 |
| F3 | Escalonamento de privilégios | instrução alegada de nível superior vence a política | T205, T301–T303 |
| F4 | Sobrecarga cognitiva | dilui/priming/suprime a aplicação das regras | T401–T404 |
| F5 | Ofuscação | codifica a intenção; filtros de superfície não veem, o modelo vê | T501–T509 |
| F6 | Conflito de objetivos | recusa enquadrada como violação de um bem superior | T204, T601* |
| F7 | Dados/indireto (agentic) | instrução chega disfarçada de DADO (RAG, ferramentas, MCP) | T701–T704 |
| F8 | Multi-turno | escalonamento gradual via consistência conversacional | T410–T411 |

\* T601 é absorvida pelas templates de conflito do `convert`; a família model-level
(fine-tuning, quantização, abliteration, CoT hijacking, Best-of-N) não é gerada por
templates — é documentada aqui para o plano de testes e defesas (§5).

Causa-raiz alternativa por construção (PIAtlas, 2026): 6 classes — Instruction
Manipulation, Structural Spoofing, Obfuscation, Social Engineering, Scenario
Framing, Output Coercion — numa hierarquia de 3 níveis (34 técnicas, 131
sub-técnicas) [S3]. Não há convergência entre taxonomias
(>12 eixos incompatíveis) [S3][S8] — esta skill usa mecanismo como eixo primário.

## 3. Técnicas por família (mecanismo → evidência → deteção/defesa)

### F1 — Persona/impersonação

- **Persona sem restrições (DAN):** instruïr o modelo a encarnar um alter-ego sem
  regras e proibir fórmulas de recusa; a recusa fica "fora de personagem". Classe
  dominante em 1.405 prompts in-the-wild de 131 comunidades, com reescrita
  comunitária contínua (o DAN original sobreviveu >240 dias até ser neutralizado)
  [S10][S11]. *Deteção/defesa:* proibição explícita de personas + protocolo de
  resposta fixo (D2); classificador de entrada para padrões de persona.
- **Persona de especialista confiável:** autoridade alegada normaliza o pedido [S10][S12].
- **Modo de manutenção simulado:** cabeçalhos/status fictícios (ticket, aprovação) [S10].
- **Mensagem disfarçada de sistema:** marcadores `<<SYS>>`/`[SYSTEM]` no texto do
  utilizador — testa a separação instrução↔dado e o Spotlighting [S2][S81].

### F2 — Persuasão

- **PAP (Persuasive Adversarial Prompts):** 40 técnicas das ciências sociais; ASR
  >92% em Llama-2-7b Chat, GPT-3.5 e GPT-4 sem otimização especializada; *logical
  appeal* é a técnica mais eficaz e modelos mais avançados são MAIS suscetíveis [S12].
- **Apelo emocional/urgência:** compliance emocional em vez de avaliação de política [S12].
- **Conflito de objetivos (bem maior):** a recusa é enquadrada como violação de um
  objetivo superior; mecanismo documentado como gatilho autónomo [S1][S2].
  *Deteção/defesa:* política com escala explícita ("nenhum enquadramento anula a
  política") + validação semântica de intenção (D2).

### F3 — Escalonamento de privilégios

- **Skeleton Key (acknowledge-then-reframe):** pedir ao modelo que "aumente" (não
  mude) as diretrizes e prefixe conteúdo sensível com aviso em vez de recusar;
  funcionou "fully and without censorship" em 7 modelos (Llama 3, Gemini Pro,
  GPT-3.5/4o, Mistral Large, Claude 3 Opus, Command R+); GPT-4 resiste via input do
  utilizador mas cede via system message — o canal de entrega importa [S13][S14].
- **Credencial de desenvolvedor alegada / invalidação de instruções anteriores:**
  "ignore tudo o que foi dito antes…" + nova constituição [S10][S2].
- **Reconhecimento de prompt de sistema:** pedir eco/parafraseia das instruções —
  primeiro passo de ataques dirigidos; OWASP LLM07: o system prompt **não é
  segredo** nem controlo de segurança [S83]. *Defesa:* protocolo de recusa fixo (D2)
  + deteção de leaking na saída (D4).

### F4 — Sobrecarga cognitiva

- **Many-shot jailbreaking:** N fake-diálogos no contexto; escala de lei de potência
  no nº de shots — ineficaz com 5, consistente com 256 (Claude 2.0) [S35].
  *Defesa:* orçamento de sessão + varrimento do contexto (D3).
- **Diluição de contexto:** volume de texto irrelevante/contraditório degrada a
  aplicação da política [S2][S4].
- **Supressão de recusa (DSN):** proibir o vocabulário de recusa ("no sorry, no I
  cannot") remove a saída habitual; formalizado com unlikelihood loss [S19].
- **Aninhamento hipotético:** ficção/counterfactuals saem da distribuição da
  segurança treinada (mismatched generalization); suites reportam 65–78% [S17][S18].

### F5 — Ofuscação/encoding

| Técnica | Evidência quantitativa | Fonte |
| --- | --- | --- |
| Línguas de baixo recurso | LRL-combined 79,04% vs <1% EN (Zulu 53,1%) | [S21] |
| Cifras in-context (CipherChat) | ASCII ~98% no GPT-4; SelfCipher 99% | [S24] |
| MathPrompt (matemática simbólica) | 73,6% vs ~1% baseline (13 LLMs) | [S25] |
| FigStep (imagem tipográfica) | 82,5% em LVLMs open-source | [S23] |
| ArtPrompt (ASCII art) | média 36% (Gemini 60%) | [S22] |
| Emojis + variation selectors | bypass de guardrails comerciais até 100% (Mindgard); degrada juízes (ShieldLM 71,9→3,5%) | [S28][S29] |
| Unicode tags/zero-width | tokenizer recompõe o payload (Goodside); StegoAttack 92% ASR | [S27][S30] |
| Base64/ROT13/leetspeak | dependente do modelo: decodificação 0–3% em modelos domésticos chineses; payload splitting só no GPT-4-1106 | [S31][S32] |

*Deteção (OWASP/cisco): normalizar e decodificar ANTES do matching — strip de
zero-width/tag chars U+E0000–E007F/bidi, decode de candidatos Base64/hex só para
inspeção, limite de comprimento antes da normalização, pattern-matching YARA [S26][S27].*

### F7 — Dados/indireto/agentic (a família crítica para automação)

- **Tool poisoning em MCP:** instruções escondidas em descrições de ferramentas
  (invisíveis ao utilizador, visíveis ao modelo) fazem o agente ler/exfiltrar
  segredos; benchmark MCPTox em 45+ servidores reais: >60% de sucesso (máx 72,8%);
  rug-pull (mudança de definições pós-aprovação) formalizado como CVE-2025-54136
  (CVSS 8,8) [S44][S46].
- **IPI via output de ferramenta:** GitHub MCP exploited — uma issue em repo público
  instrui o agente a copiar dados de repos privados para um PR público [S44].
- **Exfiltração zero-click:** EchoLeak (CVE-2025-32711, M365 Copilot, CVSS 9,3) — um
  único e-mail → bypass do classificador XPIA → link reference-style → auto-fetch de
  imagem → proxy Teams; corrigido maio 2025 [S48]. ShadowLeak (ChatGPT Deep Research,
  ago 2025): exfiltração 100% server-side sem artefactos locais [S50].
- **Memory poisoning cross-session:** instruções plantadas em memória de longo prazo
  propagam-se a sessões futuras (Gemini/Rehberger 2025; Azure; Bedrock — Unit 42) [S51].
- **Confused deputy:** a IPI separa autenticação de autorização; endurecer o system
  prompt bloqueia o ataque direto mas a mesma injeção indireta volta a vencer — a
  correção é autorização, não prompts [S52].
- **Payloads diferidos/condicionais:** MITRE ATLAS AML.T0051.002 (triggered
  injection); PIAtlas F1.T6.S1 conditional trigger [S3][S66].
- **IPI web em escala:** 15,3K instâncias confirmadas em 11,7K páginas de 1,2B URLs;
  54 templates cobrem 95%; sucesso individual máx 8% (texto simples) e 0,2–1,1% com
  estrutura preservada — o risco é o volume [S43][S5].
- **Multi-agente:** injeção via document poisoning, API response injection, schema
  drift e tool metadata poisoning [S53].
- **Benchmark:** AgentDojo (629 casos) — GPT-4o: utility under attack 50,08%,
  targeted ASR 47,69% [S47].

### F8 — Multi-turno

- **Crescendo:** escalonamento citando as próprias respostas do modelo; ASR média
  56,2% (GPT-4) / 82,6% (Gemini-Pro), binário 98%/100%; 63,2% vs 38,9% do MSJ em
  HarmBench; <10 queries (maioria <5 turnos) [S33].
- **Deceptive Delight:** tópicos sensíveis entre benignos em contexto positivo; ~65%
  em 3 turnos (8000 casos, 8 modelos) [S34].
- **Contra-evidência:** multi-turn automatizado ≈ reamostrar ataques single-turn
  quando se conta o orçamento [S42]; resiliência varia muito por modelo (TAP 44–60%
  em Claude-3-Opus vs 84–94% GPT-4o) [S37][S41].
  *Defesa:* estado de sessão + orçamento de violações + deriva de tópico (D3).

### Automatizadas (para conhecer e para medir; não geradas por templates)

- **PAIR:** atacante LLM itera prompts semânticos, <20 queries [S36].
- **TAP:** árvore de ataques com poda; 85–99% ASR com 10–29 queries [S37].
- **GCG:** otimização por gradiente white-box; 100% Vicuna-7B / 88% Llama-2-7B-Chat;
  transferência fraca a fechados (47,4% GPT-3.5, 2,1% Claude-2), melhorada por
  sufixos universais com supressão da direção de recusa (86% GPT-3.5-Turbo) [S38][S39].
- **AutoDAN-Turbo:** agente lifelong que descobre estratégias; 56,4–57,7% média
  HarmBench; 88,5% no GPT-4-1106 [S40].
- **Best-of-N:** 89% GPT-4o / 78% Claude 3.5 Sonnet com 10.000 amostras
  (ASR(N)=1−(1−p)^N); 52% contra circuit breakers [S60].

### Model-level (fora do prompt)

- **Fine-tuning malicioso:** 10 exemplos (<US$0,20 via API) jailbreakam o GPT-3.5
  Turbo; fine-tuning benigno também degrada o alinhamento [S54].
- **Quantização:** pesos benignos full-precision podem tornar-se maliciosos
  pós-quantização (injeção até 74,7%); Q-Misalign instala misalignment dormente
  ativado só pós-quantização; efeito heterogéneo por método/modelo [S55][S57][S58].
- **Abliteration (refusal direction):** ortogonalização da direção de recusa; em
  Qwen3-14B eleva a ASR de 11% para 91%; receita padrão dos modelos "uncensored" [S62].
- **CoT hijacking (modelos de raciocínio):** padding de raciocínio benigno atinge
  99/94/100/94% ASR em Gemini 2.5 Pro, o4-mini, Grok 3 mini, Claude 4 Sonnet; a ASR
  sobe de 27% para 80% com o comprimento do CoT — diluição do sinal de recusa [S59].
- **Logit/sampling:** manipulação de logits e prefixos forçados aumenta a geração
  nociva [S61].
- **Tokenizer/Unicode:** caracteres invisíveis, homoglifos e glitch tokens exploram a
  lacuna renderizador↔tokenizador; StegoAttack 92% ASR média [S30][S61].

## 4. Armadilhas de medição (leia antes de citar qualquer ASR)

1. **Exageração sistemática:** avaliações independentes (StrongREJECT) mostram que
   ASRs quase-100% raramente se replicam; jailbreaks frequentemente degradam a
   capacidade do modelo [S15].
2. **Juízes LLM pouco fiáveis em segurança:** concordância com humanos 47–78% por
   categoria; o MLCommons trocou LLM-as-judge por classificador determinístico [S74][S75].
3. **Overfitting ao benchmark:** o JailbreakBench bane submissões que usem o próprio
   juiz e publica dataset de calibração [S71].
4. **Over-refusal é o custo oposto:** OR-Bench (80.000 prompts) quantifica falsas
   recusas — endurecer demais custa utilidade [S70].
5. **Dependência de modelo:** a mesma técnica varia muito entre modelos e versões
   (TAP/PAIR em Claude vs GPT; Base64 entre famílias) [S37][S31].

## 5. Mapeamento ataque→defesa (resumo; detalhe em `defesa-em-profundidade.md`)

| Vetor | Defesa primária | Controlo concreto |
| --- | --- | --- |
| Persona/persuasão/privilégio | D2 | system prompt endurecido + hierarquia de instruções (+63% contra extração) [S82] |
| Sobrecarga/many-shot | D3 | orçamento de sessão, varrimento de contexto, estado multi-turno |
| Ofuscação | D1 | normalização Unicode + decodificação pré-matching + classificador robusto a ofuscação (atenção: −24–37% DSR sob ofuscação) [S85] |
| Multi-turno (Crescendo) | D3 | deriva de tópico + orçamento de violações (janela deslizante sozinha é derrotável) [S88] |
| Indireto/MCP/RAG | D5 | Spotlighting (>50%→<2% ASR de IPI) [S81] + menor privilégio + HITL + autorização (confused deputy) [S52] + telemetria de ferramentas [S44] |
| Exfiltração | D4 | controlo de egress, sanitização de markdown/imagem, canários na resposta |
| Model-level | D5/D1 | proveniência de pesos, quantização testada em produção, re-alinhamento pós-quantização |

## Fontes

Ver `pesquisas/2026-11-04-bypass-guardrails-llm.md` §6 ([S1]–[S88]) — cada referência
com URL/DOI, tipo e nível (A–D).
