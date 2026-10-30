# 05 · Convenciones, tests y Git

## Código
- Python 3.11+, `from __future__ import annotations`, type hints en API pública.
- `dataclass(frozen=True, slots=True)` para modelos; `tuple`/`Mapping` en el dominio.
- Nombres de dominio en inglés (`Order`, `Vehicle`); los **nombres de campo de archivo** (`costo_por_cuadra`, `deposito_x`) viven solo en `io/`, que los mapea al dominio.
- Funciones cortas (< 40 líneas), sin efectos laterales fuera de `io/` y `cli.py`.
- `logging`, no `print` (salvo la salida final del CLI).
- Errores propios (`DatasetError`, `PlanError`) con mensajes accionables ("pedido 7: y=25 fuera de la grilla 20x20").
- `ruff check` + `ruff format`. Comentarios para el *porqué*, no para repetir el código.

## Tests
- `pytest`; un archivo por módulo; fixtures en `tests/fixtures/`.
- **Fixture real**: `tests/fixtures/practica_n23/` (JSON y CSV). Test: ambos formatos dan el mismo `Dataset` con 40 pedidos, 5 vehículos, depósito (0,0), `departure == 480`, `sum(weights) == 455`.
- **Variantes derivadas** (se generan en el test, no se commitean): mismo dataset con depósito en (10,10) y otros costos; con 1 vehículo; con ids de pedido no consecutivos; con campos extra y `null`/vacíos.
- **Paridad con el simulador oficial** (`tests/simulation/test_parity.py`): planes fijos con el costo que devolvió `python -m quickdrop simular`. Caso del enunciado: 25 pedidos → **2641**. Agregar un plan sobre `practica_n23` con su costo oficial.
- **Propiedades del solver** (semilla fija): plan siempre válido; ningún pedido repetido; sin usar más vehículos de los que hay; funciona con depósito ≠ (0,0).
- **Regresión de calidad**: sobre `practica_n23` el costo no debe superar el mejor registrado en `docs/BITACORA.md` (arrancar con ≈ 971 del prototipo, **a confirmar con el simulador oficial**).
- Cada regla: test de "no aplica" y de "aplica".

## Git (obligatorio en Nivel 3)
- `main` siempre ejecutable. Nadie pushea directo: **rama + PR**.
- Ramas: `feat/<modulo>`, `fix/<tema>`, `rule/<evento>-<nombre>`, `docs/<tema>`.
- Commits convencionales y chicos: `feat(solvers): agrega operador relocate`, `fix(io): tolera null en peso`, `test(sim): paridad con ejemplo 2641`.
- Un PR = una tarea de `06-tareas.md`. Descripción: qué cambió, por qué, cómo se probó, costo antes/después si toca el solver.
- Tags en cada cierre: `entrega-1`, `entrega-2`… con el costo obtenido en el mensaje.
- `.gitignore`: `out/`, `__pycache__/`, `.venv/`, `datos/entrega*/`.

## Bitácora para el pitch
`docs/BITACORA.md`: hora, decisión, alternativas, números (costo antes/después), quién. Es la evidencia de «toma de decisiones», «adaptabilidad» y «planificación».
