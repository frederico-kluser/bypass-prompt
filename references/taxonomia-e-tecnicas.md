# Taxonomia de gatilhos e técnicas de bypass de guardrails de LLM (estudo definitivo)

> Compilado do dossiê de pesquisa profunda (`pesquisas/2026-11-04-bypass-guardrails-llm.md`)
> e do estudo técnico interno (`pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md`,
> proveniência `owner`); síntese de engenharia em `references/mecanica-interna-e-arquitetura-2026.md`.
> Cada técnica traz: mecanismo causal, evidência quantitativa publicada, deteção e defesa.
> **Nota de honestidade métrica:** ASRs publicadas são frequentemente exageradas — o
> StrongREJECT mostra que juízes lenientes contam respostas incoerentes como sucesso [S15];
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

### 1.1 A recusa é uma direção linear — e é atacável no peso

Arditi et al. (2024), em 13 modelos open-weight, mostraram que a recusa é mediada por uma
**única direção** no fluxo residual, estimável com 128 prompts maliciosos e 128 benignos:

$$\mathbf{r} = \mu_{\text{harmful}} - \mu_{\text{harmless}}, \quad \hat{\mathbf{r}} = \mathbf{r}/\|\mathbf{r}\|$$

- **Ablação direcional** ($\mathbf{x} \leftarrow \mathbf{x} - (\mathbf{x}\cdot\hat{\mathbf{r}})\hat{\mathbf{r}}$)
  anula a recusa no JailbreakBench sem gradiente; preserva MMLU/ARC/GSM8K e regride TruthfulQA.
- **Adição de ativação** ($+\mathbf{r}$) faz recusar pedidos inócuos do Alpaca.
- Sufixos adversariais (GCG) suprimem a propagação de $\hat{\mathbf{r}}$ nas cabeças de atenção.

Consequência para a taxonomia: além das famílias de **prompt**, existe uma classe **model-level**
que não se deteta no texto — só com proveniência de pesos, hash de artefactos e re-teste de
segurança pós-quantização/LoRA. É por isso que `bypass.py taxonomy` distingue técnicas
*convertíveis* de técnicas **documentais** (família `modelo`).

## 2. Taxonomia de gatilhos (7 famílias)

«Guarding the Guardrails» (2025) organiza 50 estratégias em 7 famílias por
mecanismo [S1], que absorvem os 3 tipos de Liu et al. [S4] e cruzam com o eixo
direto/indireto da indústria [S5]:

| # | Família | ASR geral / selec. | Mecanismo primário | Técnicas na skill |
| --- | --- | --- | --- | --- |
| F1 | Impersonação/persona | 14,3 % / 11,3 % | desloca o modelo para fora do "modo assistente" onde a recusa não é acionada | T101–T105 |
| F2 | Persuasão | **17,1 % / 12,5 %** | falácias e apelos convencem o modelo de que é permitido | T201–T204 |
| F3 | Escalonamento de privilégios | 12,5 % / **13,8 %** | instrução alegada de nível superior vence a política | T205, T301–T306 |
| F4 | Sobrecarga cognitiva | 13,7 % / 10,9 % | dilui/priming/suprime a aplicação das regras | T401–T405 |
| F5 | Ofuscação | **7,8 % / 3,2 %** | codifica a intenção; filtros de superfície não veem, o modelo vê | T501–T515 |
| F6 | Conflito de objetivos | 13,2 % / 12,5 % | recusa enquadrada como violação de um bem superior | T204, T601* |
| F7 | Dados/indireto (agentic) | **16,9 % / 14,9 %** | instrução chega disfarçada de DADO (RAG, ferramentas, MCP, agentes) | T701–T706 |
| F8 | Multi-turno | (multi-turno ≥ 60 %) | escalonamento gradual via consistência conversacional | T410–T414 |
| F9 | Raciocínio (CoT) | (recusa < 2 % em o1/o3) | traço falso convence o modelo de que a verificação já passou | T801–T802 |
| — | Modelo (pesos/tokenizer) | — | fine-tuning, quantização, abliteration, glitch tokens | documental (ver §3) |

