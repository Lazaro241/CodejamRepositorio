# 06 · Tareas para OpenCode

**Uso**: una tarea por sesión/rama. Pegá el bloque "Prompt". El agente ya lee `AGENTS.md` y `docs/`.
Hay un prototipo previo de referencia (loader, cost, solver, main en un solo bloque): se puede adjuntar para migrar su lógica a esta estructura.

| # | Rama | Tarea | Depende de |
|---|---|---|---|
| T0 | `feat/scaffold` | Esqueleto, packaging, CLI vacío, fixtures | — |
| T1 ∥ | `feat/domain` | Modelos y geometría | T0 |
| T2 ∥ | `feat/io` | Lectores/escritores sobre el formato real | T1 |
| T3 ∥ | `feat/simulation` | Simulador, objetivo, validador, paridad | T1 |
| T4 | `feat/rules-base` | Protocolo `Rule`, `RuleSet`, registro | T3 |
| T5 | `feat/solver-construction` | Barrido + vecino más cercano | T4 |
| T6 | `feat/solver-improvement` | Operadores 2-opt/relocate/swap | T5 |
| T7 | `feat/orchestrator` | Búsqueda sobre k vehículos + presupuesto de tiempo | T6 |
| T8 | `feat/cli-e2e` | CLI completo + test extremo a extremo | T2, T7 |
| T9 | `rule/capacidad` | Primera regla real (plantilla de extensión) | T8 y guía del evento |

Orden mínimo si falta tiempo: T0, T1, T3, T5, T7, T8 (T2 y T4 en versión simple; T9 requiere T4).

---

## T0 · Scaffold
> Creá la estructura de `docs/03-arquitectura.md` con `__init__.py` vacíos, `pyproject.toml` (Python ≥3.11, sin dependencias de runtime; extras `dev`: pytest, ruff), `.gitignore` y `planner/__main__.py` que llame a `planner.cli.main`. `cli.main` acepta los argumentos de `AGENTS.md` y por ahora solo imprime "no implementado". Dejá `tests/fixtures/practica_n23/` tal como está. Test de humo que importe el paquete.

**Aceptación:** `pip install -e .[dev]`, `pytest -q` y `python -m planner --help` funcionan.

## T1 · Dominio
> Implementá `planner/domain/models.py` y `geometry.py` según el contrato de `03-arquitectura.md`. Inmutables, sin I/O. `Order.weight` es `int` (0 si falta), `Vehicle` solo tiene `id: str` + `extra`. `World.departure` en minutos. Tests de construcción e inmutabilidad.

**Aceptación:** cero imports de otras capas; `ruff` limpio.

## T2 · I/O (formato real)
> Implementá `planner/io/readers.py` y `writers.py` siguiendo **exactamente** `docs/02-formato-datos.md`. Lectores JSON y CSV (`mundo` CSV es `clave,valor`; `hora_salida "HH:MM"` → minutos; `pedidos.json` lista de objetos; `vehiculos` solo `id`). Tolerar campos opcionales ausentes/`null`/vacíos; campos desconocidos van a `extra`; BOM y CRLF. `detect_reader` prefiere JSON. Escritores de plan JSON/CSV sin vehículos vacíos. Errores con `DatasetError`. Test principal: leer `tests/fixtures/practica_n23` en JSON y en CSV ⇒ **mismo `Dataset`** (40 pedidos, 5 vehículos `V1..V5`, depósito (0,0), `departure == 480`, suma de pesos 455). Tests extra con depósito ≠ (0,0), ids de pedido no consecutivos y una columna desconocida en `vehiculos` (debe aparecer en `Vehicle.extra`).

**Aceptación:** JSON y CSV equivalentes; ningún campo del dataset hardcodeado.

## T3 · Simulación
> Implementá `planner/simulation/`: `simulate(dataset, plan, rules) -> Evaluation` replicando el simulador oficial (`01-contexto.md`), `objective.py` con `CostTerm` componibles y `validator.py` (vehículo inexistente/repetido, pedido inexistente/repetido). Vehículo "usado" = tiene ≥1 entrega. Test de paridad: caso del enunciado (25 pedidos, 2 vehículos → 2641, desglose 430/2/1231/0) y un plan sobre `practica_n23` cuyo costo completarás corriendo `python -m quickdrop simular`.

