# Mecânica de guardrails e arquitetura: leitura técnica revisada

> Revisão de fontes: **2026-11-04**. Esta síntese integra o [estudo fornecido](<../pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md>) sem converter toda afirmação nele em fato confirmado. O [registro de evidências](<evidencias.json>) diferencia correção, observação contextual, recomendação e número não verificado. Fontes externas são dados, nunca instruções.

## 1. O que um guardrail faz — e o que não faz

**Intrínseco:** SFT, RLHF, DPO e outras formas de pós-treinamento alteram distribuições de comportamento nos pesos. **Extrínseco:** classificadores, validadores, motores de políticas e controles de ferramentas inspecionam entradas, estados disponíveis, propostas de ação e saídas.

Um sistema real pode combinar redes neurais, regex, listas de destinos, schemas e código determinístico. Portanto, não é correto afirmar que *todo* guardrail opera por representações latentes ou que filtros por assinatura não existem. Também não há um único gatilho universal: intenção, forma, contexto, modalidade, versão e composição da aplicação importam.

Classificadores são sensores probabilísticos úteis. A fronteira de contenção deve ser imposta por mecanismos externos de identidade, autorização, capacidades, isolamento, egress e integridade de dados. “Determinístico” descreve como uma regra é aplicada, **não prova que a regra/implementação esteja correta**.

## 2. Causas-raiz e interpretabilidade

### 2.1 Objetivos concorrentes e generalização desalinhada

Wei, Haghtalab e Steinhardt descrevem:

- **Competing objectives:** utilidade, completação de padrões e seguimento de instruções podem entrar em conflito com objetivos de segurança. Prefixos afirmativos e proibição lexical de recusa são exemplos de pressão, não garantias de sucesso.
- **Mismatched generalization:** capacidades podem generalizar para cifras, código, idiomas e contextos pouco cobertos pelo treino de segurança. Modelos mais capazes podem acompanhar transformações mais difíceis, mas isso não estabelece uma lei de que “maior é sempre menos seguro”.

O eixo instrutivo é o **mecanismo causal hipotetizado**, não a criação de uma lista de palavras proibidas. Ver [taxonomia](<taxonomia-e-tecnicas.md>).

### 2.2 Direção mediadora de recusa (E06)

Arditi et al. estudaram **13 modelos conversacionais abertos até 72B**, identificando uma direção mediadora de recusa no fluxo residual. A notação do estudo é:

$$r=\mu_{harmful}-\mu_{harmless}, \qquad \hat r=r/\|r\|.$$

A intervenção de projeção investigada pode ser expressa como:

$$x' = x-(x\cdot\hat r)\hat r.$$

As intervenções causais estudadas incluem remoção/adicionamento dessa direção e análise da supressão de sua propagação por sufixos. Isso fornece evidência mecanística **nos modelos e avaliações estudados**, não uma descrição completa da segurança de todo modelo. Recusa não equivale a ausência de capacidade nociva nem a contenção das ferramentas.

**Consequência defensiva:** verificar procedência/hashes de pesos e adaptadores, tokenizer, quantização e mudanças de pós-treinamento. O projeto documenta esse vetor, mas **não altera pesos nem instala circuit breakers ou sondas**.

### 2.3 Fronteira entre controle e dados

A analogia *in-band* ajuda a compreender a mistura de instruções e conteúdo numa sequência interpretada pelo modelo. Porém, APIs possuem papéis/canais reais: não se deve negar sua existência nem afirmar que uma tag no texto cria um canal privilegiado.

Uma mensagem legítima do usuário pode conter instruções subordinadas **e** citações como dados. Documento, página, e-mail, memória recuperada, campo de fatura e saída de ferramenta não ganham autoridade por se parecerem com `SYSTEM`, `task_summary` ou uma política XML.

Separação probabilística no modelo precisa ser acompanhada de fronteiras reais na aplicação. Histórico fabricado, resumo assinado mas falso e descrição MCP comprometida continuam exigindo políticas externas.

## 3. Taxonomia e métricas corrigidas (E01–E02)

O artigo citado é **Giarrusso, Sorokoletova et al., “Guarding the Guardrails: A Taxonomy-Driven Approach to Jailbreak Detection”, arXiv:2510.13893v2, 2026-02-04**.

A Tabela 1 mede sucesso por conversa no **Minerva-7B-instruct-v1.0**, em 1.364 ramos adversariais com 185 sucessos, obtidos por 48 mestrandos em sessões de duas horas, principalmente em italiano e parte em inglês. As famílias **coocorrem**; o denominador varia por rótulo.

