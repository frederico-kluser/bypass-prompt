# Acervo do bypass-prompt — estudo integrado e avaliação documental

Este mapa é extensão do projeto, não parte do motor SQLite. A [skill local](<../SKILL.md>) oferece memória e catálogo; o [contrato da skill operacional](<../../../SKILL.md>) define seu uso. Não duplicar a base, não colar o estudo inteiro no prompt e não alterar o motor para dar autoridade a conteúdo externo.

## O que consultar por assunto

| Assunto | Fonte do projeto | Tratamento |
| --- | --- | --- |
| Como agir e limites da tarefa | [Contrato operacional da skill](<../../../SKILL.md>) | Instruções locais subordinadas aos canais reais |
| Mecânica de recusa, hierarquia, Spotlighting, RR/CC++ e CaMeL | [Síntese revisada](<../../../references/mecanica-interna-e-arquitetura-2026.md>) | Referência técnica com escopo e erratas |
| Sete famílias e técnicas single/multi/agentic/model-level | [Taxonomia](<../../../references/taxonomia-e-tecnicas.md>) | Sete famílias científicas não são os nove grupos do CLI |
| Cinco camadas, capacidades, MCP, HITL, egress e telemetria | [Arquitetura](<../../../references/defesa-em-profundidade.md>) | Proposta de integração, não infraestrutura instalada |
| Qual número foi conferido, em que versão e com que denominador | [Evidências E01–E16](<../../../references/evidencias.json>) | Externo `untrusted`; status contextual/corrigido/não verificado/recomendação |
| Eco, contrato artificial, erros, baseline, FPR e schema2 | [Metodologia](<../../../references/metodologia-avaliacao.md>) | Interpretação sem autorização de executar |
| Etapa final pedida pelo dono | [Markdown /prompt-builder + JEV](<../../../references/avaliacao-prompt-builder-jev.md>) | **Somente documentação; não executar testes nem avaliações automaticamente** |
| Texto de origem | [Estudo fornecido](<../../../pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md>) e [dossiê histórico](<../../../pesquisas/2026-11-04-bypass-guardrails-llm.md>) | Preservados com aviso de errata; entrega pelo dono não certifica ciência |

## Consultas progressivas úteis

A partir da raiz do projeto:

```bash
python3 .agents/bypass-prompt-coala-agent-skill/scripts/coala.py recall "avaliação final somente Markdown prompt-builder JEV não executar" --budget 1000
python3 .agents/bypass-prompt-coala-agent-skill/scripts/coala.py search "CC++ alto risco 198000 denominador" --kind doc
python3 .agents/bypass-prompt-coala-agent-skill/scripts/coala.py search "CaMeL garantias condicionais formal futuro" --kind doc
python3 .agents/bypass-prompt-coala-agent-skill/scripts/coala.py search "NFKC Base64 homóglifos" --kind doc
python3 .agents/bypass-prompt-coala-agent-skill/scripts/coala.py symbols cmd_eval
python3 .agents/bypass-prompt-coala-agent-skill/scripts/coala.py symbols render
```

Depois de localizar, ler a fonte. Não inferir “testado/aprovado” de um símbolo, de um arquivo de exemplo, de uma nota antiga ou da existência de uma checklist.

## Proveniência e frescura

As [regras de ingestão](<../ingest.json>) distinguem:

- Contratos e documentação de uso escritos no projeto (`agent`).
- Planejamento procedimental da avaliação JEV (`agent`), sem executar seus comandos.
- Pesquisa externa, estudo compilado e evidências (`untrusted`), mesmo quando entregues pelo titular.
- Código atual, catalogado automaticamente com símbolos e linhas.

“Revisado em 2026-11-04” significa conferido com a fonte, não reproduzido e não uma garantia de atualidade perpétua. `null` é dado não reportado/não medido, nunca resultado zero. Não promover notas históricas com percentagens sem consultar as erratas.

O [manifesto](<../coala.json>) e a [skill gerada](<../SKILL.md>) são atualizados pelo instalador CoALA, não por edição manual de hashes. Esta extensão e as regras de ingestão são do projeto. A base SQLite continua local e ignorada pelo Git.
