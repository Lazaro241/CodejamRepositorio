# Bitácora de decisiones (insumo del pitch)

| Hora | Decisión | Alternativas | Números (antes → después) | Quién |
|---|---|---|---|---|
| — | Baseline del prototipo sobre `practica_n23` (local, sin confirmar con el oficial) | — | costo ≈ 971 (2 vehículos, 162 cuadras, 365 min, 0 fallas) | — |
| — | T3 simulation: réplica línea por línea del simulador oficial (`planner/simulation/`), paridad fijada ejecutando `python -m quickdrop simular` | Composite de `CostTerm` vs fórmula fija (elegimos Composite por docs/04: reglas nuevas agregan términos); `rules` duck-typed hasta T4 | caso del enunciado reproducido EXACTO **2641** (430 cuadras×3 + 2×60 + 1231 min + 0 fallas, dataset sintético `tests/fixtures/enunciado_25`); `ejemplo` del simulador **1013** (594/180/239/0); `practica_n23` + plan de referencia (chunks secuenciales de 8) **2674** (1908/300/466/0) | OpenCode |
