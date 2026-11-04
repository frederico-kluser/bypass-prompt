# bypass-prompt — adversarial rewriting engine for LLM guardrail red-teaming

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Selftest](https://img.shields.io/badge/selftest-51%20scenarios-green.svg)](#verification)
[![Code style: stdlib only](https://img.shields.io/badge/deps-stdlib%20only-orange.svg)](#installation)

**`bypass-prompt`** is a defensive-security toolkit: it converts a test objective —
by default a harmless **canary** — into adversarial variants that exercise
**documented guardrail-bypass techniques** (9 families, 50 convertible techniques plus
6 model-level techniques), runs them against a target **under your control**, and
returns a findings report that maps every successful bypass to a **layered defense**,
including the concrete **5-layer runtime pipeline** to instrument. It also generates
**hardened system prompts (v2026)** and checks them against an **18-control** checklist.

Grounded in a deep-research dossier (88 sources, 2023–2026) and a 2026 technical study:
Wei et al. (NeurIPS 2023), Arditi et al. (2024, refusal direction), *Guarding the
Guardrails* (2025), SoK PIAtlas (2026), Anthropic Constitutional Classifiers++ (2025/ICLR
2026), CaMeL (2025), EchoLeak (CVE-2025-32711), Morris II (CCS 2025), H-CoT (2025),
HarmBench, JailbreakBench, AgentDojo, OR-Bench, StrongREJECT — full material in
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
       --model my-model --key-env BYPASS_TARGET_KEY --baseline --runs 3 --out results.json

# 4. findings report with defense recommendations, CIs and pipeline mapping
python scripts/bypass.py report --from results.json

# 5. harden your system prompt — and verify it
python scripts/bypass.py harden --template corporativo-pt --canario CANARIO-INT-1 --out system_prompt.md
python scripts/bypass.py check --file system_prompt.md

# 6. print the defense-in-depth pipeline
python scripts/bypass.py pipeline
```

## What it does

| Command | Purpose |
| --- | --- |
| `authorize` | registers the authorization attestation (org, scope, expiry) — **required gate** |
| `convert` | generates variants: persona/DAN/Dr. House, PAP persuasion, Skeleton Key, Policy Puppetry, hardware override, compound conflict, many-shot, math decomposition, refusal suppression, Base64/ROT13/leetspeak/low-resource/ASCII-art/emoji/zero-width/**Unicode Tag smuggling**/typoglycemia/euphemism/CodeAttack/synthetic language/fragment reassembly, payload splitting, RAG/tool-output/MCP/delegation-chain injection, Crescendo/Deceptive Delight/**Echo Chamber/Bad Likert Judge/CCA** multi-turn plans and **H-CoT/CoT padding** |
| `eval` | runs variants against your endpoint; classifies **refusal / canary-echoed / compliant**; `--runs R` measures pass@k; Wilson 95% CI; baseline comparison; rate-respecting |
| `report` | measurement conditions, findings with per-technique defense + pipeline layers, metric caveats |
| `pipeline` | the 5-layer runtime defense with thresholds, tools and latencies + isolation patterns + TEVV |
| `harden` | hardened system prompts (corporate PT/EN, agentic with MCP/RAG rules), per-session canary, nonce and datamarking |
| `check` | scores a system prompt against **18 hardening controls** (anti-mimicry, anti-H-CoT, anti-Bad-Likert, anti-exfiltration, canary, datamarking, …) |
| `taxonomy` | families (with empirical ASR) × convertible/documentary techniques × defenses × references |
| `selftest` | 51 deterministic offline scenarios (gate, canary, base64, Unicode tags, plans, classifier, provider guard, eval with injected transport, pass@k, CI, report, harden, pipeline, secret redaction) |

### Attack → defense mapping (core value)

Every variant carries `defesa_id`/`defesa`; every finding in the report names the
concrete controls and the **pipeline layers** that stop it — Spotlighting with dynamic
datamarking, instruction hierarchy, session metrics (`refusals ≥ 3` & `max_cosine > 0.85`),
egress control, CaMeL-style capability enforcement, least privilege/HITL, MCP
signature pinning. See [`references/defesa-em-profundidade.md`](references/defesa-em-profundidade.md)
and [`references/mecanica-interna-e-arquitetura-2026.md`](references/mecanica-interna-e-arquitetura-2026.md).

## Key findings baked into the design

- **Mechanism beats keyword**: refusal is mediated by a single linear direction in the residual stream, removable by directional ablation in all layers — so safety is a property of weights and containment, not of a regex.
- **The 2026 ASR ranking inverts intuition**: obfuscation is the *least* effective family (3.2% on selected tasks) yet absorbs most regex effort; persuasion (17.1%), data poisoning (16.9%) and impersonation (14.3%) lead; effective jailbreaks are compound (≥5 sub-techniques).
- **Indirect/agentic is the critical family in production**: MCP tool poisoning >60% on 45+ real servers; Tool Output Mimicry defeated a 4-layer agent pipeline (FinBot CTF 19/19); EchoLeak (CVE-2025-32711, CVSS 9.3) zero-click exfiltration; Morris II/RAGworm >90% replication through hop 11.
- **Multi-turn and reasoning hijacks are the high-ASR end**: Crescendo 63.2% ASR / 91% coverage on HarmBench; Bad Likert Judge ~71.6%; Echo Chamber >90%; H-CoT drops o1/o3 refusal below 2% — <2% is also what an isolated output guardrail catches.
- **Defenses are quantified but never absolute**: instruction hierarchy +63%; Spotlighting >50%→<2% IPI ASR (dynamic datamarking, 1/N^k guessing); Circuit Breakers 87%→14%; CC++ 0.005 jailbreaks/1,000 queries at ~1% overhead; CaMeL 77% AgentDojo with formal guarantees — yet an adaptive attacker bypassed 12 published defenses >90% of the time.
- **Measure honestly**: published ASRs are systematically exaggerated (StrongREJECT); LLM judges agree with humans only 47–78% in safety; adaptive multi-step jailbreaks degrade the target from 74% to 32% on GPQA Diamond. This tool reports pass@k, Wilson CIs, FPR-friendly baseline comparisons and deterministic classification by default.

## Installation

```bash
git clone https://github.com/frederico-kluser/bypass-prompt.git
cd bypass-prompt
python scripts/bypass.py selftest   # 51 offline scenarios must PASS
```

Python 3.10+ · **stdlib only** · no network except the endpoint *you* point `eval` at.

## Safety & ethics

- **Authorization gate** — commands refuse without a valid, unexpired attestation; the `AUTH-…` reference is embedded in results (audit trail).
- **Canary by default** — measures whether the *structure* of an attack passes, not whether harm is delivered.
- **Provider guard** — public LLM endpoints (OpenAI, Anthropic, DeepSeek, Mistral, Groq, …) are rejected by `eval` unless you pass `--allow-public-provider` and accept responsibility (your account, their terms).
- **No bundled payloads** — templates wrap *your* test objective; `selftest` asserts no harmful content is embedded.
- **Findings require defenses** — a bypass report without a recommended control (and the layer to instrument) is considered incomplete.
- For long automated optimization campaigns (GCG/PAIR/TAP) use [garak](https://github.com/NVIDIA/garak) or [PyRIT](https://github.com/microsoft/PyRIT); for CI/CD of applications and agents use Promptfoo with the `owasp:agentic` preset — and note the counter-evidence that automated multi-turn ≈ resampling single-turn.

## Repository layout

```
SKILL.md                     agent-skill instructions (the contract)
scripts/bypass.py            CLI: authorize/convert/eval/report/harden/check/pipeline/taxonomy/selftest
scripts/strategies.py        50-technique registry with defense mappings, ASR metadata and refs (+6 documentary)
scripts/harden.py            hardened system-prompt templates (v2026) + 18-control checker
scripts/defesa.py            5-layer defense pipeline, classifier limits, isolation patterns, TEVV
references/                  the definitive studies (internal mechanics, taxonomy, defense-in-depth, methodology)
pesquisas/                   deep-research dossier + 2026 technical study (primary sources)
assets/                      example outputs
```

## Verification

`python scripts/bypass.py selftest` runs 51 deterministic offline scenarios and
must exit 0. CI runs it on every push (3.10/3.12/3.14) and checks that the hardened
template passes all 18 controls.

## License

MIT — see [LICENSE](LICENSE).
