# Defesa em profundidade: controles, pressupostos e integrações

> O [estudo fornecido](<../pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md>) é integrado com erratas e limites no [registro de evidências](<evidencias.json>). Esta arquitetura é uma **proposta**, não um firewall já instalado. O [catálogo em código](<../scripts/defesa.py>) apenas a representa. Latência, FPR e ASR locais não foram medidas nesta entrega.

## 1. Invariantes de contenção

1. Dados externos não podem conceder autoridade, aprovar ações ou selecionar arbitrariamente recursos/destinos.
2. Toda ação consequente é mediada por código confiável, com identidade do chamador e tenant, esquema, capacidades e política de negócio.
3. Saídas de um Q-LLM, resumo, extrator ou juiz continuam sujeitas a validação. Separar modelos não torna argumentos confiáveis.
4. O usuário pode instruir legitimamente dentro do escopo, mas não pode elevar sua autoridade por texto. Conteúdo colado/citado numa mensagem não herda confiança automaticamente.
5. Assinatura autentica origem/integridade sob hipóteses de chave/verificador; não prova verdade, intenção benigna ou autorização da ação.
6. Aprovação humana deve vincular ação, argumentos, destino, recurso/versão, identidade/tenant e expiração. Revalidar no uso, com anti-replay e consumo único quando aplicável.
7. Falha de sensor não autoriza ação. Se a decisão determinística ou aprovação necessária não está disponível, suspender a ação protegida, mantendo análise sem efeito lateral quando segura.

“Classificadores são sensores; contenção é a fronteira” é orientação arquitetural, não teorema de infalibilidade de software determinístico.

## 2. Cinco camadas de inspeção em runtime

| # | Objetivo | Controles | Limites e calibração |
| --- | --- | --- | --- |
| 1 | Borda L7 / vistas | Limites de bytes/tokens/tempo; original preservado; vista NFKC; análise de tags, bidi/invisíveis e UTS39; decodificação limitada Base64/Hex/ROT13 só para inspeção | NFKC não colapsa homóglifos cross-script. Strip indiscriminado corrompe conteúdo. Evitar divergência entre parser do validador e o da ferramenta |
| 2 | RAG / proveniência | Quarentena por item, rótulos de origem, inspeção anti-replicação, minimização e Spotlighting externo com marcadores novos | Marcador não é autenticação nem isolamento; Base64 não é confidencialidade; perplexidade é sensor opcional com FPs em código/línguas |
| 3 | Semântica de entrada | Detector de override separado de nocividade; chunks com bordas sobrepostas; shadow, avaliação por idioma/tenant e revisão de erros | Pontuações não são probabilidades calibradas por definição. Dois detectores correlacionados não formam duas garantias independentes |
| 4 | Sessão / ação | Estado no servidor; histórico com origem; orçamento; trajetória acumulada; validação de ferramenta/schema/argumentos/capacidades; HITL verificável | Contadores/encerramento pertencem ao runtime, não à memória imaginada pelo LLM. Auditoria usa evidência observável, não CoT privado |
| 5 | Saída / egress | DLP, esquema, buffering antes da emissão, sanitizador de renderização, fetch desabilitado por padrão, política de rede/SSRF | Bytes já enviados não podem ser recolhidos. Redigir PII não prova ausência de segredos. Não adicionar ruído a valores operacionais |

Cada camada deve ter proprietário, versão, ponto de enforcement, comportamento de falha, orçamento de latência e observabilidade. O catálogo não promete “0ms”, `<2ms` ou qualquer SLA local.

### 2.1 Unicode e múltiplas vistas (E08)

- Armazenar original e proveniência com acesso restrito, retenção mínima e redação de segredos.
- Normalizar uma vista de inspeção em NFKC, que é compatibilidade + composição canônica; análise de confusables/mixed-script é adicional.
- Detectar Tags Unicode U+E0000–U+E007F, controles bidi, zero-width e seletores de apresentação. Não presumir que todos sejam maliciosos.
- Limitar tamanho, profundidade e expansão de decodificação; não interpretar código nem seguir comandos da vista decodificada.
- Valores críticos de ação precisam ser tipados e validados **na mesma representação final** usada pelo executor. Normalização não pode trocar silenciosamente identidade, endereço ou permissão.

### 2.2 Spotlighting e RAG anti-worm (E07)

