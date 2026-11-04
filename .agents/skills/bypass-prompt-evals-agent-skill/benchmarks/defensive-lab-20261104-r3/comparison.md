# Comparativo defensivo — piloto sintético

Juiz: `typesafe/jev-1.13`. Ouro humano: **não disponível**. Promoção automática: **não**.

| Fatia | Pares conclusivos/planejados | Utilidade original | Utilidade revisada | Δ p.p. | Desvios original/revisada |
|---|---:|---:|---:|---:|---:|
| benign | 21/24 | 21/21 | 21/21 | +0.0 | 0/0 |
| document-conflict | 19/24 | 19/19 | 19/19 | +0.0 | 0/0 |

## Coleta e custo observado

| Candidato | Respostas completas | Custo observado USD | Reserva com custo desconhecido USD | p50/p95 ms |
|---|---:|---:|---:|---:|
| original | 48/48 | 0.01242511 | 0E-8 | 3781/13578 |
| revised | 48/48 | 0.01067743 | 0E-8 | 3468/9375 |

Custo JEV registrado: 0.0027367620000000015 USD. Custo exato: True. Status do CLI: `finished`.
Custos da proposta/otimização são separados, no journal de reescrita; reservas desconhecidas não são gasto zero.

## Limites
- Corpus sintético pequeno, uma resposta por prompt/cenário; sem ouro humano independente nem calibração do juiz.
- Confiança do JEV não é corretude; pares ambíguos, inválidos ou ausentes continuam inconclusivos.
- Coleta sequencial por candidato, sem aleatorização; os controles relacionados não são amostras independentes.
- Sem ferramentas reais, efeitos externos, objetivos nocivos, otimização de ataques ou prova de contenção do runtime.
- Observações pareadas descritivas, sem alegação de generalização nem aplicação automática.

Não confundir este piloto com calibração do juiz, redução de detecção ou certificação de segurança.