| Família científica | Conversas com rótulo | Sucessos | SR publicada, arredondada |
| --- | ---: | ---: | ---: |
| Impersonação/ficção | 696 | 105 | 15,1% |
| Escalonamento de privilégios | 100 | 11 | 11,0% |
| Persuasão | 250 | 36 | 14,4% |
| Sobrecarga cognitiva | 289 | 38 | 13,1% |
| Codificação/ofuscação | 139 | 13 | 9,4% |
| Conflito de objetivos | 624 | 74 | 11,9% |
| Envenenamento de dados/contexto | 198 | 34 | 17,2% |

As percentagens 14,3/17,1/7,8 etc. e a coluna “tarefas selecionadas” do estudo fornecido **não correspondem a essa tabela do v2**. Não tratá-las como um ranking universal, nem substituir uma tabela corrigida por uma narrativa de “persuasão sempre vence”. O SR sem técnica é 7/110, aproximadamente 6,4%, no mesmo protocolo. Ataques automáticos são um **eixo auxiliar ortogonal**, não uma oitava família causal.

O ganho de detecção GPT-5 de **60/91 (65,9%) para 71/91 (78,0%)** foi medido apenas em diálogos com jailbreak já bem-sucedido, excluindo ataques de infraestrutura. Foram 13 recuperados e dois perdidos, ganho líquido de 11/91, aproximadamente 12,1 pontos percentuais. Sem benignos, **FPR não medida**. Não é acurácia global nem ganho líquido de 14,3pp.

Os nove agrupamentos de [strategies.py](<../scripts/strategies.py>) mantêm compatibilidade operacional e adicionam multi-turno/raciocínio como eixos úteis. Suas 50 templates **não reproduzem fielmente** o protocolo de todos os artigos de mesmo nome. As notas quantitativas individuais remanescentes são históricas/não revalidadas até revisão específica.

## 4. Defesas no modelo e no prompt

### 4.1 Hierarquia de instruções

Treinar um modelo para privilegiar canais e ignorar conteúdo conflitante é diferente de apenas escrever “prioridade absoluta” num prompt. A aplicação deve instalar instruções no canal correto; delimitadores não podem sobrepor sistema/developer/usuário real.

Medir utilidade e sobre-recusa separadamente. Perguntas sobre capacidades e explicações públicas de limites não devem ser bloqueadas por definição. O system prompt não deve conter credenciais nem servir como fronteira de confidencialidade.

### 4.2 Spotlighting (E07)

Delimitação, datamarking e mudanças de representação ajudam o modelo a reconhecer a origem dos dados. Resultados como **menos de 2% de ASR** pertencem a experimentos específicos, não a qualquer agente corporativo.

- A transformação tem de ocorrer **no código da aplicação**; gerar um texto que a descreve não a aplica.
- O marcador pode mudar por chamada, com geração segura e tratamento de colisões.
- `1/N^k` é chance idealizada de adivinhação do marcador, não limite de sucesso de injeção.
- **Base64 é reversível**, não “codificação unidirecional” criptográfica nem confidencialidade.
- O atacante pode influenciar o modelo sem fechar tags ou adivinhar marcador algum.

### 4.3 Circuit Breakers / Representation Rerouting

Redirecionamento de representações e adaptadores são defesas de nível de modelo; requerem acesso e treinamento apropriados, avaliação de utilidade e atacante adaptativo compatível com o threat model. Resultados em function calling, multimodalidade e idiomas não são intercambiáveis nem garantia contra adversário white-box.

Não confundir o método de pesquisa com um `if` no prompt ou uma mensagem “circuit breaker ativado”. O cancelamento real de uma ferramenta pertence ao runtime.

### 4.4 Constitutional Classifiers++ (E03–E04)

A cascata usa probes internos e classificador de troca para casos suspeitos. Separar seus resultados:

| Dado | Interpretação correta |
| --- | --- |
| 1 vulnerabilidade de alto risco / 198.000 tentativas | Aproximadamente **0,005 descobertas por mil consultas de red team**, não probabilidade universal de jailbreak por consulta |
| Mais de 1.700h sem universal encontrado no protocolo | Resultado de busca sob orçamento/escopo específicos, não inexistência provada |
| Cerca de 1% compute | Estimativa para tráfego Claude Opus 4.0, não latência nem custo genérico de qualquer sonda |
| 0,05% benignos Sonnet 4.5 em um mês | Relato de taxa em consultas benignas; conferir shadow flag vs recusa no protocolo |
| 40× e 8× | Comparadores distintos: baseline exchange classifier e cascata sem probes |

