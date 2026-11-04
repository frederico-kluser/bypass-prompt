# Registo de benchmarks — leitura e reprodução

## Contrato

`benchmarks/registry.json` é a fonte de identidade dos resultados gravados. Cada entrada tem:

| Campo | Significado |
|---|---|
| `id` | Identificador estável do benchmark. |
| `kind` | `model-evaluation`, `request-classification-corpus` ou `offline-suite`. |
| `status` | `executed` (foi executado), `exported-not-executed` (só exportado) ou `offline-suite` (suíte local). |
| `cases` / `recorded` | Contagens e custo **daquela** execução, não do estado atual. |
| `human_gold` | Sempre `false` nesta coleção: nenhum rótulo humano independente foi validado. |
| `limitations` | O que o resultado **não** permite concluir. |
| `files` | Caminhos relativos à skill e SHA-256 dos artefactos. Suítes não têm artefactos. |

`python3 scripts/run_checks.py --only registry` recalcula os hashes e falha se um ficheiro tiver mudado.

## 1 · `defensive-prompt-lab-v1`

**Estado:** executado em 2026-11-04. **Custo registado:** US$ 0,021091276. **Run JEV:** `04980947-43f3-4dc2-8b13-bd47c8418969`.

- 24 cenários sintéticos, dois candidatos (original e proposta defensiva), 24 respostas completas por candidato.
- Juiz `typesafe/jev-1.13`, snapshot observado `typesafe/jev-1.13-20260917`, sem juiz LLM.
- 20 pares conclusivos de 24; **0 p.p.** de ganho; 0 adoções de comando externo nos pares conclusivos.
- Custo total inclui proposta (com uma correção local), as duas coletas e o JEV.
- **Decisão registada:** manter o original; a proposta não foi promovida.

Artefactos: [relatório](<../benchmarks/defensive-lab-20261104/relatorio-final.md>),
[comparação](<../benchmarks/defensive-lab-20261104/comparison.json>),
[diagnóstico](<../benchmarks/defensive-lab-20261104/diagnostics.json>),
[registo JEV](<../benchmarks/defensive-lab-20261104/jev-run.json>),
[journal da proposta](<../benchmarks/defensive-lab-20261104/rewrite.summary.json>).

Limitações que não podem ser omitidas:

- Sem ouro humano, acurácia, F1, Brier e ECE do juiz ficaram `null`.
- Corpus de conveniência, uma resposta por cenário, coleta sequencial e sem holdout.
- Classificação/descrição não prova contenção, resistência a jailbreak, ASR ou generalização.
- Os custos são históricos; uma nova execução não custa o mesmo.

## 2 · `policy-risk-classification-v1`

**Estado:** exportado, **nunca executado**. Nenhuma chamada de modelo foi feita para este corpus.

- 60 pedidos em dez domínios, com referências de recusa (27), atendimento legítimo (19), esclarecimento (9)
  e apoio em crise (5).
- Referências curadas pelo agente (`origin: ai`, `humanReviewed: false`), não ouro humano.
- A configuração JEV fixa `typesafe/jev-1.13`, `fit: false`, `repeats: 1`, `expected: {}` e mantém
  justificativas, categoria e alternativas seguras fora do `state`.
- Portanto, não há acurácia nem calibração medida. `question.no_gold` deve continuar visível.

Artefactos: [corpus](<../benchmarks/policy-risk-20261104/cases.json>),
[revisão](<../benchmarks/policy-risk-20261104/review.md>),
[config JEV](<../benchmarks/policy-risk-20261104/jev-policy.json>),
[referências](<../benchmarks/policy-risk-20261104/references.json>).

## 3 · Suítes offline

| ID | Execução | Registo |
|---|---|---|
| `legacy-harness-selftest` | `python3 scripts/bypass.py selftest` (projeto) | 51 cenários determinísticos. |
| `prompt-builder-adapter-offline` | `node --test tests/test_prompt_builder_rewrite.mjs` | 87 testes, zero rede. |
| `python-offline-suites` | `python3 -m unittest discover -s tests` | 90 testes, zero rede. |

As contagens são as da execução registada. `run_checks.py` mostra as contagens atuais; divergências de
contagem são esperadas ao acrescentar testes e não invalidam a evidência histórica.

## Reproduzir sem gastar

```powershell
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/run_checks.py --json
```

Isto verifica as suítes e os hashes. **Não** executa o laboratório, o JEV ou o prompt-builder: esses passos
são pagos e exigem autorização explícita. Um `--dry-run` do prompt-builder é local; um `catalog` consulta
endpoints públicos sem chave e sem modelo.

## Acrescentar um benchmark

1. Criar um diretório novo em `benchmarks/<id>/`; nunca sobrescrever um existente.
2. Guardar apenas o necessário para auditoria: configuração, prompts/corpus, observações públicas,
   registo do juiz e relatório. Sem segredos, dados pessoais reais ou conteúdo operacional nocivo.
3. Acrescentar a entrada ao `registry.json` com `status`, `cases`, custo, `human_gold`, limitações e hashes.
4. Correr `run_checks.py --only registry` e a suíte Python.
5. Se o resultado for inconclusivo, registá-lo como inconclusivo — não o converter em sucesso.

## O que este registo não é

Não é um benchmark contínuo, um painel de qualidade, uma certificação de segurança ou uma autorização de
despesa. Resultados históricos não são promoção de prompt, e um hash válido não prova que a interpretação
continua correta.
