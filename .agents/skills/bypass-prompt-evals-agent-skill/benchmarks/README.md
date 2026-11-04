# Benchmarks registados

Cópias curadas dos resultados que o projeto já mediu. O `results/` da raiz continua a ser o bruto local e
está fora do Git; **estas cópias são a evidência versionada** e não devem ser editadas.

> Nota de migração: no relatório histórico copiado, os links para ferramentas e evidências foram ajustados
> para a nova localização. O texto, os números e as limitações não foram alterados.

| Diretório | Estado | Conteúdo |
|---|---|---|
| `defensive-lab-20261104/` | Executado | Prompt original/revisado, 48 observações, registo JEV integral, custos, comparação e relatório. |
| `policy-risk-20261104/` | Exportado, não executado | 60 casos, referências curadas, revisão e configuração JEV-only. |
| `registry.json` | Índice | Tipos, estados, custos, limitações e SHA-256 de cada artefacto. |

## Verificar

```powershell
python3 ../scripts/run_checks.py --only registry
```

A verificação recalcula os hashes e confirma o formato. Também corre como parte de
`python3 ../scripts/run_checks.py` e dos testes Python (`tests/test_benchmark_artifacts.py`).

## Regras

- Não reescrever um artefacto histórico para "melhorar" um resultado. Se um número mudou, criar um novo
  benchmark com novo `id`, data e hashes.
- Não apagar observações inconclusivas, erros, custos desconhecidos ou limitações.
- Um resultado `executed` não é um resultado atual; uma classificação `exported-not-executed` não é uma
  medição.
- Sem ouro humano, não apresentar concordância do JEV como acurácia validada.
- Nenhum destes ficheiros contém chaves, credenciais, dados pessoais reais ou conteúdo operacional nocivo.
