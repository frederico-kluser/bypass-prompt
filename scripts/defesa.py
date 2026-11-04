# -*- coding: utf-8 -*-
"""Catálogo de arquitetura defensiva, não um firewall instalado.

As cinco camadas são propostas de integração externa. Este módulo NÃO instala
classificadores, não acessa ativações/CoT privado e não impõe políticas em outros
agentes. Evidências e limites: references/evidencias.json, revisão 2026-11-04.
"""
from __future__ import annotations

import json

PIPELINE = [
    {
        "id": 1, "nome": "Borda L7 e inspeção Unicode multi-vista",
        "foco": "Inspecionar representações alternativas sem perder original, sem executar payloads e sem corromper conteúdo legítimo.",
        "controlos": [
            "Preservar original/proveniência; criar vista NFKC (compatibilidade, não colapso universal de homóglifos)",
            "Sinalizar tags U+E0000–U+E007F, bidi e invisíveis; remoção apenas em vista derivada e conforme idioma/contexto",
            "Confusables/mixed-script exigem análise adicional UTS39, não substituição cega de identidades",
            "Decodificar candidatos Base64/Hex/ROT13 só para inspeção, com tetos de bytes, expansão, profundidade e tempo",
            "Aplicar autorização/validação sobre a representação final usada pela ferramenta, evitando divergência de parsers",
        ],
        "ferramentas": ["unicodedata + análise UTS39 externa", "gateway L7 e limites de recursos"],
        "latencia_ms": None, "evidencias": ["E08"],
    },
    {
        "id": 2, "nome": "Proveniência, RAG em quarentena e Spotlighting",
        "foco": "Manter conteúdo recuperado no plano de dados; detectar replicação sem promover documentos a instruções.",
        "controlos": [
            "Aplicar delimitação/datamarking por código confiável antes da inferência; renderizar prompt não transforma documentos",
            "Marcadores novos por invocação e escape de colisões; 1/N^k não é limite de ASR nem autenticação",
            "Quarentena por item, rótulos de origem, minimização de contexto e inspeção de conteúdo auto-replicante",
            "Perplexidade opcional para ruído/sufixos: não detecta necessariamente persuasão fluente e pode gerar FPs em código/línguas",
            "Janelas 32/stride16 e chunks512/overlap64 são exemplos a calibrar com o tokenizer do detector",
        ],
        "ferramentas": ["Spotlighting (integração externa)", "filtro anti-worm a selecionar e validar localmente"],
        "latencia_ms": None, "evidencias": ["E07", "E11", "E12"],
    },
    {
        "id": 3, "nome": "Sensores semânticos de entrada",
        "foco": "Detectar tentativas de sobrescrever instruções, separando intenção de injeção, nocividade e autorização.",
        "controlos": [
            "Inspecionar dados externos e entrada de usuário sem perder a distinção de autoridade entre os canais",
            "Começar em shadow; medir precisão/recall/FPR por tenant, idioma, tipo de documento e ataques inéditos",
            "Não tratar scores como probabilidades calibradas sem calibração; dois sensores correlacionados não são independentes",
            "No Prompt Guard 2, respeitar limite de 512 tokens e cobertura de bordas/chunks; 22M é menos multilíngue",
        ],
        "ferramentas": ["Prompt Guard 2 22M/86M (escopo/model card em E09)", "classificador de nocividade separado quando necessário"],
        "latencia_ms": None, "evidencias": ["E09", "E11"],
    },
    {
        "id": 4, "nome": "Runtime: sessão e guarda determinística de ação",
        "foco": "Conter ações e fluxo de dados mesmo quando o modelo aceita contexto adversarial.",
        "controlos": [
            "Estado no servidor por identidade/tenant; histórico autenticado, anti-replay, limites de consultas/tokens e expiração",
            "Hipóteses a calibrar: refusals>=3 com cosine>0.85; turnos fabricados>=10; tokens>tenant_p99; tendência de scores",
            "Não confundir citação, mudança legítima de tarefa ou decodificação benigna com violação automática",
            "Auditar apenas pedido, contexto autorizado, respostas públicas, chamadas/argumentos e decisões observáveis; não exigir CoT privado",
            "Validar ferramenta, schema, valores, destinatário, recurso e capacidade de leitura/escrita em código fora do LLM",
            "HITL vinculado a ação/args/tenant/identidade/expiração, anti-replay e revalidação atômica no uso (TOCTOU)",
        ],
        "ferramentas": ["interpretador/policy engine com capacidades (padrão CaMeL)", "runtime de identidade e aprovação humana"],
        "latencia_ms": None, "evidencias": ["E05", "E11", "E16"],
    },
    {
        "id": 5, "nome": "Saída, DLP, egress e renderização segura",
        "foco": "Evitar vazamento e efeitos de renderização antes de expor bytes ou executar ferramentas.",
        "controlos": [
            "Alarme A: entrada não sinalizada + saída sinalizada exige investigação, não prova automática de bypass",
            "Alarme B: idioma/codificação inesperados exigem avaliar escopo e significado, não banir tarefas multilíngues legítimas",
            "Alarme C: eco inesperado de canário é sensor; eco de marcador público autorizado não comprova comprometimento",
            "DLP minimiza/redige segredos/PII; nunca adicionar ruído a valores financeiros, destinatários ou permissões operacionais",
            "Renderizador não faz fetch de imagens/links não aprovados; resolver destinos e impedir SSRF/redirects por política externa",
            "Verificar buffers/streaming antes da emissão: bytes já entregues não podem ser des-exfiltrados",
        ],
        "ferramentas": ["DLP/Presidio ou equivalente a integrar", "sanitizador de HTML/Markdown e proxy de egress deny-by-default"],
        "latencia_ms": None, "evidencias": ["E10", "E12", "E16"],
    },
]

