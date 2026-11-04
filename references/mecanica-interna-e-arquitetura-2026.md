# Mecânica interna, contenção e arquitetura de defesa (estado da arte 2026)

> Destilado do estudo técnico `pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md`
> (fonte `owner`) e cruzado com o dossiê `pesquisas/2026-11-04-bypass-guardrails-llm.md` ([S#]).
> **Premissa operacional:** classificadores são redutores de velocidade; a contenção
> determinística é a fronteira. Nenhuma métrica aqui é garantia — cada número tem versão de
> modelo e data associadas.

## 1. Porque é que um modelo alinhado recusa (e porque deixa de recusar)

### 1.1 Dois modos de falha

| Modo | Definição | Consequência prática |
| --- | --- | --- |
| **Objetivos concorrentes** (Wei et al., 2023) | Utilidade, completação de padrões e obediência ao formato entram em atrito com a política de segurança | Prefix injection, supressão de recusa, "começa a resposta com «Claro…»" funcionam porque penalizam os tokens de recusa |
| **Generalização desalinhada** (Wei et al., 2023) | A capacidade generaliza para cifras, código, LRL e ficção; o treino de segurança não | Modelos maiores são **mais** exploráveis por ofuscação/persuasão (paradoxo da capacidade) |

A falha transversal é a **ausência de fronteira de confiança**: system prompt (control plane) e
dados (data plane) viajam na mesma sequência de tokens — o equivalente a sinalização *in-band*
numa linha telefónica (Hines et al., 2024). Daí OWASP LLM01–LLM08:2025 e MITRE ATLAS
AML.T0051.000/.001, T0054, T0056, T0057.

### 1.2 A direção de recusa é linear e causal

Arditi et al. (2024), 13 modelos open-weight:

$$\mathbf{r} = \mu_{\text{harmful}} - \mu_{\text{harmless}}, \qquad \hat{\mathbf{r}} = \mathbf{r}/\|\mathbf{r}\|$$

estimado numa camada intermédia e posição pós-instrução com apenas **128 + 128** prompts.

**Ablação direcional (abliteration)** — remove a componente da recusa em todas as camadas/posições:

$$\mathbf{x} \leftarrow \mathbf{x} - (\mathbf{x}\cdot\hat{\mathbf{r}})\,\hat{\mathbf{r}}$$

- Anula a recusa no **JailbreakBench** sem ajuste fino por gradiente.
- Preserva MMLU, ARC e GSM8K; regride **TruthfulQA** (a direção sobrepõe-se a desinformação).
- **Adição de ativação** (somar $\mathbf{r}$) faz o modelo recusar pedidos inócuos do Alpaca.
- Sufixos adversariais suprimem mecanicamente a propagação de $\hat{\mathbf{r}}$ nas cabeças de atenção.

**Implicação de defesa:** segurança não é um "filtro" externo ao modelo; é uma direção no fluxo
residual. Modelos com pesos abertos podem ser "abliterados"; portanto **proveniência de pesos,
hash de artefactos e re-teste pós-quantização/LoRA** são controlos de supply chain, não burocracia.
Para modelos fechados, o equivalente defensivo é a sonda de ativação interna (CC++, §3.3).

## 2. Anatomia dos vetores (o que a defesa tem de intercetar)

### 2.1 Sete famílias de mecanismo — ASR empírica (Guarding the Guardrails, 2025–2026)

| Família | ASR geral | ASR tarefas selecionadas | Sinal de deteção primário |
| --- | --- | --- | --- |
| Impersonação / cenários ficcionais | 14,3 % | 11,3 % | persona, "divisão antagónica", enquadramento académico/jogo |
| Escalonamento de privilégios | 12,5 % | 13,8 % | `[SYSTEM OVERRIDE]`, root/debug, política falsa em XML/JSON/INI |
| Persuasão | **17,1 %** | 12,5 % | autoridade normativa, urgência, reciprocidade, coerção |
| Sobrecarga cognitiva | 13,7 % | 10,9 % | decomposição X+Y+Z, distratores, saturação de contexto |
| Codificação / ofuscação | 7,8 % | **3,2 %** | invisible chars, Base64, homóglifos, ASCII art, LRL |
| Conflito de objetivos | 13,2 % | 12,5 % | prefixo afirmativo obrigatório, proibição de recusa |
| Envenenamento de dados | 16,9 % | **14,9 %** | histórico fabricado, many-shot, RAG/tool poisoning |

Leituras que mudam prioridades:

1. **Ofuscação é a família menos eficaz** (3,2 % nas tarefas selecionadas) apesar de concentrar a
   atenção dos filtros regex — o esforço defensivo está mal alocado.
2. **Persuasão, envenenamento e impersonação** lideram; a impersonação está em **51 %** dos
   prompts analisados pela SilentForce, com 15,1 % de sucesso.
3. **Ataques compostos** (≥ 5 subtécnicas no mesmo prompt) são a forma dominante dos jailbreaks
   eficazes.
4. Um referencial taxonómico no contexto do classificador sobe a deteção de **65,9 % → 78,0 %**
   (GPT-5), recuperando 14,3 % de ataques que passariam — a taxonomia é ela própria um controlo.

### 2.2 Eficácia por classe de ataque (com a ressalva de versão)

| Classe | ASR observada | Nota |
| --- | --- | --- |
| Pedido direto sem técnica | 1,9 % (selecionadas) / 6,1 % (geral) | baseline de referência |
| Estratégia estruturada de turno único | 13,9 % – 27,0 % | intervalo de avaliações padronizadas |
| Multi-turno / persuasivo / amostragem / CoT | 60 % – >95 % | Crescendo, Bad Likert, Echo Chamber, PAP, H-CoT |
| Guardrail de saída isolado (sem alinhamento) | interceta < 2 % | não é camada de segurança |

### 2.3 Técnicas que a taxonomia de 2026 acrescenta (e o que testam)

| Técnica | Mecanismo | Números publicados | Defesa que a trava |
| --- | --- | --- | --- |
| **Policy Puppetry** (HiddenLayer, abr. 2025) | Política de sistema falsa em XML/JSON/INI + guião TV; o modelo obedece a "config" | system prompt extraído em GPT-4/4o/o1, Claude 3.5/3.7, Gemini 1.5/2.0, Llama 3/4, DeepSeek, Qwen, Mistral (por versão) | anti-mimetismo no prompt + validação determinística de origem |
| **Dr. House** (abr. 2025) | Persona canónica anti-ética (rejeita comités de ética) + "caso clínico urgente" | 85–95 % em compilações de red team | anti-persona + política com escala explícita |
| **Involuntary Jailbreak** (ago. 2025) | Declara remoção de segurança por override de hardware/firmware | conformidade direta sem narrativa | hierarquia de instruções + deteção de autoridade alegada |
| **Unicode Tag Smuggling** (Goodside; ASCII Smuggler, jan. 2024) | U+E0000–U+E007F mapeiam ASCII, invisíveis no ecrã, lidos pelo tokenizer | evasão até 100 % contra 6 guardrails (Mindgard + ACL 2025) | NFKC + strip de tags/zero-width/bidi + inspeção multi-vista |
| **Typoglycemia / homóglifos** | embaralhar letras internas / cirílico | idem (até 100 % contra PromptGuard/Azure Prompt Shield) | normalização + classificador robusto a ruído |
| **ArtPrompt** (ACL 2024) | palavra-chave em arte ASCII | 36 % média (Gemini 60 %) | decodificação/visão do artefacto antes do matching |
| **ASCII Attack** (2026) | pedido legível + glifos, "crítica de estilo artístico" | — | proibir crítica estética de arte ASCII no prompt |
| **CipherChat / SelfCipher** (2024) | cifra ensinada no contexto | quase total no GPT-4 | inspeção multi-vista + proibição de cifra não autorizada |
| **Jogos de língua sintética** (2024) | língua inventada no diálogo | 93 % GPT-4o | deteção de deriva linguística |
| **LRL** (Yong et al., 2023) | zulu, gaélico, hmong, guarani | <1 % EN → 79 % GPT-4 | re-verificação semântica na língua de origem |
| **CodeAttack** (Ren et al., 2024) | payload em estruturas de código | >80 % GPT-4/Claude-2/Llama-2 | análise de artefactos de código |
| **DrAttack / FlipAttack** | fragmentação + remontagem / inversão | — | reassembly antes de classificar |
| **I-GCG** (2024) | multi-coordenada + templates | ~400 passos, 100 % em Vicuna/Guanaco/Llama-2/Mistral | perplexidade + auditoria de saída |
| **SM-GCG** (2025) | gradiente em 5 espaços | +10–15 pp sobre GCG | perplexidade + circuit breaker |
| **Best-of-N** (2024) | amostragem estocástica em massa | 89 % GPT-4o / 78 % Claude 3.5 (N=10.000); 41 % (N=100) | orçamento de sessão + deteção de reamostragem |
| **PAP** (ACL 2024) | paráfrase persuasiva (40 técnicas) | 92 % em 3 tentativas; 60 % GPT-4 vs melhor defesa adaptativa | classificador de intenção + política imune a enquadramento |
| **Crescendo** (USENIX 2024/25) | escalonamento citando as próprias respostas | 63,2 % ASR / 91 % cobertura HarmBench; <5 turnos | estado de sessão + orçamento de violações |
| **Echo Chamber** (NeuralTrust, 2025) | amplificação das próprias saídas, sem termo inseguro | >90 % em GPT-4/Gemini; GPT-5 safe completions em ~24 h | deteção de deriva semântica + revisor humano |
| **Skeleton Key** (MSRC, 2024) | "aumentar" diretrizes + disclaimer | 7 modelos; GPT-4 cede via system message | anti-Skeleton Key + canal de entrega autenticado |
| **Deceptive Delight** (Unit 42, 2024) | sanduíche de distração em 3 turnos | ~65 % | estado multi-turno + tópico sensível isolado |
| **Bad Likert Judge** (Unit 42, 2024/25) | o modelo avalia respostas e preenche o topo da escala | +60 pp; ~71,6 % em 6 modelos; filtros externos cortam ~89,2 % | proibir geração de exemplos nocivos em rubricas |
| **CCA** (MSRC, 2025) | histórico fabricado em APIs stateless | — | proveniência/assinatura do histórico; estado no servidor |
| **MSJ** (Anthropic, NeurIPS 2024) | 128–256+ shots no contexto | lei de potência; slope maior em modelos maiores | orçamento de tokens + deteção de turnos falsos |
| **H-CoT** (Duke/CMU, 2025) | traço de raciocínio falso "já verificado" | recusa <2 % em o1/o3 (Malicious-Educator) | anti-H-CoT + verificação independente de política |
| **EchoLeak** (CVE-2025-32711) | e-mail → XPIA bypass → markdown reference-style → imagem → proxy Teams | CVSS 9,3, zero-click | sanitização de markdown/imagem + controlo de egress |
| **Morris II / RAGworm** (CCS 2025) | worm auto-replicante em RAG (texto ou imagem FGSM) | >90 % até ao 11.º hop; 64 % no 20.º | DonkeyRail + proveniência + quarentena |
| **Tool Output Mimicry** (Ai-EGIS, FinBot CTF 19/19) | falsifica `task_summary`/instrução do orquestrador num campo de utilizador | pagamento fraudulento com 4 camadas ativas | assinatura criptográfica de resumos + política determinística |
| **MCP tool poisoning** | descrição de ferramenta alterada lê-se como sistema | — | assinar descrições, read-only em produção, rug-pull pinning |
| **Delegação (delayed zero-click RCE)** | system prompt manda "processar instruções nos documentos" | execução semanas depois | remover instruções de roteamento do prompt + sandbox de ferramentas |
| **Fine-tuning / LoRA** (Qi et al., ICLR 2024) | 100 exemplos maliciosos, ou dataset 100 % benigno | Shadow Alignment; deriva de embeddings mesmo com p=0 | proveniência de adaptadores + re-teste de segurança |
| **Glitch tokens** (Land & Bartolo, EMNLP 2024) | tokens sub-treinados (2 % menos frequentes) | alucinação/falha imprevisível | varrimento de tokenizer ao introduzir modelo |

### 2.4 As três ressalvas que invalidam leituras ingénuas de ASR

1. **Versão + data.** Toda a ASR está presa à versão do modelo e à data; correções contínuas
   nos endpoints movem os números.
2. **StrongREJECT.** Juízes automatizados lenientes contam respostas incoerentes ou não
   acionáveis como sucesso → ASRs académicas sistematicamente sobreavaliadas.
3. **Custo cognitivo.** Jailbreaks multi-passo degradam o desempenho no **GPQA Diamond de 74 %
   para 32 %** (red teaming Anthropic): o ataque "funciona" e o modelo fica inútil para a tarefa.
   Meça sempre **utilidade sob ataque**, não só recusa.

## 3. Defesa: quatro controlos de modelo + pipeline de cinco camadas

### 3.1 Instruction Hierarchy (Wallace et al., OpenAI 2024)

Sistema > developer > utilizador > dados/ferramentas, treinado com *Context Synthesis* (instruções
alinhadas) e *Context Ignorance* (conflituantes).

| Métrica | Antes | Depois |
| --- | --- | --- |
| Robustez global (GPT-3.5) | — | **+63 %** |
| Extração de system prompt (TensorTrust) | 32,8 % | **95,9 %** resistente |
| Jailbreaks não vistos no treino | 37,4 % | **71,2 %** |
| Conformidade em sondagens benignas (over-refusal) | 85,2 % | 75,0 % |

O custo é over-refusal: meça-o com OR-Bench-like antes de subir a regra.

### 3.2 Spotlighting dinâmico (Hines et al., Microsoft 2024)

| Variante | ASR de IPI | Robustez ao atacante que conhece o formato |
| --- | --- | --- |
| Delimitação estática | ~metade do baseline | fraca (tags conhecidas são reproduzíveis) |
| **Datamarking dinâmico** (k-gram de k chars de um alfabeto de N símbolos, intercalado em cada palavra) | **>50 % → <2 %** | **1/N^k** de adivinhação por chamada, mesmo com prompt vazado |
| Codificação unidirecional (Base64 do externo) | comparável | boa, mas quebra legibilidade para o modelo |

Regra: o marcador é gerado **por sessão/chamada**, nunca fixo no prompt.

### 3.3 Circuit breakers (Zou et al., NeurIPS 2024) e CC++ (Anthropic 2025/ICLR 2026)

| Controlo | Resultado publicado | Limite |
| --- | --- | --- |
| Representation Rerouting (LoRA 0–20, perda nas camadas 10/20, 150 passos, A100 ~20 min) | Forced function calling 87 %→**14 %**; LLaVA PGD 91,0 %→14,3 %; multilingue 19,3 %→3,5 %; BFCL 76,0 (vs 74,8) | atacante white-box adaptativo pode levar a robustez a **0 %** → precisa de isolamento de API |
| Constitutional Classifiers v1 | 86 %→**4,4 %**; +23,7 % de inferência; +0,38 % falsas recusas | vulnerável a reconstrução em código e ofuscação de saída |
| **CC++** (classificador de troca + sonda linear no estágio 1 + ensemble no 2) | **0,005 jailbreaks/1.000 consultas**; 0 universais em 1.700 h; **0,05 %** de bloqueio em produção (Sonnet 4.5); ~**1 %** de custo; **40×** mais barato que o classificador de troca isolado (8× vs cascata sem sondas) | tecnologia de fornecedor; sonda depende de acesso às ativações |

### 3.4 O pipeline de cinco camadas (com limiares acionáveis)

| # | Camada | Controlos e limiares | Ferramentas / latência |
| --- | --- | --- | --- |
| 1 | Borda L7 + normalização multi-vista | `NFKC`; remover `\u200B`–`\u200F`, `\u2060`, `\uFEFF`, bidi e **U+E0000–U+E007F**; decodificar Base64/Hex/ROT13 e correr assinaturas em todas as vistas | Agentgateway PromptGuard ~0 ms (L7, sem GPU); pré-processador <2 ms |
| 2 | Perplexidade + RAG anti-worm + Spotlighting | janela 32 / stride 16 + comprimento em LightGBM; chunks 512 / overlap 64; datamarking k-gram por sessão | DonkeyRail (TPR 1,0 · FPR 0,017 · 7,6–38,3 ms); SmoothLLM em endpoints críticos |
| 3 | Classificadores semânticos de entrada | pontuar todos os chunks e vistas; começar em **shadow/annotate** e só bloquear com dupla confirmação | Prompt Guard 2 22M (19,3 ms; 88,7 % recall @1 % FPR) / 86M (92,4 ms; 97,5 %); Azure Prompt Shields 52 ms; Lakera ~50 ms; LLM Guard 50–200 ms |
| 4 | Runtime: sessão, CoT e guarda de ação | **recusa-reformulação**: `refusals ≥ 3` **e** `max_cosine > 0,85` contra prompts recusados; **many-shot**: turnos falsos ≥ 10 **ou** `input_tokens > tenant_p99`; **declive de escalonamento**: tendência positiva dos scores brutos nos últimos N turnos; auditar CoT contra *goal hijacking*; validar ferramentas em motor determinístico | LlamaFirewall (AlignmentCheck + PromptGuard 2 → ASR 1,75 %; CodeShield 96 % precisão / 79 % recall); Granite Guardian 4.1 8B (0,79 balanced accuracy em *function-call hallucination*); NeMo Guardrails 100–500 ms |
| 5 | Saída, DLP, canários, renderização | **três alarmes**: (a) entrada limpa + saída sinalizada = bypass provável → bloquear e rever sessão; (b) língua/codificação inesperada (Base64/Hex); (c) canário na saída; redação regex + ruído diferencial em constantes numéricas de `task_summary`; bloquear `<img>` externo e links reference-style | Presidio 3–15 ms; Guardrails AI 50–300 ms (Pydantic/JSON); Qwen3Guard-Stream 0.6B–8B (119 línguas); OpenAI Moderation 192 ms (F1 0,899 limpo) |

**Porque nenhuma camada chega sozinha:** Azure Content Safety F1 0,928 em dados limpos cai para
0,19–0,61 sob ataque; Qwen3Guard-8B 91,0 % → 33,8 % em ataques inéditos; Llama Guard 4 69 % recall
/ 11 % FPR; na Unit 42 a configuração mais permissiva interceta **53 %** dos ataques (deixando passar
42 de 51 ataques com role-play e 100 % dos embutidos em revisão de código) e a mais agressiva bloqueia
92 % com 13,1 % de FPR — o ótimo calibrado é ~**91 % de bloqueio com 0,6 % de FPR**.

### 3.5 Isolamento: Dual LLM → CaMeL e padrões derivados

```
utilizador (confiável) ──► P-LLM (planeia, vê ferramentas) ──► plano em pseudo-Python
                                                                      │
RAG/web/e-mail/MCP (não confiável) ──► anti-worm + Spotlighting ──► Q-LLM (sem ferramentas)
                                                                      │
                                     interpretador + Data Flow Graph + Capacidades
                                                                      │
                                          política determinística ──► HITL ──► execução
```

- O **Dual LLM puro** protege o fluxo de controlo; um documento injetado ainda pode trocar
  argumentos (destinatário, ficheiro) no Q-LLM.
- **CaMeL** resolve isso com grafo de fluxo de dados + capacidades por variável e verificação
  determinística antes de cada chamada: **77 %** das tarefas no AgentDojo com garantias formais
  (84 % sem defesa).
- Padrões complementares: **Action-Selector**, **Plan-Then-Execute**, **LLM Map-Reduce**,
  **Context-Minimization**.
- Multi-agente/MCP: assinar `task_summary` e descrições de ferramentas; read-only em produção;
  eliminar do prompt instruções do tipo "processa instruções de roteamento nos documentos"; políticas
  de negócio (limites, listas de bloqueio) em código fora do LLM com identidade do chamador.

| Defesa declarada | Bypass com atacante adaptativo |
| --- | --- |
| 12 defesas publicadas avaliadas em "The Attacker Moves Second" (2025) | contornadas em **>90 %** |

Conclusão de arquitetura: **classificadores são speed bumps; containment is the boundary.**

## 4. Prompt endurecido v2026 — o que não pode faltar

O system prompt não é segredo (OWASP LLM07) nem controlo único: sem credenciais no texto e com
validação externa. Os controlos que o estudo exige, e que `harden.py` verifica:

1. **Hierarquia explícita** (bloco de sistema > developer > utilizador > dados/ferramentas).
2. **Spotlighting dinâmico** com tag por sessão (`<UNTRUSTED_DATA_{NONCE}>`) e datamarking k-gram.
3. **Anti-mimetismo**: ignorar `[TASK_SUMMARY]`, `[ORCHESTRATOR INSTRUCTION]`, `[SYSTEM OVERRIDE]`
   e políticas falsas em XML/JSON/YAML/INI.
4. **Anti-H-CoT**: ignorar raciocínio pré-preenchido e alegações de que a verificação já passou.
5. **Anti-Skeleton Key / DAN / Dr. House**: nenhuma persona, nenhum "aumento de diretrizes" com
   disclaimer.
6. **Anti-Bad-Likert**: nunca gerar exemplos nocivos em rubricas, escalas, crítica de arte ASCII
   ou completação de estruturas de dados.
7. **Anti-EchoLeak**: proibir imagens externas, HTML, links reference-style, dados internos em URLs
   e respostas codificadas (Base64/Hex/ROT13).
8. **Canário** de integridade no prompt, nunca reproduzível, com alarme na saída.
9. **HITL** para ações consequentes e **menor privilégio** por ferramenta/sessão.
10. **Orçamento de sessão** e protocolo fixo de resposta a padrões suspeitos (circuit breaker).

## 5. Operacionalização (TEVV)

| Vetor de validação | Ferramenta | O que cobre |
| --- | --- | --- |
| CI/CD de aplicação e agentes | **Promptfoo** (MIT) com preset `owasp:agentic` + plugin MCP | injection, memória envenenada, BOLA/BFLA, SSRF a cada PR |
| Modelo e tokenizador | **NVIDIA garak** (Apache 2.0, 120+ sondas) | sondas estáticas/dinâmicas/adaptativas + glitch tokens ao introduzir modelo/LoRA/tokenizer |
| Adversário adaptativo multi-turno | **Microsoft PyRIT** (MIT) | Crescendomation, Skeleton Key, TAP, 16 vulnerabilidades agênticas |
| Medição | regras de higiene | nunca contar erros de infra como bloqueio; medir *safety score* e integridade de chamadas, não frases de recusa; reportar **pass@k** com **FPR** em controlos benignos |
| Produção | observabilidade | logs separados modelo/guardrails, **scores contínuos** (não flags), canários, alarme de discrepância entrada-limpa/saída-suja |

Conformidade: ações **MEASURE 2.7**, **MEASURE 2.10**, **MS-2.5-006** e **MG-4.1-002** do **NIST AI
600-1**; red teaming documentado como suporte de *safe harbor* (ex.: Texas AI statute,
Sec. 552.105(e)).