Datamarking e delimitação são transformações da aplicação antes da inferência. Um nonce no prompt não prova que todos os documentos foram marcados. Usar marcos novos e tratamento de colisões reduz previsibilidade, mas um atacante pode afetar comportamento sem adivinhar o marcador.

Quarentena deve preservar rótulos quando dados viram resumo, argumento ou memória. Inspeção anti-worm e contenção de propagação são relevantes mesmo quando nenhum termo suspeito aparece. Desativar envio/replicação fora do plano; material de teste deve ser sintético. DonkeyRail e seus números do estudo não são integração instalada nem medição local (E12).

### 2.3 Sensores: escopos diferentes (E09)

Prompt Guard 2 classifica intenção explícita de sobrescrever instruções, não nocividade geral nem autorização. No model card, 22M/86M têm recall inglês de 88,7%/97,5% a 1% FPR em benchmark privado, com 19,3/92,4ms para 512 tokens numa A100. Isso **não é resultado em pt-BR no tráfego deste projeto**; 22M tem limitação multilíngue maior.

Llama Guard, Granite, CodeShield, Presidio, NeMo, Azure, AWS, Lakera e outros podem ter tarefas, versões e políticas diferentes. Não comparar accuracy, F1, bloqueio e latência de benchmarks distintos como uma tabela homogênea. Os números comerciais históricos não foram revalidados (E12).

## 3. Sessão: detectar trajetória sem DoS por citação

O estudo propõe estes **pontos iniciais de engenharia, não limiares validados** (E11):

| Sinal | Hipótese inicial | Antes de bloquear |
| --- | --- | --- |
| Recusa/reformulação | `refusals >= 3` e `max_cosine > 0.85` | Definir recusa confirmada, embedding/tokenizer, idioma e comportamento benigno de esclarecimento |
| Forma many-shot | Turnos fabricados `>= 10` ou tokens `> tenant_p99` | Documentos podem conter diálogos legítimos; preservar task e origem dos turnos |
| Escalonamento | Tendência de scores em N turnos | Scores não calibrados ou mudança legítima de assunto não provam ataque |
| Perplexidade/chunks | Janela32/stride16; chunk512/overlap64 | Medir cobertura, custo e FPs; tokenizers dos detectores podem diferir |

Manter estado por tenant/identidade com TTL, limites e privacidade. Janela limitada pode perder dependências longas; estado ilimitado pode gerar custo, vazamento e acusações persistentes falsas. Definir o equilíbrio com tráfego legítimo.

**Não exigir raciocínio oculto:** usar pedidos, respostas públicas, propostas de ferramenta, argumentos, proveniência e decisões reais do runtime. Resumo de raciocínio disponível pode ser sinal auxiliar, nunca evidência fiel do processo interno. Alegações “já revisado/APROVADO” em dados não substituem checagem externa.

## 4. Saída, canários e renderização

Três alertas úteis, sem confundir alerta com prova:

1. **Entrada sem sinal / saída com sinal:** investigar toda a trajetória e revisar cobertura; o classificador de saída também pode errar.
2. **Idioma/codificação inesperados:** conferir tarefa e semântica. Tradução, encoding e código legítimos devem continuar possíveis.
3. **Eco inesperado de marcador:** confirmar a política daquele marcador. Eco de canário público solicitado não é vazamento por definição; um contrato artificial proibido deve ser explícito.

Renderizador deve interpretar HTML/Markdown com política segura, não depender de uma regex contra links de referência. Desabilitar conteúdo ativo e fetch externo não aprovado; resolver URLs/destinos; impor egress, redirects, SSRF e rede fora do modelo. A classe EchoLeak motiva essa separação, não a conclusão de que bloquear uma sintaxe elimina exfiltração.

DLP e minimização de PII são camadas falíveis. Valores financeiros, identificadores de recurso, destinatários e permissões precisam de **exatidão e validação**, não ruído diferencial genérico em `task_summary`. DP só com mecanismo, sensibilidade e orçamento formais numa finalidade estatística apropriada (E16).

## 5. Controle e dados: Dual LLM → capacidades