\* T601 é a template de **ataque composto** (prefixo + supressão de recusa + responsabilidade) do
`convert`; a família `modelo` (fine-tuning,
quantização, abliteration, glitch tokens) **não é gerada por templates** — é documentada aqui para o
plano de testes e defesas (§3 e §5). O ranking ASR é o do estudo de 2026 e inverte a intuição
corrente: **a ofuscação, que concentra os filtros regex, é a família menos eficaz** (3,2 % nas
tarefas selecionadas), enquanto persuasão, envenenamento e impersonação lideram. Ataques eficazes
são **compostos**: ≥ 5 subtécnicas no mesmo prompt.

Causa-raiz alternativa por construção (PIAtlas, 2026): 6 classes — Instruction
Manipulation, Structural Spoofing, Obfuscation, Social Engineering, Scenario
Framing, Output Coercion — numa hierarquia de 3 níveis (34 técnicas, 131
sub-técnicas) [S3]. Não há convergência entre taxonomias
(>12 eixos incompatíveis) [S3][S8] — esta skill usa mecanismo como eixo primário.
Um referencial taxonómico dado ao classificador sobe a deteção de **65,9 % para 78,0 %**
(GPT-5), recuperando 14,3 % de ataques — a taxonomia é ela própria um controlo.

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
- **Persona canónica anti-ética (Dr. House, abr. 2025):** usar um arquétipo de pré-treino que
  rejeita comités de ética ("diagnóstico direto para salvar o paciente") e apresentar o payload como
  "caso clínico urgente"; compilações de red team reportam **85–95 %** de sucesso. *Defesa:*
  proibição nominal de personas + política com escala explícita; `check` verifica "anti-persona".
- **Divisão antagónica (*antagonistic split*):** duas entidades alternam uma palavra de cada vez até
  o texto virar o pedido proibido — explora a coerência do padrão, não a semântica de uma frase.
  *Defesa:* deteção de construção de texto a duas vozes + re-scoring do acumulado.
- **Enquadramentos benignos:** investigação académica, "teste de segurança", cenário de jogo —
  a mesma frase muda de classe consoante o quadro. *Defesa:* classificar intenção, não o quadro.

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
- **Policy Puppetry (HiddenLayer, abr. 2025):** encapsula o pedido numa **política de sistema falsa**
  em XML/JSON/INI, com enquadramento de guião televisivo. Modelos treinados para obedecer a ficheiros
  de configuração tratam-na como diretiva autoritativa; o relatório do fornecedor reporta extração de
  system prompt em GPT-4/4o/o1, Claude 3.5/3.7, Gemini 1.5/2.0, Llama 3/4, DeepSeek, Qwen e Mistral
  (por versão). *Defesa:* anti-mimetismo (ASP/XML/INI falsos são DADO), validação determinística de
  origem e hierarquia de instruções.
- **Involuntary Jailbreak (ago. 2025):** declara que a segurança foi removida por *hardware
  override*, *firmware patch* ou *core dump* forçado — dispensa narrativa longa e apela à obediência
  a um estado de execução privilegiado. *Defesa:* hierarquia de instruções + deteção de "autoridade
  alegada" (nunca há override legítimo fora do plano de controlo).