# Comparações numéricas heterogêneas do estudo não são um ranking de fornecedores.
LIMITES_CLASSIFICADORES = [
    {"controlo": "Prompt Guard 2", "limpo": "model card: recall inglês 88,7%/97,5% @1% FPR; A100 512 tokens 19,3/92,4ms", "sob_ataque": "benchmark privado; não é FPR/latência do nosso tráfego; E09"},
    {"controlo": "Classificador lexical/perplexidade", "limpo": "sensor opcional", "sob_ataque": "persuasão fluente e conteúdo legítimo raro limitam generalização"},
    {"controlo": "CC++", "limpo": "~1% compute estimado Opus 4.0; 0,05% benignos Sonnet 4.5 no relato", "sob_ataque": "1 descoberta alto risco/198000 tentativas; não ASR universal; E03/E04"},
    {"controlo": "Azure/AWS/Lakera/LLM Guard", "limpo": "números comparativos não revalidados nesta revisão", "sob_ataque": "sem protocolo comum, não comparar F1/recall/latência como uma mesma métrica; E12"},
    {"controlo": "Qwen/Llama Guard/Granite/CodeShield", "limpo": "escopos distintos: nocividade, injeção, código, ação", "sob_ataque": "não transferir resultado de uma tarefa/modelo para outra; E12"},
    {"controlo": "Juiz JEV", "limpo": "decisões tipadas sobre corpus com ouro humano", "sob_ataque": "estado externo pode induzir erro; calibrar em pt-BR e abster; nunca autoriza ferramenta"},
]

PADROES_ISOLAMENTO = [
    {"id": "D5", "nome": "CaMeL (capacidades + proveniência)",
     "regra": "Planejador não lê dados hostis; interpretador confiável rotula variáveis e medeia cada fluxo/ação sob política explícita.",
     "evidencia": "headline v2: 77% vs84% AgentDojo; pressupostos/limites e verificação formal futura em E05"},
    {"id": "D5", "nome": "Dual LLM / modelo em quarentena",
     "regra": "Modelo que lê dados externos não tem ferramentas; saídas extraídas continuam não confiáveis, inclusive argumentos.",
     "evidencia": "isolamento de controle não basta para integridade/autorização do fluxo de dados"},
    {"id": "D5", "nome": "Plan-Then-Execute / Action-Selector / Map-Reduce",
     "regra": "Fixar ações antes dos dados ou isolar leitura por item; ainda validar argumentos, destinatários e proveniência.",
     "evidencia": "redução de superfície sob pressupostos; não afirmar IPI zero"},
    {"id": "D5", "nome": "Envelopes autenticados de agentes e MCP",
     "regra": "Assinaturas/verificação fora do LLM, schema e binding a tarefa/tenant/origem/versão/expiração; descrições pinadas e read-only.",
     "evidencia": "assinatura prova origem/integridade, não veracidade nem autorização; E16"},
    {"id": "D5", "nome": "Políticas de negócio e HITL fora do LLM",
     "regra": "Limites, recursos, destinatários e efeitos são validados na identidade do chamador; nenhuma string de aprovação em dados basta.",
     "evidencia": "aprovação concreta, única/expirável e revalidada na execução; E16"},
]

