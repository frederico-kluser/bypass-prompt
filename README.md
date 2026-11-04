# bypass-prompt — adversarial rewriting engine for LLM guardrail red-teaming

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Selftest](https://img.shields.io/badge/selftest-30%20scenarios-green.svg)](#verification)
[![Code style: stdlib only](https://img.shields.io/badge/deps-stdlib%20only-orange.svg)](#installation)

**`bypass-prompt`** is a defensive-security toolkit: it converts a test objective —
by default a harmless **canary** — into adversarial variants that exercise
**documented guardrail-bypass techniques** (8 families, 25 techniques), runs them
against a target **under your control**, and returns a findings report that maps
every successful bypass to a **layered defense**. It also generates **hardened
system prompts** and checks them against a 12-control hardening checklist.

Grounded in a deep-research dossier (88 sources, 2023–2026): Wei et al.
(NeurIPS 2023), Shen et al. (CCS 2024), *Guarding the Guardrails* (2025), SoK
PIAtlas (2026), HarmBench, JailbreakBench, OR-Bench, AgentDojo — full study in
[`pesquisas/`](pesquisas/) and [`references/`](references/).

> **Intended use — read this first.** This is a red-team/evaluation tool for
> systems **you own or have written authorization to test**. It is *not* a
> jailbreak service: the default test payload is a canary, no harmful content is
> bundled, and public provider endpoints are blocked by default. Every command
> requires an explicit authorization attestation.

## Quickstart

```bash
# 1. declare authorization (gate — required once)
python scripts/bypass.py authorize --org "Acme" --escopo "internal gateway + local model"

# 2. generate adversarial variants (canary by default)
python scripts/bypass.py convert "echo exactly the marker CANARIO-AB12CD34" --json

# 3. evaluate your target (OpenAI-compatible endpoint you control)
python scripts/bypass.py eval --target https://gateway.internal/v1/chat/completions \
       --model my-model --key-env BYPASS_TARGET_KEY --baseline --out results.json

# 4. findings report with defense recommendations
python scripts/bypass.py report --from results.json

# 5. harden your system prompt — and verify it
python scripts/bypass.py harden --template corporativo-pt --out system_prompt.md
python scripts/bypass.py check --file system_prompt.md
```

## What it does

| Command | Purpose |
| --- | --- |
| `authorize` | registers the authorization attestation (org, scope, expiry) — **required gate** |
| `convert` | generates variants: persona/DAN, PAP persuasion, privilege escalation, skeleton key, many-shot, refusal suppression, Base64/ROT13/leetspeak/low-resource/ASCII-art/emoji/Unicode, payload splitting, RAG/tool-output injection probes, Crescendo & Deceptive Delight multi-turn plans |
| `eval` | runs variants against your endpoint; classifies **refusal / canary-echoed / compliant**; baseline comparison; rate-respecting |
| `report` | findings with per-technique defense recommendation + layered defense map |
| `harden` | hardened system prompts (corporate PT/EN, agentic with MCP/RAG rules) |
| `check` | scores a system prompt against 12 hardening controls |
| `taxonomy` | families × techniques × defenses × references |
| `selftest` | 30 deterministic offline scenarios (gate, canary, base64, plans, classifier, provider guard, eval with injected transport, secret redaction) |

### Attack → defense mapping (core value)

Every variant carries `defesa_id`/`defesa`; every finding in the report comes with
the concrete control that stops it — Spotlighting, instruction hierarchy, session
budget, egress control, least privilege/HITL, MCP tool-pinning. See
[`references/defesa-em-profundidade.md`](references/defesa-em-profundidade.md).

## Key findings baked into the design

- Guardrail triggers organize into **7 mechanism families** + multi-turn + model-level vectors [S1][S2][S4].
- **Persuasion scales with model capability** (PAP >92% ASR even on GPT-4) [S12].
- **Indirect/agentic is the critical family in production**: MCP tool poisoning >60% success on 45+ real servers [S44][S46]; EchoLeak CVE-2025-32711 (CVSS 9.3) zero-click exfiltration [S48].
- **Reasoning models**: CoT hijacking reaches 94–100% ASR [S59].
- **Defenses are quantified but never absolute**: Llama Guard 3 F1 0.939 — yet obfuscation degrades it 24–37% [S77][S85]; Spotlighting >50%→<2% IPI ASR [S81]; Constitutional Classifiers 86%→4.4% with one universal jailbreak found in the public bounty [S80].
- **Measure honestly**: published ASRs are systematically exaggerated [S15]; LLM judges agree with humans only 47–78% in safety [S74] — this tool uses deterministic classification + canary echo by default.

## Installation

```bash
git clone https://github.com/frederico-kluser/bypass-prompt.git
cd bypass-prompt
python scripts/bypass.py selftest   # 30 offline scenarios must PASS
```

Python 3.10+ · **stdlib only** · no network except the endpoint *you* point `eval` at.

## Safety & ethics

- **Authorization gate** — commands refuse without a valid, unexpired attestation; the `AUTH-…` reference is embedded in results (audit trail).
- **Canary by default** — measures whether the *structure* of an attack passes, not whether harm is delivered.
- **Provider guard** — public LLM endpoints (OpenAI, Anthropic, DeepSeek, Mistral, Groq, …) are rejected by `eval` unless you pass `--allow-public-provider` and accept responsibility (your account, their terms).
- **No bundled payloads** — templates wrap *your* test objective; `selftest` asserts no harmful content is embedded.
- **Findings require defenses** — a bypass report without a recommended control is considered incomplete.
- For long automated optimization campaigns (GCG/PAIR/TAP) use [garak](https://github.com/NVIDIA/garak) or [PyRIT](https://github.com/microsoft/PyRIT) — and note the counter-evidence that automated multi-turn ≈ resampling single-turn [S42].

## Repository layout

```
SKILL.md                     agent-skill instructions (the contract)
scripts/bypass.py            CLI: authorize/convert/eval/report/taxonomy/selftest
scripts/strategies.py        25-technique registry with defense mappings + refs
scripts/harden.py            hardened system-prompt templates + hardening checker
references/                  the definitive studies (taxonomy, defense-in-depth, methodology)
pesquisas/                   deep-research dossier (88 sources, verified quotes)
assets/                      example outputs
```

## Verification

`python scripts/bypass.py selftest` runs 30 deterministic offline scenarios and
must exit 0. CI runs it on every push (3.10/3.12/3.14).

## License

MIT — see [LICENSE](LICENSE).