- **Simulação tipográfica de autoridade:** `[SYSTEM OVERRIDE]`, MAIÚSCULAS, `Access level: ROOT`,
  ticket/aprovação fictícios — explora o viés de obediência hierárquica. *Defesa:* cabeçalhos de
  dados nunca são instruções; assinar/verificar autenticação fora do prompt.

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
- **Decomposição matemática/algebraica:** definir variáveis ("X = 'How to', Y = 'make a', Z =
  'pipe bomb'"), pedir a concatenação e a resposta técnica; o pedido nunca aparece como frase
  classificável. *Defesa:* reassembly/detokenização semântica antes de classificar (D1) e deteção de
  álgebra de variáveis na camada 2.
- **Saturação de contexto / deflection:** milhares de palavras benignas ou um script intermédio
  ("escreve o parser primeiro") deslocam a atenção das restrições para a tarefa lógica. *Defesa:*
  orçamento de tokens por turno + re-scoring do objetivo no fim (D3).
- **Instrução mascarada (TCINS):** pedir "edição de texto" ou "conclusão" de um fragmento onde a
  continuação é o payload; a tarefa declarada é inócua. *Defesa:* classificar a saída e a intenção,
  não a tarefa declarada.

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

Técnicas de ofuscação que a taxonomia de 2026 acrescenta:

- **Unicode Tag Smuggling / ASCII Smuggling:** o bloco **U+E0000–U+E007F** mapeia ASCII
  (U+E0041 = "A"), é invisível em browsers/editores/chat e lido pelo tokenizador (Goodside;
  *ASCII Smuggler* de Rehberger, jan. 2024). Mindgard + workshop de segurança da ACL (2025):
  transformações de caracteres e espaços em branco atingiram **até 100 % de evasão** em seis
  guardrails comerciais, incluindo PromptGuard (Meta) e Azure Prompt Shield.
- **Typoglycemia e homóglifos:** embaralhar letras internas ("ignroe all prevoius systme
  instructions"), cirílico, KaTeX branco (`\color{white}`) — quebra o matching léxico sem quebrar a
  leitura pelo modelo.
- **ASCII Attack (2026):** pedido **totalmente legível** ao lado de glifos ASCII, apresentado como
  "crítica de estilo artístico" — o registo estético muda, o conteúdo não.
- **CodeAttack (Ren et al., 2024):** payload embutido em estruturas de dados de código; >80 % contra
  GPT-4, Claude-2 e Llama-2.
- **Línguas sintéticas:** jogo de língua inventado no próprio diálogo (Peng et al., 2024) — 93 % no
  GPT-4o, sem tradução externa.
- **DrAttack / FlipAttack:** fragmentação em segmentos inócuos remontados na geração / inversão da
  ordem de palavras ou caracteres — a mesma falha de generalização, sem cifra.
- **SM-GCG (2025):** agrega gradientes em cinco espaços (candidato, texto, token, one-hot,
  embedding), somando **+10–15 pp** de ASR sobre GCG em modelos robustos.
- **Best-of-N (Hughes et al., 2024):** N amostras estocásticas simples (capitalização, espaçamento,
  troca de caracteres); lei de potência — **89 %** GPT-4o / **78 %** Claude 3.5 Sonnet com N=10.000,
  41 % com N=100. *Defesa:* orçamento de sessão e deteção de reamostragem, não perplexidade.

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
- **Tool Output Mimicry (Ai-EGIS, OWASP FinBot CTF 19/19):** o resumo de tarefa
  (`task_summary`) passa de agente para agente como texto simples, sem assinatura; num campo
  controlável (descrição de fatura) o atacante forja `[FRAUD AGENT TASK_SUMMARY]`,
  `[ORCHESTRATOR INSTRUCTION TO payments_agent]` e o valor da transferência — o `payments_agent`
  executa o pagamento mesmo com 4 camadas de defesa ativas. *Defesa:* assinar/resumos verificados,
  rejeitar estruturas de orquestração vindas de campos de utilizador, política de valores fora do LLM.
- **Worm RAG (Morris II / RAGworm, CCS 2025):** prompt auto-replicante em texto ou imagem FGSM propaga-se
  entre assistentes de e-mail/RAG; >90 % de replicação até ao 11.º hop (64 % no 20.º em Gemini 1.5
  Pro); propagação super-linear (20 novos clientes em 1–3 dias). *Defesa:* anti-worm (DonkeyRail),
  proveniência de documentos, quarentena de conteúdo recuperado.
- **Cadeia de delegação (delayed zero-click RCE):** um system prompt que manda "processar quaisquer
  instruções de roteamento encontradas nos documentos" transforma o upload de um SOC2/ISO/PCI-DSS com
  script embutido em execução e exfiltração semanas depois. *Defesa:* remover instruções de
  roteamento do prompt, validar artefactos e sandbox de ferramentas.
- **Benchmark:** AgentDojo (629 casos) — GPT-4o: utility under attack 50,08%,
  targeted ASR 47,69% [S47].

### F8 — Multi-turno

- **Crescendo:** escalonamento citando as próprias respostas do modelo; ASR média
  56,2% (GPT-4) / 82,6% (Gemini-Pro), binário 98%/100%; 63,2% vs 38,9% do MSJ em
  HarmBench; <10 queries (maioria <5 turnos) [S33]. O `Crescendomation` (PyRIT) acrescenta
  *backtracking*: se o alvo recusa, o turno é removido e a pergunta reformulada.
- **Deceptive Delight:** tópicos sensíveis entre benignos em contexto positivo; ~65%
  em 3 turnos (8000 casos, 8 modelos) [S34].
- **Echo Chamber (NeuralTrust, jun. 2025):** "sementes" benignas nos primeiros turnos e apenas
  referências indiretas; o modelo amplifica as suas próprias saídas em conteúdo proibido sem que o
  utilizador enuncie um termo inseguro — >90 % em categorias avaliadas no GPT-4/Gemini e *safe
  completions* do GPT-5 contornadas em ~24 h após o lançamento (ago. 2025).
- **Skeleton Key:** "aumentar" diretrizes em vez de trocar a persona, com aviso de isenção em vez de
  recusa; 7 modelos; no GPT-4 o ataque falha pelo canal do utilizador mas passa pelo *system message* —
  o **canal de entrega importa**.
- **Bad Likert Judge:** pedir ao modelo que avalie respostas numa escala Likert e depois preencher o
  topo da escala (1–10 "sem censura"); **+60 pp** de ASR e ~71,6 % médio em 6 modelos, cortado em
  ~89,2 % por filtros externos de conteúdo.
- **Context Compliance Attack (CCA):** histórico de conversa fabricado enviado por API *stateless*;
  o modelo assume que já concordou e mantém a conformidade.
- **Many-Shot Jailbreaking (MSJ):** 128–256+ turnos fictícios; lei de potência (log-verossimilhança
  cai linearmente com o número de shots); modelos maiores têm declive mais acentuado e o ajuste fino
  de alinhamento desloca o intercepto, **não** o expoente.
- **Contra-evidência:** multi-turn automatizado ≈ reamostrar ataques single-turn
  quando se conta o orçamento [S42]; resiliência varia muito por modelo (TAP 44–60%
  em Claude-3-Opus vs 84–94% GPT-4o) [S37][S41].
  *Defesa:* estado de sessão + orçamento de violações + deriva de tópico (D3).

### F9 — Sequestro de raciocínio (modelos CoT)

- **H-CoT (Hijacking the Chain-of-Thought, Duke/CMU 2025, arXiv:2502.12893):** injeta no contexto um
  traço de raciocínio falso na "fase de execução", convencendo o modelo de que a verificação de
  segurança **já foi feita e aprovada**; recusa dos modelos o1/o3 cai para **<2 %** no
  Malicious-Educator. Modelos que expõem o CoT (DeepSeek-R1) são estruturalmente mais exploráveis.
- **CoT padding benigno:** raciocínio longo e inócuo dilui o sinal de recusa (ASR 27 %→80 % com o
  comprimento do CoT; 99/94/100/94 % em Gemini 2.5 Pro, o4-mini, Grok 3 mini, Claude 4 Sonnet).
- *Defesa:* validar a política **independentemente** do traço (nunca confiar em "já verificado"),
  anti-H-CoT no prompt, auditoria de CoT (LlamaFirewall/AlignmentCheck) e circuit breakers.

### Automatizadas (para conhecer e para medir; não geradas por templates)

- **PAIR:** atacante LLM itera prompts semânticos, <20 queries [S36].
- **TAP:** árvore de ataques com poda; 85–99% ASR com 10–29 queries [S37]; v3: 90 % GPT-4,
  84 % GPT-4-Turbo, 76 % GPT-3.5-Turbo, 60 % Claude-3-Opus.
- **GCG:** otimização por gradiente white-box; 100% Vicuna-7B / 88% Llama-2-7B-Chat;
  transferência fraca a fechados (47,4% GPT-3.5, 2,1% Claude-2), melhorada por
  sufixos universais com supressão da direção de recusa (86% GPT-3.5-Turbo) [S38][S39].
- **I-GCG (Jia et al., 2024):** templates de alvo diversificados + atualização multi-coordenada;
  converge em ~400 passos com 100 % em Vicuna-7B, Guanaco-7B, Llama-2-7B-Chat e Mistral-7B
  (transferência 22–26 % para GPT-3.5).
- **SM-GCG (Gu et al., 2025):** cinco espaços de transformação; +10–15 pp sobre GCG.
- **AutoDAN-Turbo:** agente lifelong que descobre estratégias; 56,4–57,7% média
  HarmBench; 88,5% no GPT-4-1106 [S40].
- **Best-of-N:** 89% GPT-4o / 78% Claude 3.5 Sonnet com 10.000 amostras
  (ASR(N)=1−(1−p)^N); 52% contra circuit breakers [S60].
- **PAP (Zeng et al., ACL 2024):** *paraphraser* persuasivo sobre 40 técnicas; 92 % em
  Llama-2-7B/GPT-3.5/GPT-4 em 3 tentativas e 60 % no GPT-4 contra a defesa adaptativa mais forte.

### Model-level (fora do prompt)

- **Fine-tuning malicioso:** 10 exemplos (<US$0,20 via API) jailbreakam o GPT-3.5
  Turbo; **fine-tuning 100 % benigno** (Dolly, p = 0) também induz deriva de *embeddings* ocultos e
  degrada a recusa — a regressão de segurança não exige dados maliciosos [S54].
- **Quantização:** pesos benignos full-precision podem tornar-se maliciosos
  pós-quantização (injeção até 74,7%); Q-Misalign instala misalignment dormente
  ativado só pós-quantização; efeito heterogéneo por método/modelo [S55][S57][S58].
- **Abliteration (refusal direction):** ortogonalização da direção de recusa; em
  Qwen3-14B eleva a ASR de 11% para 91%; receita padrão dos modelos "uncensored" [S62].
- **CoT hijacking (modelos de raciocínio):** ver F9 — H-CoT reduz recusa a <2 % em o1/o3;
  padding de raciocínio atinge 99/94/100/94% ASR em Gemini 2.5 Pro, o4-mini, Grok 3 mini,
  Claude 4 Sonnet; a ASR sobe de 27% para 80% com o comprimento do CoT [S59].
- **Glitch tokens (Land & Bartolo, EMNLP 2024):** tokens do vocabulário BPE quase ausentes do treino
  (2 % menos frequentes; norma $L_2(E_{in})$ / cosseno $C(E_{out},u_{ref})$; ex. pontuação com `\r`,
  fragmentos como `FFIRMED`) provocam alucinação, saída ilegível ou falha imprevisível de segurança.
  *Controlo:* varrer o tokenizador ao introduzir modelo/LoRA.
- **Logit/sampling:** manipulação de logits e prefixos forçados aumenta a geração
  nociva [S61].
- **Tokenizer/Unicode:** caracteres invisíveis, homoglifos e glitch tokens exploram a
  lacuna renderizador↔tokenizador; StegoAttack 92% ASR média [S30][S61].

## 4. Armadilhas de medição (leia antes de citar qualquer ASR)

1. **Exageração sistemática:** avaliações independentes (StrongREJECT) mostram que
   ASRs quase-100% raramente se replicam; juízes lenientes contam respostas incoerentes ou não
   acionáveis como sucesso; jailbreaks frequentemente degradam a
   capacidade do modelo [S15].
2. **Juízes LLM pouco fiáveis em segurança:** concordância com humanos 47–78% por
   categoria; o MLCommons trocou LLM-as-judge por classificador determinístico [S74][S75].
3. **Overfitting ao benchmark:** o JailbreakBench bane submissões que usem o próprio
   juiz e publica dataset de calibração [S71].
4. **Over-refusal é o custo oposto:** OR-Bench (80.000 prompts) quantifica falsas
   recusas — endurecer demais custa utilidade [S70].
5. **Dependência de modelo e data:** a mesma técnica varia muito entre modelos e versões
   (TAP/PAIR em Claude vs GPT; Base64 entre famílias) [S37][S31]; endpoints hospedados recebem
   correções contínuas — **cite versão e data** em qualquer ASR.
6. **Custo cognitivo do ataque:** jailbreaks multi-passo degradam o desempenho do alvo no
   **GPQA Diamond de 74 % para 32 %** (red teaming Anthropic). Um bypass que inutiliza o modelo não
   é o mesmo finding que um bypass que preserva utilidade: meça **utilidade sob ataque**.
7. **Higiene de contagem:** nunca contabilizar erros de infraestrutura, timeouts ou falhas de
   telemetria como ataques bloqueados; reportar **pass@k** (sob ataque adaptativo) junto com
   **FPR** em controlos benignos.

## 5. Mapeamento ataque→defesa (resumo; detalhe em `defesa-em-profundidade.md`)

| Vetor | Defesa primária | Controlo concreto |
| --- | --- | --- |
| Persona/persuasão/privilégio | D2 | system prompt endurecido + hierarquia de instruções (+63% contra extração) [S82] |
| Policy Puppetry / autoridade tipográfica | D2 + D5 | anti-mimetismo (XML/JSON/INI falsos são DADO) + validação determinística de origem + assinatura de planos |
| Sobrecarga/many-shot | D3 | orçamento de sessão, varrimento de contexto, estado multi-turno, `input_tokens > tenant_p99` |
| Ofuscação | D1 | NFKC + strip de U+E0000–U+E007F/zero-width/bidi + decodificação pré-matching + classificador robusto (atenção: −24–37% DSR) [S85] |
| Unicode tag smuggling / typoglycemia | D1 | normalização canónica **antes** do matching; inspeção multi-vista (100 % de evasão em 6 guardrails sem ela) |
| Multi-turno (Crescendo/Echo Chamber) | D3 | deriva de tópico + orçamento de violações (janela deslizante sozinha é derrotável) [S88] + `refusals ≥ 3` & `max_cosine > 0,85` |
| Bad Likert Judge | D2 + D4 | proibir geração de exemplos nocivos em rubricas/avaliações; classificar a saída |
| H-CoT / CoT padding | D2 + D3 | anti-H-CoT (nunca confiar em "já verificado") + auditoria de CoT + sonda de ativação (CC++) |
| Indireto/MCP/RAG | D5 | Spotlighting (>50%→<2% ASR de IPI) [S81] + datamarking k-gram + menor privilégio + HITL + autorização (confused deputy) [S52] + telemetria de ferramentas [S44] |
| Tool Output Mimicry / multi-agente | D5 | assinar `task_summary` e descrições MCP; rejeitar cabeçalhos de orquestração vindos de campos de utilizador; políticas críticas em código |
| Worm RAG (Morris II) | D5 | anti-worm (DonkeyRail: TPR 1,0 / FPR 0,017) + proveniência + quarentena |
| Exfiltração | D4 | controlo de egress, sanitização de markdown/imagem, canários na resposta, alarme de discrepância entrada-limpa/saída-suja |
| Model-level | D5/D1 | proveniência de pesos/adaptadores, hash de artefactos, quantização testada em produção, re-alinhamento pós-quantização, varrimento de glitch tokens |
| Sessão | D3/D5 | circuit breaker determinístico + motor de políticas com capacidades (CaMeL) + HITL |

## Fontes

- `pesquisas/2026-11-04-bypass-guardrails-llm.md` §6 ([S1]–[S88]) — cada referência
  com URL/DOI, tipo e nível (A–D).
- `pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md` — estudo interno
  (`owner`) com as métricas de 2026 (ASR por família, CC++, CaMeL, EchoLeak, Morris II, H-CoT,
  pipeline de 5 camadas) e o apêndice de referências primárias.
- `references/mecanica-interna-e-arquitetura-2026.md` — síntese de engenharia (fórmulas,
  limiares, tabelas de decisão).
