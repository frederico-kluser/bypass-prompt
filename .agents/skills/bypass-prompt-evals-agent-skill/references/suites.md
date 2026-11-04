# Suítes de teste — cobertura e garantias

## Matriz

| Ficheiro | Alvo | O que prova | O que não prova |
|---|---|---|---|
| `tests/test_defensive_api.py` | Cliente OpenRouter fixo | Modelo exato, provider único, effort `max`, preços/limites, orçamento, redirecionamentos recusados, respostas inválidas/inconclusivas, retries transitórios, recusas terminais, ausência de ferramentas. | Comportamento real de um provider, qualidade do modelo ou segurança de conteúdo. |
| `tests/test_defensive_lab.py` | Laboratório benigno | Corpus congelado, hashes, journals exclusivos, coleta completa, pareamento, missingness, deriva de snapshot, custo/telemetria, bloqueio do corpus de política. | Eficácia de um prompt, calibração do JEV ou contenção do runtime. |
| `tests/test_policy_cases.py` | Corpus de risco/recusa | Schema estrito, 60 IDs únicos, dez categorias, contagens, proveniência `ai`/`humanReviewed:false`, filtros, exportação sem inferência, hashes próprios, escrita exclusiva, barreira de escopo. | Revisão humana, acurácia de classificação ou concordância com um especialista. |
| `tests/test_prompt_builder_rewrite.mjs` | Adaptador prompt-builder | Modelo/provider/effort/teto fixos, sem fallback/ferramentas/decisões, allowlist de destino, bloqueio de rede, recusas terminais, uma correção local, não-replay, pressão de orçamento. | Que uma proposta seja boa, segura ou digna de promoção. |
| `tests/test_benchmark_artifacts.py` | Evidência registada | Hashes do registo, formato dos artefactos, números históricos, ausência de credenciais, configuração JEV-only. | Que os resultados históricos continuem válidos hoje. |

## Garantias offline

- Python usa `unittest` e stdlib; os transportes são objetos falsos injetados, não `fetch`/`socket` reais.
- Node substitui `fetch`, `http`, `https`, `net` e `tls` por tripwires; qualquer tentativa real falha o teste.
- Os diretórios de trabalho são `mkdtemp` e são removidos pelos próprios testes.
- Nenhuma variável de ambiente real é necessária; as chaves usadas nos testes são placeholders sintéticos.
- `run_checks.py` não lê `OPENROUTER_API_KEY`, não consulta catálogo e não chama modelo.
- O único passo de rede em toda a skill é `defensive_lab.py catalog`, que é público, não envia chave e não
  gera inferência; não é executado por `run_checks.py`.

## Requisitos

| Check | Requisito |
|---|---|
| `python` | Python 3.10+ (testado em 3.12). |
| `node` | Node 20.11+ para `node --test`. |
| `project` | `scripts/bypass.py` no projeto; `BYPASS_PROMPT_ROOT` permite outro checkout. |
| `templates` | `scripts/harden.py` no projeto. |
| `registry` | `benchmarks/registry.json` e os artefactos referidos. |

A integração Node importa módulos internos compilados de `C:/Users/kluse/Projects/prompt-builder/dist`.
Se essa instalação não existir, a suíte continua a correr, mas os testes de integração opcionais são
saltados com uma mensagem; não é uma falha de rede nem uma autorização para instalar dependências.

## Como acrescentar um teste

1. Escolher a suíte existente mais próxima; não criar um segundo executor.
2. Injetar transporte/catálogo falsos; nunca usar `fetch`, `socket` ou credenciais reais.
3. Escrever num diretório temporário; nunca alterar `benchmarks/` durante um teste.
4. Asserções devem distinguir **erro**, **inconclusivo** e **resultado válido**. Falha de infraestrutura não
   é bloqueio de segurança.
5. Se o teste criar uma nova evidência histórica, registá-la em `benchmarks/registry.json` com hash e
   limitações — não basta copiar um ficheiro.
6. Correr `python3 scripts/run_checks.py` antes de fechar a alteração.

## Contagem e estabilidade

O número de testes é reportado em tempo real por `run_checks.py`. O registo guarda a contagem da execução
histórica; não usar essa contagem para afirmar que a suíte atual tem o mesmo tamanho. Testes novos devem
ser determinísticos e não depender de ordem, relógio, rede ou estado global.