TEVV = [
    {"vetor": "Etapa final deste projeto", "ferramenta": "references/avaliacao-prompt-builder-jev.md",
     "cobre": "somente roteiro Markdown; não executar testes/benchmarks/dry-run automaticamente"},
    {"vetor": "Juiz único planejado", "ferramenta": "/prompt-builder em modo JEV com typesafe/jev-1.13",
     "cobre": "casos importados com ouro humano, decisões atômicas, incerteza e revisão humana; sem painel LLM implícito"},
    {"vetor": "Métricas futuras", "ferramenta": "planejamento documental",
     "cobre": "ASR contratual vs eco, FPR benigna, utilidade, cobertura, erros, versão/data, custo e limites"},
    {"vetor": "Ferramentas citadas na literatura", "ferramenta": "Promptfoo / garak / PyRIT",
     "cobre": "referências do estudo, não execução nem etapa final adotada neste pedido"},
]

AVISO_METRICO = (
    "Eco de canário público não comprova bypass. ASR exige contrato de sucesso explícito; "
    "versão, data, orçamento e corpus condicionam cada taxa. Erros são inconclusivos, "
    "baseline/benignos ficam separados e repetição fixa não é ataque adaptativo. "
    "Wilson é descritivo sob correlação; reporte cobertura, FPR e utilidade. Fontes/ressalvas em E01–E16."
)

MAPA_DEFESA_CAMADAS = {"D1": [1, 2, 3], "D2": [], "D3": [4], "D4": [5], "D5": []}
NOTA_DEFESA = {
    "D2": "Camada de instruções: harden gera só texto; check é lint, não certificação.",
    "D5": "Integração externa de capacidades/identidade/políticas/HITL; este catálogo não a implementa.",
}


def camadas_para(defesa_id: str) -> dict:
    ids = MAPA_DEFESA_CAMADAS.get(defesa_id, [])
    return {"camadas": [{"id": c["id"], "nome": c["nome"]} for c in PIPELINE if c["id"] in ids],
            "nota": NOTA_DEFESA.get(defesa_id, "")}


def pipeline_json() -> dict:
    return {"estado": "catalogo-proposto-nao-instalado", "metricas_locais": "nao-medidas",
            "camadas": PIPELINE, "limites_classificadores": LIMITES_CLASSIFICADORES,
            "padroes_isolamento": PADROES_ISOLAMENTO, "tevv": TEVV, "aviso_metrico": AVISO_METRICO}


def render_pipeline() -> str:
    linhas = ["Pipeline proposto (5 camadas + contenção; NÃO instalado por este módulo)",
              "Latências locais: não medidas. Números externos exigem contexto/versionamento.", ""]
    for c in PIPELINE:
        linhas.append("Camada %d — %s" % (c["id"], c["nome"]))
        linhas.append("  foco: %s" % c["foco"])
        linhas.extend("  - %s" % ctl for ctl in c["controlos"])
        linhas.append("  integrações propostas: %s" % "; ".join(c["ferramentas"]))
        linhas.append("  evidências: %s\n" % ", ".join(c["evidencias"]))
    linhas.append("Isolamento e contenção (D5):")
    linhas.extend("  - %s: %s (%s)" % (p["nome"], p["regra"], p["evidencia"]) for p in PADROES_ISOLAMENTO)
    linhas.append("\nLimites dos sensores:")
    linhas.extend("  - %s: %s | %s" % (l["controlo"], l["limpo"], l["sob_ataque"]) for l in LIMITES_CLASSIFICADORES)
    linhas.append("\nTEVV planejado (sem execução):")
    linhas.extend("  - %s: %s — %s" % (t["vetor"], t["ferramenta"], t["cobre"]) for t in TEVV)
    linhas.append("\nAviso métrico: %s" % AVISO_METRICO)
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    print(json.dumps(pipeline_json(), ensure_ascii=False, indent=2) if "--json" in sys.argv else render_pipeline())
