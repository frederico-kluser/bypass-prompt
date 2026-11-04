# -*- coding: utf-8 -*-
"""defesa.py — arquitetura de defesa em profundidade do bypass-prompt (estado da arte 2026).

Estrutura os controlos por camada, com limiares acionáveis e ferramentas reais,
para que o relatório de red-team não fique em "recomendações" genéricas. Fonte:
`references/mecanica-interna-e-arquitetura-2026.md` e
`pesquisas/2026-11-04-estudo-tecnico-guardrails-anatomia-bypass-defesa.md`.

Nada aqui é garantia: cada número tem versão de modelo e data. A premissa é
"classifiers are speed bumps; containment is the boundary".
"""

from __future__ import annotations

import json

PIPELINE = [
    {
        "id": 1,
        "nome": "Borda L7 e normalização multi-vista",
        "foco": "Neutralizar ofuscação ortográfica, contrabando Unicode e ataques reciclados antes de consumir GPU.",
        "controlos": [
            "Normalização canónica NFKC em toda a entrada",
            "Strip de zero-width (U+200B–U+200F, U+2060, U+FEFF), bidi e Tags Unicode (U+E0000–U+E007F)",
            "Extração e decodificação multi-vista de candidatos Base64/Hex/ROT13",
            "Assinaturas em todas as vistas: reset de regras, personas, turnos falsos User:/Assistant:, pedido de saída codificada",
        ],
        "ferramentas": ["Agentgateway PromptGuard (L7, sem GPU, Apache 2.0)", "pré-processador NFKC + decodificador multi-vista"],
        "latencia_ms": "<2",
    },
    {
        "id": 2,
        "nome": "Perplexidade, anti-worm RAG e Spotlighting",
        "foco": "Intercetar sufixos otimizados por gradiente e worms auto-replicantes em documentos recuperados.",
        "controlos": [
            "Perplexidade em janela deslizante (window=32, stride=16) + comprimento de tokens em LightGBM",
            "Chunking sobreposto (max_len=512, overlap=64)",
            "Filtro anti-worm em documentos RAG",
            "Datamarking dinâmico k-gram por sessão (1/N^k de adivinhação)",
        ],
        "ferramentas": ["DonkeyRail (TPR 1,0 · FPR 0,017 · 7,6–38,3 ms)", "SmoothLLM em endpoints críticos"],
        "latencia_ms": "7,6–38,3",
    },
    {
        "id": 3,
        "nome": "Classificadores semânticos de entrada",
        "foco": "Detetar override de instruções, role-play parafraseado e injeções indiretas em documentos.",
        "controlos": [
            "Pontuar todos os chunks de 512 tokens e vistas decodificadas",
            "Arrancar em modo shadow/annotate e medir FPR no tráfego real",
            "Bloquear só em pontuação dupla de alta confiança",
        ],
        "ferramentas": [
            "Prompt Guard 2 22M (19,3 ms; 88,7 % recall @1 % FPR)",
            "Prompt Guard 2 86M (92,4 ms; 97,5 % recall @1 % FPR)",
            "Azure Prompt Shields (52 ms)",
            "Lakera Guard (~50 ms) / LLM Guard (50–200 ms)",
        ],
        "latencia_ms": "19–200",
    },
    {
        "id": 4,
        "nome": "Runtime: sessão, auditoria de CoT e guarda de ação",
        "foco": "Bloquear Crescendo, many-shot, H-CoT, alucinação de ferramentas e violação de fluxo de dados.",
        "controlos": [
            "Loop recusa-reformulação: refusals >= 3 E max_cosine > 0,85",
            "Forma many-shot: turnos falsos >= 10 OU input_tokens > tenant_p99",
            "Declive de escalonamento: tendência positiva dos scores brutos em N turnos",
            "Auditoria do CoT contra goal hijacking e alegação 'já verificado'",
            "Validação de chamadas de ferramentas em motor determinístico (CaMeL) com HITL",
        ],
        "ferramentas": [
            "LlamaFirewall (AlignmentCheck + PromptGuard 2; ASR 1,75 %; CodeShield 96 % precisão / 79 % recall)",
            "Granite Guardian 4.1 8B (0,79 balanced accuracy em function-call hallucination)",
            "NeMo Guardrails (Colang, 100–500 ms)",
        ],
        "latencia_ms": "100–500",
    },
    {
        "id": 5,
        "nome": "Saída, DLP, canários e sanitização de renderização",
        "foco": "Prevenir PII/segredos, system prompt leakage, exfiltração por Markdown e respostas nocivas.",
        "controlos": [
            "Alarme A: entrada limpa + saída sinalizada = bypass provável -> bloquear e rever sessão",
            "Alarme B: língua/codificação inesperada (Base64/Hex) na resposta",
            "Alarme C: canary string na saída",
            "Redação regex de PII/segredos + ruído diferencial em constantes de task_summary",
            "Bloquear <img> externo e links Markdown reference-style",
        ],
        "ferramentas": [
            "Presidio (3–15 ms)",
            "Guardrails AI (50–300 ms, Pydantic/JSON)",
            "Qwen3Guard-Stream (0.6B–8B, 119 línguas)",
            "OpenAI Moderation (192 ms, F1 0,899 em dados limpos)",
        ],
        "latencia_ms": "3–300",
    },
]