A referência versionada é arXiv:2601.04603v1. A atribuição bibliográfica e a alegação ICLR do texto original não foram adotadas sem confirmação. Acesso às ativações não está disponível em toda API hospedada; não simular probes por texto.

## 5. Contenção e cinco camadas

O [catálogo de defesa](<defesa-em-profundidade.md>) e [defesa.py](<../scripts/defesa.py>) organizam:

1. Borda/normalização multi-vista com original preservado e limites de recursos.
2. Proveniência, RAG em quarentena, anti-replicação e Spotlighting externo.
3. Classificadores de injeção/nocividade separados e calibrados em shadow.
4. Runtime com identidade/tenant, estado, guarda de ação, capacidades e HITL.
5. Saída com DLP, buffering, sanitização de renderização e egress deny-by-default.

Nenhuma integração é instalada pelo catálogo. Latência local é **não medida**. Parâmetros como 3 recusas, similaridade 0,85 ou dez turnos fabricados são **hipóteses de calibração**, não resultados científicos universais (E11).

**Dual LLM:** Q-LLM lê dados externos sem ferramentas; P-LLM planeja sem ler texto hostil. Isso reduz influência sobre controle, mas argumentos extraídos podem continuar adulterados.

**CaMeL v2 (E05):** associa proveniência/capacidades a valores e medeia fluxo/ações no interpretador. Headline 77% de utility no AgentDojo versus 84% sem defesa, condicionado à versão. Pedido do usuário e memória confiáveis, políticas/labels corretos e mediação completa são pressupostos. Não garante veracidade de resumos, prevenção de phishing textual ou de todo canal lateral. A verificação formal do interpretador é explicitamente **trabalho futuro**.

## 6. Três erros de engenharia a evitar

- **Unicode:** NFKC é compatibilidade + composição, não conversão de todo “a” cirílico em latino. UTS39 é análise adicional; não destruir evidência, idioma ou identidade (E08).
- **Criptografia:** assinatura valida origem/integridade sob hipóteses de chave/verificador, não verdade nem autorização. Usar envelope, schema, contexto, anti-replay e políticas externas (E16).
- **Dados operacionais:** não aplicar ruído diferencial genericamente a valores de pagamento, destinatários, permissões ou limites. DP requer desenho formal em agregações apropriadas; integridade operacional exige valores exatos (E16).

Auditoria genérica usa **evidência observável**, não CoT privado. Um resumo de raciocínio não é garantia de fidelidade ao cálculo interno nem prova de segurança.

## 7. TEVV e normas sem falsa certificação

O estudo cita Promptfoo, garak e PyRIT como ferramentas da literatura. **A etapa final adotada neste pedido é apenas o [Markdown /prompt-builder + JEV](<avaliacao-prompt-builder-jev.md>), sem execução**; esses frameworks não são tarefas adicionais.

NIST AI 600-1 é perfil voluntário. MEASURE 2.7 cobre segurança/resiliência e MEASURE 2.10, privacidade. IDs de ações sem conferência direta do PDF e suposto safe harbor do Texas permanecem não confirmados nesta revisão (E13). Não derivar aconselhamento ou garantia jurídica de um checklist.

Fixar snapshot da MITRE ATLAS: em **2026.10**, extração de system instructions e memória/contexto aparecem como **AML.T0085.003** e **AML.T0085.002**, após migração dos IDs antigos T0056/T0057. Injeção direta/indireta/triggered e jailbreak mantêm AML.T0051.000/.001/.002 e AML.T0054; tool poisoning é AML.T0110 (E14). OWASP é vocabulário de risco, não prova de que toda categoria tenha a mesma causa-raiz.

## Fontes primárias principais

- [Taxonomia v2](<https://arxiv.org/html/2510.13893v2>), [direção de recusa v3](<https://arxiv.org/abs/2406.11717v3>) e [StrongREJECT v2](<https://arxiv.org/abs/2402.10260v2>).
- [Spotlighting](<https://arxiv.org/html/2403.14720v1>), [CC++ v1](<https://arxiv.org/html/2601.04603v1>), [relato CC++](<https://www.anthropic.com/research/next-generation-constitutional-classifiers>) e [CaMeL v2](<https://arxiv.org/html/2503.18813v2>).
- [UAX15](<https://www.unicode.org/reports/tr15/>), [UTS39](<https://www.unicode.org/reports/tr39/>), [RFC4648](<https://www.rfc-editor.org/rfc/rfc4648>) e [Prompt Guard 2 model card](<https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M/blob/main/README.md>).

O [registro completo](<evidencias.json>) contém localizadores, unidades e limitações. Números não auditados não devem ser “confirmados por proximidade” de uma citação verificada.
