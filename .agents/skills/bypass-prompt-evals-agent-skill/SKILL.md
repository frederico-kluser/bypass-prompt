---
name: bypass-prompt-evals-agent-skill
description: "Testes e benchmarks LOCAIS do projeto bypass-prompt: suítes offline da API fixa OpenRouter/GLM, do laboratório defensivo, do corpus de risco/recusa e do adaptador prompt-builder, mais os artefactos e resultados já medidos. Use ao executar ou auditar testes, reproduzir/verificar um benchmark, comparar um prompt defensivo antes/depois com JEV-only, listar ou exportar casos de política, ou confirmar hashes de evidência. Não faz chamadas pagas nem rede automaticamente; não otimiza evasão, não reencaminha recusas e não trata referências curadas pelo agente como ouro humano."
metadata:
  type: evals-and-benchmarks
  project: bypass-prompt
  offline-default: "true"
  paid-calls: "explicit authorization only"
---

# Testes e benchmarks — bypass-prompt

Esta skill é a **casa canónica** das suítes de teste e dos benchmarks do projeto. As ferramentas de avaliação
vivem aqui, e não no `scripts/` principal. O projeto continua a ser a fonte dos módulos centrais
(`harden.py`, `bypass.py`); o caminho é resolvido automaticamente e pode ser sobreposto com
`BYPASS_PROMPT_ROOT`.

**Contrato:** correr verificações é offline por omissão. Nenhum comando deste guia gasta créditos, consulta
catálogo remoto ou lê credenciais, exceto os passos **live** explicitamente marcados, que exigem autorização
do dono e orçamento. Resultados gravados são **evidência histórica**, não uma medição atual nem permissão
para repetir a despesa.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `scripts/defensive_api.py` | Cliente OpenRouter fixo: GLM 5.3 Flash, effort `max`, provider `z-ai/fp8`, sem fallback/ferramentas. |
| `scripts/defensive_lab.py` | Laboratório benigno: prepare/catalog/collect/export-jev/compare e o comando `policy-cases`. Corpus v2: 24 pares originais congelados + 12 pares por família de gatilho. |
| `scripts/policy_cases.py` | Corpus de política: validação, filtros, exportação e verificação de pacotes. |
| `scripts/prompt_builder_rewrite.mjs` | Adaptador de uma proposta defensiva cega via prompt-builder local. |
| `scripts/run_checks.py` | Executor único das verificações offline e do registo de benchmarks. |
| `tests/` | Cinco suítes: API, laboratório, política, adaptador Node e integridade dos benchmarks. |
| `assets/casos-politica-risco-v1.json` | 60 casos de alto nível em dez domínios de risco. |
| `benchmarks/` | Cópias curadas dos resultados medidos, manifesto com hashes e limitações. |
| `references/` | Detalhe das suítes e do registo de benchmarks. |

O template de hardening usado como linha de base do laboratório vive no projeto (`scripts/harden.py`,
v6) e ganhou uma secção de gatilhos conhecidos em dados derivada do estudo interno — só as secções de
defesa; nada do estudo é usado para evasão.

## Verificação offline — começar aqui

```powershell
# A partir da raiz do projeto; não precisa de chave nem de rede.
python3 .agents/skills/bypass-prompt-evals-agent-skill/scripts/run_checks.py
```

| Check | O que faz |
|---|---|
| `python` | `unittest` sobre `tests/`, com transportes falsos e diretórios temporários. |
| `node` | Suíte do adaptador com `fetch` falso e bloqueio de rede. |
| `project` | `scripts/bypass.py selftest` do projeto, determinístico e offline. |
| `templates` | Lint heurístico dos três templates de hardening (não é certificação). |
| `registry` | Recalcula os SHA-256 de todos os artefactos registados. |

Opções: `--only python,node` (lista separada por vírgulas), `--json` para payload estável.
Exit `0` = tudo passou · `1` = falha · `2` = uso inválido.

As suítes podem ser executadas isoladamente a partir desta pasta:

```powershell
python3 -m unittest discover -s tests -v
node --test tests/test_prompt_builder_rewrite.mjs
```

## Benchmarks registados

O [registo](<benchmarks/registry.json>) é a fonte de identidade: `id`, tipo, estado, contagens, custo
registado, limitações e hashes. O executor confirma que os ficheiros não divergiram.

| ID | Tipo | Estado | Registo principal |
|---|---|---|---|
| `defensive-prompt-lab-v1` | Avaliação de modelo | Executado em 2026-11-04 | 24 cenários, 20 pares conclusivos, **0 p.p.** de ganho, custo total ≈ US$ 0,0211, sem ouro humano. |
| `defensive-prompt-lab-v2` | Avaliação de modelo | Executado em 2026-11-04 | 24 cenários, 22 pares conclusivos, **0 p.p.** de ganho, coleta −4,17% e p95 −49,42% vs original, custo ≈ US$ 0,0189, não promovida. |
| `defensive-prompt-lab-v3` | Avaliação de modelo | Executado em 2026-11-04 | 48 cenários (corpus v2, 13 famílias), 40 pares conclusivos, **0 p.p.**, coleta −14,09% e p95 −30,97% vs template v6, custo ≈ US$ 0,0324 (+ US$ 0,0292 em tentativas falhadas), 2 defeitos reproduzíveis da proposta registados, não promovida. |
| `policy-risk-classification-v1` | Corpus de classificação | Executado em 2026-11-04 | 60 casos, decisões JEV 27/19/9/5 = referências curadas, concordância 60/60 (consistência descritiva, **não acurácia**; sem ouro humano). |
| `legacy-harness-selftest` | Suíte offline | Executado | 51 cenários determinísticos do harness legado. |
| `prompt-builder-adapter-offline` | Suíte offline | Executado | 87 testes Node, zero rede. |
| `python-offline-suites` | Suíte offline | Executado | 90 testes Python, zero rede. |