**Aceptación:** el costo local coincide con el oficial en ambos casos.

## T4 · Base de reglas
> Implementá `planner/rules/base.py` (`Rule` Protocol con defaults neutros), `RuleSet` (aplica las reglas activas en orden; `RuleSet.from_dataset`) y `registry.py`. Sin reglas concretas: con `RuleSet` vacío `expand` devuelve la ruta intacta. Integralo en `simulate`. Tests con una regla falsa que inserta `DEPOSITO` cada 2 pedidos y solo se activa si `Vehicle.extra` trae un campo de prueba.

**Aceptación:** con `practica_n23` (sin campos nuevos) el `RuleSet` queda vacío y el costo no cambia.

## T5 · Construcción
> Implementá `SweepConstructor` (ordena pedidos por ángulo alrededor del **depósito del dataset**, los parte en k grupos balanceados, con rotación de inicio) y `nearest_neighbor(group, depot)`. Interfaz `Constructor.build(ds, k, offset) -> list[list[int]]`. Tests: cada pedido aparece exactamente una vez; k grupos; depósito en (10,10); un solo pedido; k mayor que pedidos.

## T6 · Mejora local
> Implementá `TwoOpt`, `Relocate`, `Swap` con `Operator.neighbors(routes)` y `LocalSearch(operators, evaluate)` de primera mejora con `deadline`. `evaluate` se inyecta. Tests: el costo nunca empeora; respeta el deadline; agregar un operador no requiere editar `LocalSearch`.

## T7 · Orquestador
> `solvers/orchestrator.py`: para k = 1..min(#vehículos, #pedidos) y algunos offsets, construye, mejora y se queda con el menor costo según `simulation.simulate` con el `RuleSet` activo. Respeta `ctx.deadline`. Pedidos que ninguna regla permite asignar quedan fuera (fallan). Loguea costo por k. Tests: plan siempre válido; con `costo_por_vehiculo` enorme usa 1 vehículo; con costo de vehículo 0 y `costo_por_minuto_total` alto usa más de 1.

**Aceptación:** tabla k → costo en el log (material para el pitch).

## T8 · CLI extremo a extremo
> Completá `planner/cli.py`: leer → `RuleSet.from_dataset` → solver → `validator` (si falla, error y exit≠0) → escribir JSON (y CSV con `--csv`) → imprimir desglose. Flags `--seed`, `--budget`. Test e2e sobre `practica_n23` y sobre su variante con depósito (10,10).

**Aceptación:** costo del CLI = costo de `python -m quickdrop simular`.

## T9 · Primera regla real: capacidad (plantilla para todos los eventos)
> **Antes de empezar**, confirmá en la guía del evento el nombre real del campo (p. ej. `capacidad` en `vehiculos`) y su semántica. Implementá `planner/rules/capacity.py`: se activa solo si algún `Vehicle.extra` trae el campo; `expand` inserta `DEPOSITO` cuando el peso acumulado superaría la capacidad; pedidos con peso mayor a la mayor capacidad ⇒ no asignables (`assignable=False`). Registrala. **No modifiques solvers, `io` ni simulador.** Si no podés, detenete y explicá qué abstracción falta. Tests: no aplica con `practica_n23` actual; con una copia del fixture + columna `capacidad` parte rutas; el plan resultante coincide con el simulador oficial actualizado.

**Aceptación:** diff limitado a `rules/` + tests.

---

## Plantilla para tareas de eventos
> Evento N trae la regla «<descripción de la guía>». Campos nuevos: <lista, en qué archivo>. Hacé `git pull` del simulador y primero añadí/actualizá el test de paridad con su costo oficial. Luego implementá `planner/rules/<nombre>.py` según `docs/04-patrones.md#cómo-se-ve-agregar-una-regla`. No toques solvers ni `io` salvo que `Rule` no alcance; en ese caso proponé el cambio mínimo a la interfaz antes de implementarlo y anotalo en `docs/BITACORA.md`.