LIMITES_CLASSIFICADORES = [
    {"controlo": "Azure AI Content Safety", "limpo": "F1 0,928; PII precisão 1,0; 52 ms", "sob_ataque": "F1 0,19–0,61"},
    {"controlo": "AWS Bedrock Guardrails", "limpo": "99 % em factos suportados", "sob_ataque": "F1 0,19–0,61"},
    {"controlo": "Qwen3Guard-8B (UNLV)", "limpo": "91,0 % em prompts conhecidos", "sob_ataque": "33,8 % em ataques inéditos"},
    {"controlo": "Llama Guard 4 (12B)", "limpo": "69 % recall / 11 % FPR", "sob_ataque": "versão 3-8B falhou 78,2 % num teste independente"},
    {"controlo": "Plataforma mais permissiva (Unit 42)", "limpo": "—", "sob_ataque": "interceta 53 % (42/51 role-play passam)"},
    {"controlo": "Plataforma mais agressiva (Unit 42)", "limpo": "13,1 % FPR", "sob_ataque": "bloqueia 92 %; ótimo ~91 % com 0,6 % FPR"},
]

PADROES_ISOLAMENTO = [
    {"id": "D5", "nome": "CaMeL (capacidades + Data Flow Graph)",
     "regra": "P-LLM planeia em pseudo-Python; interpretador verifica capacidades de cada variável antes de cada chamada; violação bloqueia e exige HITL.",
     "evidencia": "77 % no AgentDojo com garantias formais (84 % sem defesa)"},
    {"id": "D5", "nome": "Dual LLM / Quarantined LLM",
     "regra": "Conteúdo não confiável só é lido por um modelo sem ferramentas; o planeador nunca vê o texto hostil.",
     "evidencia": "protege o fluxo de controlo, não o de dados — combinar com CaMeL"},
    {"id": "D5", "nome": "Action-Selector / Plan-Then-Execute",
     "regra": "Sem leitura de saída de ferramentas antes de decidir a ação; plano fixo antes de ler dados.",
     "evidencia": "reduz a superfície de IPI a zero no caminho de decisão"},
    {"id": "D5", "nome": "Assinatura de task_summary e descrições MCP",
     "regra": "Resumos entre agentes e descrições de ferramentas só são aceites se assinados/verificados; read-only em produção.",
     "evidencia": "Tool Output Mimicry passou com 4 camadas ativas (FinBot CTF 19/19)"},
    {"id": "D5", "nome": "Políticas de negócio fora do LLM",
     "regra": "Limites de transferência, destinatários e listas de bloqueio em código determinístico com identidade do chamador.",
     "evidencia": "LLM06:2025 — excessive agency"},
]

