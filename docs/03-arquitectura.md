# 03 · Arquitectura

Paquete: **`planner/`** (no `quickdrop/`: ese nombre es del simulador oficial y colisiona).

```
planner/
  domain/        models.py   -> World, Order, Vehicle, Dataset, Plan (dataclasses frozen, `extra: dict`)
                 geometry.py -> manhattan(a, b)
  io/            readers.py  -> JsonReader, CsvReader + detect_reader(path)   (mapeo español -> dominio)
                 writers.py  -> JsonPlanWriter, CsvPlanWriter
  simulation/    simulator.py  -> simulate(dataset, plan, rules) -> Evaluation
                 objective.py  -> términos de costo componibles
                 validator.py  -> validate(dataset, plan) -> list[str]
  rules/         base.py     -> protocolo Rule + RuleSet
                 registry.py -> REGISTRY y activación por dataset
                 capacity.py, ...  (una regla = un archivo)
  solvers/       base.py          -> protocolo Solver, SolveContext
                 construction/    -> sweep.py, nearest_neighbor.py
                 improvement/     -> two_opt.py, relocate.py, swap.py (operadores de vecindad)
                 orchestrator.py  -> prueba k vehículos, compone fases, devuelve el mejor
  cli.py, __main__.py
tests/           espejo de planner/ + tests/fixtures/practica_n23/ (dataset real de práctica, JSON y CSV)
docs/
```

## Regla de dependencias (se verifica en revisión)
```
cli ──> solvers ──> simulation ──> rules ──> domain
 └────> io ───────────────────────────────> domain
```
`domain` no importa nada del proyecto. `simulation` no importa `solvers`. `rules` solo importa `domain`. `solvers` no lee archivos; `io` no conoce algoritmos.

## Flujo
`cli` → `io.read` → `Dataset` → `RuleSet.from_dataset(dataset)` → `Orchestrator.solve(dataset, rules, ctx)` → `Plan` → `validator.validate` → `io.write` → imprime desglose del costo.

## Contratos clave
```python
@dataclass(frozen=True, slots=True)
class World:
    width: int; height: int; depot: tuple[int, int]; departure: int   # minutos (08:00 -> 480)
    service_time: int; load_time: int; minutes_per_block: int
    cost_per_block: int; cost_per_vehicle: int; cost_per_minute: int; cost_per_failure: int
    extra: Mapping[str, Any]

@dataclass(frozen=True, slots=True)
class Order:   id: int; x: int; y: int; weight: int; extra: Mapping[str, Any]   # weight 0 si falta
@dataclass(frozen=True, slots=True)
class Vehicle: id: str; extra: Mapping[str, Any]                                  # hoy solo id
@dataclass(frozen=True, slots=True)
class Dataset: world: World; orders: Mapping[int, Order]; vehicles: tuple[Vehicle, ...]
@dataclass(frozen=True, slots=True)
class Plan:    routes: Mapping[str, tuple[int | str, ...]]                        # vehicle_id -> paradas ("DEPOSITO" literal)
@dataclass(frozen=True, slots=True)
class Evaluation: total: int; breakdown: Mapping[str, int]; unserved: tuple[int, ...]; violations: tuple[str, ...]

class Rule(Protocol):
    name: str
    def applies(self, dataset: Dataset) -> bool: ...        # se activa solo si el dataset trae sus campos
    def expand(self, vehicle: Vehicle, route: Sequence[int], ds: Dataset) -> Sequence[int | str]: ...  # p. ej. insertar DEPOSITO
    def check(self, vehicle: Vehicle, stops: Sequence[int | str], ds: Dataset) -> list[str]: ...       # factibilidad
    def extra_cost(self, evaluation: Evaluation, ds: Dataset) -> int: ...                                # default 0
    def assignable(self, order: Order, ds: Dataset) -> bool: ...                                         # default True

class Solver(Protocol):
    def solve(self, ds: Dataset, rules: RuleSet, ctx: SolveContext) -> Plan: ...
```
`SolveContext`: `seed`, `deadline` (monotonic), `rng`, `log`.

## Representación interna del solver
Rutas como `list[list[int]]` de ids de pedido (sin `DEPOSITO`), una por vehículo en el orden de `dataset.vehicles`. `rules.expand` las convierte en paradas. El costo siempre se mide con `simulation.simulate`.
**Hoy el `RuleSet` activo está vacío** (sin capacidad en los datos): el plan es una ruta por vehículo, sin `DEPOSITO`.

## Rendimiento
~40 pedidos y ~5 vehículos: evaluar el costo completo por movimiento es suficiente. Optimizar con delta-cost solo si el tiempo de cierre lo exige y con un test que compare delta vs. costo completo.
