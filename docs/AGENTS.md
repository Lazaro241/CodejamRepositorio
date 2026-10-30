# AGENTS.md — QuickDrop Planner

Programa en **Python 3.11+** que lee un dataset (`mundo`, `pedidos`, `vehiculos`; JSON o CSV) y escribe un plan de reparto.
Se evalúa con datasets ocultos y las reglas **cambian durante la jornada**. Por eso: diseño extensible > optimalidad.

## Antes de escribir código, leé
1. `docs/01-contexto.md` — el problema y sus reglas (fuente de verdad: `ESPECIFICACION.md` del simulador oficial).
2. `docs/02-formato-datos.md` — **formato exacto de los datasets** (con el de práctica real en `tests/fixtures/practica_n23/`).
3. `docs/03-arquitectura.md` — capas, carpetas y reglas de dependencia.
4. `docs/04-patrones.md` — qué patrón usar y dónde (y cuándo NO).
5. `docs/05-convenciones.md` — estilo, tests, Git.
La tarea concreta está en `docs/06-tareas.md`. Hacé **solo** la tarea que te piden.

## Reglas innegociables
- **Nada hardcodeado del dataset**: depósito, costos, velocidad, tiempos, hora de salida, tamaño de grilla y cantidad de pedidos/vehículos salen de los archivos. Prohibido suponer depósito en (0,0), grilla 20x20, 40 pedidos, 5 vehículos o ids `V1..Vn`.
- **Los datos de práctica son un ejemplo, no el contrato**: el contrato es `docs/02-formato-datos.md` (campos opcionales pueden faltar, venir `null` o vacíos; campos desconocidos se ignoran).
- **Hoy los vehículos no tienen capacidad** (solo `id`) y `peso` de los pedidos no limita nada. No inventes una capacidad. El peso se carga y se conserva para reglas futuras.
- **Dominio puro**: `planner/domain` no importa de `io`, `solvers`, `rules`, `simulation` ni `cli`.
- **Una sola fuente de verdad del costo**: `simulation/` (réplica del simulador oficial). Los solvers lo usan, no lo reimplementan.
- **Reglas nuevas = archivos nuevos** en `planner/rules/` + una línea de registro. Si para agregar una regla hay que editar el solver, el diseño está mal: frená y avisá.
- **Plan inválido vale 0**: nunca repitas pedido/vehículo ni uses ids inexistentes. `simulation/validator.py` se llama siempre antes de escribir.
- Sin dependencias en runtime (solo stdlib). `pytest` y `ruff` solo para desarrollo.
- Determinismo: toda aleatoriedad usa un `random.Random(seed)` inyectado.

## Qué NO hacer
- No sobre-diseñar: sin frameworks, sin ABCs de un solo uso, sin patrones "por si acaso" (ver `04-patrones.md`).
- No refactorizar fuera de la tarea ni renombrar archivos que no te pidieron tocar.
- No commitear datasets de evaluación ni planes generados (`out/` en `.gitignore`). Los fixtures de `tests/fixtures/` sí se versionan.

## Definition of Done (toda tarea)
- [ ] `pytest -q` pasa y hay tests nuevos para lo agregado.
- [ ] `ruff check .` limpio y type hints en funciones públicas.
- [ ] `python -m planner tests/fixtures/practica_n23 -o out/plan.json` corre y el costo coincide con `python -m quickdrop simular tests/fixtures/practica_n23 out/plan.json`.
- [ ] Docstring corto en cada módulo/clase pública explicando el *porqué*.
- [ ] Rama y commits según `05-convenciones.md`.

## Comandos
```
python -m planner <carpeta_dataset> -o out/plan.json [--csv] [--seed N] [--budget SEG]
pytest -q
python -m quickdrop simular <carpeta_dataset> out/plan.json --detalle   # simulador oficial
```
