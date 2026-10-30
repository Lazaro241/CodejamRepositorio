# 04 · Patrones de diseño: dónde sí, dónde no

Criterio: **un patrón entra si ya hay (o el enunciado anticipa) ≥ 2 variantes**. Si no, función simple.

| Necesidad | Patrón | Dónde | Ejemplo concreto |
|---|---|---|---|
| Leer JSON o CSV; escribir JSON o CSV | **Strategy + Factory** (`detect_reader`) | `io/` | Agregar otro formato = 1 clase nueva |
| Reglas que aparecen por evento | **Registry + Chain of Responsibility** (`RuleSet` aplica cada `Rule` activa en orden) | `rules/` | `CapacityRule`, luego `TimeWindowRule` |
| Distintos algoritmos de construcción | **Strategy** | `solvers/construction/` | `SweepConstructor`, `NearestNeighbor` |
| Movimientos de búsqueda local | **Strategy** sobre operadores de vecindad | `solvers/improvement/` | 2-opt, relocate, swap; agregar `or-opt` sin tocar el loop |
| Fases del solver | **Pipeline** (`Plan -> Plan`) | `solvers/orchestrator.py` | construir → mejorar → comparar k |
| Costo con términos que se suman | **Composite** de `CostTerm` | `simulation/objective.py` | distancia, vehículos, makespan, fallas, + términos de reglas |
| Datos inmutables | **Value Object** (dataclass frozen) | `domain/`, `simulation/` | `Dataset`, `Plan`, `Evaluation` |
| Semilla/deadline compartidos | **Context Object** | `solvers/base.py` | `SolveContext` |

## Cómo se ve "agregar una regla" (criterio de éxito del diseño)
1. Crear `planner/rules/<nombre>.py` con una clase que cumpla `Rule`; `applies()` mira si el dataset trae sus campos (p. ej. una columna nueva en `vehiculos`, que llega en `Vehicle.extra`).
2. Registrarla en `rules/registry.py`.
3. Test en `tests/rules/test_<nombre>.py`, incluyendo "no aplica" con el dataset de práctica actual (sin campos nuevos ⇒ el costo no cambia).
4. **No se edita** ningún solver, ni el CLI, ni `io` (los campos nuevos ya viajan en `extra`). Solo `simulation/` si el simulador oficial cambió, junto con su test de paridad.

## Anti-patrones (rechazar en revisión)
- `if dataset.tiene_capacidad:` dentro del solver o del simulador → va en una `Rule`.
- Interpretar columnas nuevas dentro de `io`: `io` solo las pasa a `extra`.
- Singletons globales mutables, estado en módulos, `import *`.
- Herencia profunda. Preferir composición y `Protocol`.
- Clases "Manager"/"Helper"/"Utils" sin responsabilidad clara.
- Factories o ABCs con una sola implementación y ninguna prevista.
- Excepciones tragadas (`except: pass`).

## SOLID aplicado (versión corta)
S: un archivo, una razón de cambio. O: se extiende registrando clases, no editando. L/I: `Protocol` chicos. D: el solver recibe `Dataset`, `RuleSet` y `SolveContext`; nunca abre archivos ni lee globals.