Os resultados das três rondas estão em [v1](<benchmarks/defensive-lab-20261104/relatorio-final.md>),
[v2](<benchmarks/defensive-lab-20261104-r2/relatorio-final.md>) e
[v3](<benchmarks/defensive-lab-20261104-r3/relatorio-final.md>), com comparação, diagnóstico por família e
achados em cada diretório. A conclusão registada é **manter o prompt original** como referência: nenhuma
proposta demonstrou ganho de utilidade (0 p.p. nas três rondas); a ronda 3 mediu a tensão entre disciplina
de saída e sinalização defensiva (a proposta reproduziu uma diretiva injetada sem tratá-la como dado em
`payload64-conflict`). Isto não é uma alegação de eficácia, de contenção ou de calibração do juiz — ver as
limitações no registo.

## Corpus de risco e recusa — classificação apenas

```powershell
python3 scripts/defensive_lab.py policy-cases --list
python3 scripts/defensive_lab.py policy-cases --list --category pentest --category armas --action refuse
python3 scripts/defensive_lab.py policy-cases --out-dir <novo-dir> --budget 0.10
python3 scripts/defensive_lab.py policy-cases --verify <novo-dir>
```

São operações locais. O pacote exportado contém `cases.json`, `references.json`, `jev-policy.json`,
`review.md` e `manifest.json`; cria sempre um diretório novo e recusa sobrescrever. O modelo JEV é fixado
em `typesafe/jev-1.13` por omissão; `--jev-model typesafe/jev-1.14` é uma escolha explícita para outra
experiência, não um fallback nem uma alegação de qualidade.

As referências são curadoria do agente (`origin: ai`, `humanReviewed: false`). A configuração JEV mantém
`expected: {}`, de modo que as referências **não** produzem acurácia/calibração como se fossem ouro humano.
O lint deve continuar a avisar `question.no_gold`; não preencher rótulos falsos para silenciar o gate.

## Laboratório de prompt defensivo — opt-in pago

O protocolo completo está no [guia do laboratório](../../../references/laboratorio-defensivo-glm-jev.md).
A partir da pasta desta skill, o resumo seguro é:

```powershell
python3 scripts/defensive_lab.py prepare <novo-dir>
python3 scripts/defensive_lab.py catalog <novo-dir>          # rede pública, sem chave e sem modelo
python3 scripts/defensive_lab.py collect <novo-dir> --candidate original --budget 0.30 --dry-run
node scripts/prompt_builder_rewrite.mjs --directory <novo-dir> \
  --prompt-builder-root C:/Users/kluse/Projects/prompt-builder --budget 0.10 --dry-run
```

`collect --live`, a proposta `--live` e o JEV pago exigem autorização explícita e teto. Não repetir uma
operação cujo desfecho é desconhecido; os journals são barreiras de não-sobrescrita. O adaptador exige
`--approval-hash` do dry-run e recusa outro modelo/provider/effort. Recusas e bloqueios são terminais:
não há troca de modelo, fallback silencioso ou reescrita para contornar um filtro.

O `catalog` consulta endpoints públicos da OpenRouter e **não** envia a chave nem chama modelo; ainda assim
é uma operação de rede. Não confundir com `--dry-run`, que neste projeto é local. O laboratório antigo
continua congelado: o corpus de política nunca passa por `collect` nem pelo reescritor.

## Proveniência, hashes e limites

- Os artefactos em `benchmarks/` são cópias curadas das execuções locais; a pasta `results/` do projeto
  continua a ser o bruto local (fora do Git). Não editar cópias registadas: o hash deixa de bater.
- O manifesto próprio cobre corpus, referências e proveniência. O `datasetHash` do prompt-builder não cobre
  tudo; um `validate` bem-sucedido não certifica origem nem revisão humana.
- Hashes detetam divergência, não autenticam autoria. Um número histórico não é um resultado atual.
- Sem segredos, dados pessoais reais, alvos de produção ou ferramentas reais nas suítes.
- A classificação de um pedido não mede a resposta de um assistente, a resistência a jailbreak ou a
  contenção do runtime. Confiança do JEV não é corretude nem permissão para agir.
- Não usar esta skill para otimizar ataques contra filtros, reduzir deteção ou obter conteúdo nocivo.

## Referências

- [Suítes de teste](<references/suites.md>) — cobertura, garantias offline e como acrescentar testes.
- [Registo de benchmarks](<references/benchmarks.md>) — reprodução, custos, estados e limitações.
- [Guia do laboratório no projeto](<../../../references/laboratorio-defensivo-glm-jev.md>) — protocolo completo.
- [Guia de risco e recusa](<../../../references/casos-risco-e-recusa.md>) — decisões do corpus e proveniência.
