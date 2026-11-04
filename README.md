# bypass-prompt — evidence-led guardrail engineering

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dependencies: stdlib only](https://img.shields.io/badge/deps-stdlib%20only-orange.svg)](#requirements)

A defensive-security agent skill for **authorized** LLM and agent assessments. It connects refusal mechanics, prompt-injection taxonomy, hardened instructions and **deterministic containment** instead of presenting prompts or classifiers as security guarantees.

- **Seven scientific mechanism families**, distinguished from nine local operational groups.
- **50 benign-objective templates** and six documentary model-level techniques; no bundled harmful objectives.
- Three hardened prompt templates, with independent random markers and an **18-control textual lint**, not security certification.
- A proposed **five-layer architecture**, capability/data-flow isolation, MCP/multi-agent provenance, scoped identity, egress and action-bound human approval.
- A [reviewed evidence registry](<references/evidencias.json>) with source versions, denominators, corrections and explicit unknowns.
- Project-local [CoALA discovery](<.agents/bypass-prompt-coala-agent-skill/SKILL.md>) for progressive retrieval rather than dumping the whole study into context.

> **Final evaluation is documentation-only.** At the owner's request, the final testing stage is exclusively the [Markdown guide for /prompt-builder with JEV](<references/avaliacao-prompt-builder-jev.md>). Do not automatically run tests, selftests, benchmarks, dry-runs or evaluation API calls. A future execution requires a new explicit request. No new test suites or CI stages are part of this delivery.

## Intended use

Only systems you own or have written authorization to assess. This is not a jailbreak service. Default objectives are harmless canaries; the local authorization attestation is an audit record, **not proof of permission or comprehensive scope enforcement**.

Tool-using agents need authorization and validation in trusted application code. Neither this skill, a generated system prompt, a successful lint score, nor a JEV decision installs that enforcement.

## Start with the skill and evidence

The main contract is [SKILL.md](<SKILL.md>). The [CoALA source map](<.agents/bypass-prompt-coala-agent-skill/references/acervo.md>) distinguishes the supplied study, reviewed engineering guidance and untrusted external evidence.

Read-only consultations and prompt preparation, not a benchmark run:

```bash
python scripts/bypass.py evidence --id E03 --json
python scripts/bypass.py taxonomy --json
python scripts/bypass.py pipeline --json
python scripts/bypass.py harden --template agentico-pt \
  --tarefa "Summarize authorized documents without external side effects" --out prompt.md
```

`harden` generates instructions only. It does **not** apply datamarking to documents, authenticate MCP metadata, inspect private chain-of-thought, configure a renderer, or install a policy engine.

## What was corrected in the study integration

| Topic | Reviewed interpretation |
| --- | --- |
| Family success rates | The cited taxonomy v2 reports conversation-level success on **Minerva-7B-instruct-v1.0**, with overlapping labels. Older percentages and the claimed selected-task column do not match that version. They are not expected success rates for this tool. |
| GPT-5 detection improvement | 60/91 to 71/91 on **selected successful attacks**, not global accuracy; no benign FPR in that experiment. |
| Constitutional Classifiers++ | One high-risk vulnerability discovered in 198,000 attempts: approximately **0.005 discoveries per 1,000 queries**, not a universal per-query ASR. The ~1% compute estimate and benign-query rate have different contexts. |
| CaMeL | Version-dependent AgentDojo headline; containment depends on trusted inputs, policies, provenance and interpreter correctness. Formal interpreter verification is future work, not an unconditional guarantee. |
| Unicode and encoding | NFKC does not collapse all cross-script confusables. Preserve originals and derived inspection views. Base64 is reversible, not encryption. |
| Runtime controls | Session thresholds are calibration hypotheses. Audit observable requests/actions, not unavailable private reasoning. Signed content can still be false or unsafe. |
| Data integrity | Do not add privacy noise to operational payment amounts, recipients or permissions. |
| Governance | Versioned MITRE ATLAS mappings; NIST alignment is not a compliance certificate or legal safe harbor. |

Details and primary-source links are in the [mechanics reference](<references/mecanica-interna-e-arquitetura-2026.md>) and [evidence registry](<references/evidencias.json>). “Reviewed” means checked against a cited source, **not reproduced here**.

## Capabilities and their boundaries

| Command | Actual scope |
| --- | --- |
| `evidence` | Local evidence lookup, source context and errata; no network |
| `taxonomy` | Scientific families, local groups, techniques and defense mappings |
| `pipeline` | Proposed integration catalog; no deployed firewall or classifiers |
| `harden` | Corporate PT/EN and agentic PT instruction text; new random defaults, explicit reproducible parameters |
| `check` | Heuristic textual lint; `certifica_seguranca: false` even for an acceptable score |
| `authorize` | Required local attestation for `convert` and `eval` only |
| `convert` | Benign test-objective wrappers and fixed multi-turn plans |
| `eval` | Legacy **opt-in** endpoint harness; not the final evaluation procedure for this request |
| `report` | Interprets schema-2 results, with baseline, controls, missingness and escaped target snippets |
| `selftest` | Retained legacy offline capability; **never invoked automatically** by the final guide |

The endpoint harness now distinguishes **diagnostic canary echo** from **violation of an explicitly declared artificial canary policy**. Neither is a measure of harmful-content delivery. Baseline and benign controls stay outside the attack denominator. Invalid/empty responses, timeouts and 5xx are inconclusive, not blocked attacks; complete replies and earlier turns are classified before log truncation.

Result schema is now **version 2**. `asr_forte` is a deprecated alias for artificial-contract ASR and is `null` in diagnostic mode. Legacy result reports are rejected rather than silently relabeled; any future regeneration must be separately authorized. Fixed repeated plans are not adaptive red-teaming. See [metric methodology](<references/metodologia-avaliacao.md>).

The old [sample report](<assets/exemplo-relatorio.md>) and [sample variants](<assets/exemplo-variantes.json>) are preserved historical illustrations, **not current schema-2 output, measured evidence or inputs for the requested JEV stage**. Their old percentages and “echo = strong bypass” interpretation must not be reused.

## Final evaluation: one Markdown, JEV only

Use the [requested final guide](<references/avaliacao-prompt-builder-jev.md>) when planning a future evaluation. It specifies:

- `/prompt-builder` as the skill and `prompt-builder` as its CLI.
- **JEV as the only automated judge**, using imported, human-labeled observations and a pinned decision model.
- No hidden LLM judging fallback, no secrets or real personal data, and no autonomous tool execution.
- Separation of judge calibration, observed system behavior, canary contract, false refusals and containment evidence.
- Budget, authorization, uncertainty, abstention and an explicitly **not executed** status.

The distinction matters: arena `--judge-engine jev` can escalate to an LLM panel. The strict JEV-only route in the guide uses decision-mode evaluation without `models.llm`; it does not pretend that Jev generates agent replies or executes the target.

## Architecture and references

- [Mechanics and corrected study integration](<references/mecanica-interna-e-arquitetura-2026.md>)
- [Taxonomy and documented techniques](<references/taxonomia-e-tecnicas.md>)
- [Defense in depth and containment](<references/defesa-em-profundidade.md>)
- [Measurement methodology](<references/metodologia-avaliacao.md>)
- [Original supplied study](<pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md>) and [historical dossier](<pesquisas/2026-11-04-bypass-guardrails-llm.md>), preserved as reference data with errata notices

## Requirements

Python 3.10+ and the standard library. No dependencies were added. No runtime model downloads, API calls or benchmarks are implied by installation or by reading this repository.

## License

MIT — see [LICENSE](<LICENSE>).