TEVV = [
    {"vetor": "CI/CD de aplicação e agentes", "ferramenta": "Promptfoo (MIT) com preset owasp:agentic + plugin MCP",
     "cobre": "injection, memória envenenada, BOLA/BFLA, SSRF a cada PR"},
    {"vetor": "Modelo e tokenizador", "ferramenta": "NVIDIA garak (Apache 2.0, 120+ sondas)",
     "cobre": "sondas estáticas/dinâmicas/adaptativas + glitch tokens ao introduzir modelo/LoRA"},
    {"vetor": "Adversário adaptativo multi-turno", "ferramenta": "Microsoft PyRIT (MIT)",
     "cobre": "Crescendomation, Skeleton Key, TAP, 16 vulnerabilidades agênticas"},
    {"vetor": "Medição", "ferramenta": "higiene de métricas",
     "cobre": "nunca contar erro de infra como bloqueio; safety score; pass@k com FPR"},
    {"vetor": "Produção", "ferramenta": "observabilidade",
     "cobre": "scores contínuos, canários, alarme de discrepância entrada-limpa/saída-suja"},
]

AVISO_METRICO = (
    "ASR é dependente de versão de modelo e data; StrongREJECT mostra que ASRs publicadas são "
    "sobreavaliadas por juízes lenientes; jailbreaks multi-passo degradam o alvo (GPQA Diamond "
    "74 % -> 32 %). Reporte n, runs, baseline, FPR e IC."
)

# Cada camada de defesa (D1–D5) mapeia para uma ou mais camadas do pipeline de runtime.
MAPA_DEFESA_CAMADAS = {
    "D1": [1, 2, 3],
    "D2": [],
    "D3": [4],
    "D4": [5],
    "D5": [],
}

NOTA_DEFESA = {
    "D2": "camada de prompt: gerar e verificar com `bypass.py harden` / `check` (não é inspeção de runtime).",
    "D5": "contenção arquitetural: CaMeL/Dual LLM, assinatura de task_summary e MCP, políticas fora do LLM.",
}


def camadas_para(defesa_id: str) -> dict:
    """Devolve as camadas do pipeline que instrumentam uma defesa D1–D5."""
    ids = MAPA_DEFESA_CAMADAS.get(defesa_id, [])
    return {
        "camadas": [{"id": c["id"], "nome": c["nome"]} for c in PIPELINE if c["id"] in ids],
        "nota": NOTA_DEFESA.get(defesa_id, ""),
    }


def pipeline_json() -> dict:
    return {
        "camadas": PIPELINE,
        "limites_classificadores": LIMITES_CLASSIFICADORES,
        "padroes_isolamento": PADROES_ISOLAMENTO,
        "tevv": TEVV,
        "aviso_metrico": AVISO_METRICO,
    }


def render_pipeline() -> str:
    linhas = ["Pipeline de defesa em profundidade (5 camadas + isolamento)", ""]
    for c in PIPELINE:
        linhas.append("Camada %d — %s  (latência %s ms)" % (c["id"], c["nome"], c["latencia_ms"]))
        linhas.append("  foco: %s" % c["foco"])
        for ctl in c["controlos"]:
            linhas.append("  - %s" % ctl)
        linhas.append("  ferramentas: %s" % "; ".join(c["ferramentas"]))
        linhas.append("")
    linhas.append("Isolamento e contenção (D5):")
    for p in PADROES_ISOLAMENTO:
        linhas.append("  - %s: %s (%s)" % (p["nome"], p["regra"], p["evidencia"]))
    linhas.append("")
    linhas.append("Limites medidos dos classificadores:")
    for lim in LIMITES_CLASSIFICADORES:
        linhas.append("  - %s: limpo=%s | sob ataque=%s" % (lim["controlo"], lim["limpo"], lim["sob_ataque"]))
    linhas.append("")
    linhas.append("Validação contínua (TEVV):")
    for t in TEVV:
        linhas.append("  - %s: %s — %s" % (t["vetor"], t["ferramenta"], t["cobre"]))
    linhas.append("")
    linhas.append("Aviso métrico: %s" % AVISO_METRICO)
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    if "--json" in sys.argv:
        print(json.dumps(pipeline_json(), ensure_ascii=False, indent=2))
    else:
        print(render_pipeline())