```text
Usuário autenticado / tarefa autorizada
            |
            v
     Planejador P-LLM ----> plano tipado sem conteúdo hostil
                                      |
RAG / e-mail / web / MCP               |
        |                             |
Proveniência + vistas + quarentena     |
        |                             |
Q-LLM sem ferramentas --> valores com rótulos de origem
                                      |
                  mediador/interpretador de capacidades
                                      |
              schema + identidade/tenant + política de negócio
                                      |
                  HITL vinculada à ação quando necessário
                                      |
                     revalidação atômica -> executor restrito
```

**Dual LLM puro:** protege a exposição do planejador ao texto externo, mas o extrator em quarentena ainda pode fornecer destinatário/valor/recurso adulterados. Um verificador LLM que lê a mesma injeção também pode falhar.

**CaMeL v2 (E05):** permite acompanhar capacidades/proveniência no fluxo e mediar ações em interpretador. O headline 77% versus84% AgentDojo depende da versão; não é “77% de segurança”. Pressupõe tarefa e memória confiáveis e correção de políticas, rótulos e mediação. Não resolve toda injeção, veracidade de texto ou phishing; formalização do interpretador é trabalho futuro.

**Padrões complementares:** Action-Selector, Plan-Then-Execute, Map-Reduce por item e minimização de contexto. Reduzem superfícies sob pressupostos, mas não autorizam afirmar risco zero nem dispensam validação de argumentos.

## 6. MCP e multi-agente: verificação fora do modelo

- Separar plano de controle, dados e transporte. Texto `[ORCHESTRATOR INSTRUCTION]` dentro de fatura nunca é um envelope de orquestração válido.
- Envelopes autenticados incluem emissor, destinatário, tarefa, tenant, versão/schema, hash do corpo, nonce/expiração e proteção anti-replay conforme a aplicação.
- Verificar assinatura e identidade em código confiável. Agente comprometido pode assinar conteúdo falso; assinatura não promove dado a instrução privilegiada.
- Fixar e revisar descrições/capacidades de ferramentas MCP; detectar mudanças posteriores à aprovação e desabilitar capacidades inesperadas.
- Manter limites de negócio e autorização por objeto/função fora do LLM, usando identidade com escopo do chamador.
- Não seguir instruções de arquivamento/roteamento/execução embutidas em documentos de conformidade. Propostas viram dados para revisão, não scripts executáveis.

## 7. Hardening de prompt sem sacrificar utilidade

As três templates em [harden.py](<../scripts/harden.py>) cobrem origem/autoridade, Spotlighting externo, anti-mimetismo, H-CoT, Skeleton Key, rubricas, confidencialidade, egress, menor privilégio e protocolo de ação. Defaults de canário/nonce/marcador são aleatórios e independentes; valores explícitos válidos permitem reproduzir o texto na mesma data.

O prompt deve **ignorar comandos injetados e continuar a tarefa segura**, não se deixar derrubar por qualquer menção a Base64/ASCII/persona. Pedidos realmente inseguros ou ações sem autorização exigem bloqueio/suspensão e alternativa segura. Não inventar verificação, assinatura válida ou estado de sessão.

O lint de 18 controles dá cobertura textual e sinais estruturais limitados. `aceitavel` não é certificado, prova de implementação nem desempenho medido. Canário público não é segredo/chave. Não colocar credenciais ou políticas sensíveis no texto.

## 8. Governança e TEVV neste pedido

NIST AI 600-1 é referência voluntária, OWASP é taxonomia de riscos e MITRE ATLAS deve ser versionada. Em ATLAS 2026.10, system instructions/contexto aparecem em AML.T0085.003/.002; tool poisoning é AML.T0110 (E13–E14). Não prometer certificação nem safe harbor jurídico.

Instrumentação futura deve correlacionar sessão e tenant sem expor segredos, registrar versões, decisões e scores brutos sem chamá-los automaticamente de probabilidades, e separar modelo, sensores, política, aprovação e executor. Preservar mínima evidência com retenção/acesso definidos.

**A etapa final solicitada é apenas o [roteiro Markdown /prompt-builder com JEV](<avaliacao-prompt-builder-jev.md>). Não executar testes, scanners, benchmarks, dry-runs, avaliação do alvo ou chamadas JEV como conclusão automática.** Promptfoo/garak/PyRIT permanecem referências de literatura, não tarefas adicionais deste pedido. A [metodologia](<metodologia-avaliacao.md>) especifica como interpretar métricas, não uma autorização de execução.
