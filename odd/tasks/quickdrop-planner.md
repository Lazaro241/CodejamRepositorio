# Feature: quickdrop-planner (T0..T9 de docs/06-tareas.md)

## Objective
Implement the QuickDrop Planner according to docs/06-tareas.md, executing tasks T0..T9
in dependency order, one branch + conventional work-unit commits per task, following
docs/AGENTS.md, docs/03-arquitectura.md, docs/04-patrones.md, docs/05-convenciones.md.

## Problem
Greenfield Python 3.11 project (`planner/` package) that reads a dataset folder
(mundo/pedidos/vehiculos in JSON or CSV) and writes a delivery plan evaluated by the
official simulator `quickdrop` (cloned at ../quickdrop-sim, not pip-installable: no
pyproject.toml; use PYTHONPATH or run with cwd there for parity runs).

## Constraints (non-negotiable per docs/AGENTS.md)
- Nothing hardcoded from the dataset (depot, costs, speed, grid, departure, counts all from files).
- Practice data is an example, not the contract.
- `planner/domain` imports nothing from io/solvers/rules/simulation/cli.
- Single source of truth for cost: `planner/simulation/` (parity with official simulator).
- New rules = new file in `planner/rules/` + one registry line; solvers untouched.
- Invalid plan scores 0: `simulation/validator.py` always runs before writing.
- Runtime = stdlib only; pytest/ruff dev-only; deterministic via injected `random.Random(seed)`.
- No silently skipped tests; record limitations in docs/BITACORA.md.

## Scope
- T0..T8 as specified in docs/06-tareas.md.
- T9 (capacity rule) requires the event guide; the current dataset has no capacidad
  field, so T9 stays PENDING until the event guide exists (doc 06: "T9 requiere T4 y guía del evento").
- Fixture `tests/fixtures/practica_n23/` (real practice data, JSON+CSV) is versioned.
- docs/ is committed (was untracked at session start); BITACORA.md updated by each task.

## Git plan (docs/05-convenciones.md)
- Branch per task: feat/scaffold, feat/domain, feat/io, feat/simulation, feat/rules-base,
  feat/solver-construction, feat/solver-improvement, feat/orchestrator, feat/cli-e2e.
- After each task passes acceptance, merge to main (--no-ff) so main stays ejecutable;
  next branch starts from updated main. No push (user decides delivery).
- Conventional commits, small; no AI attribution. Tag `entrega-N` at each closure
  (cost in message when solver work produces one).

## Todo (ordered)
- [x] T0 scaffold — branch feat/scaffold: package skeleton, pyproject (py>=3.11, extras dev: pytest, ruff), .gitignore, __main__/cli stub ("no implementado"), version fixture+docs, smoke test. Acceptance: pip install -e .[dev], pytest -q, python -m planner --help. Route: delegated writer.
- [ ] T1 domain — feat/domain: models.py + geometry.py per 03-arquitectura.md contracts, frozen dataclasses, tests.
- [ ] T2 io — feat/io: readers (Json/Csv + detect_reader), writers, DatasetError; tests incl. JSON==CSV equivalence on practica_n23 (40 orders, 5 vehicles V1..V5, depot (0,0), departure 480, sum weights 455).
- [ ] T3 simulation — feat/simulation: simulate/objective/validator; parity tests (case 2641 documented; practica_n23 cost vs official sim via ../quickdrop-sim). Depends T1.
- [ ] T4 rules-base — feat/rules-base: Rule Protocol, RuleSet, registry; integrated into simulate; fake-rule tests. Depends T3.
- [ ] T5 construction — feat/solver-construction: SweepConstructor + nearest_neighbor, Constructor.build(ds,k,offset). Depends T4.
- [ ] T6 improvement — feat/solver-improvement: TwoOpt/Relocate/Swap + LocalSearch with deadline. Depends T5.
- [ ] T7 orchestrator — feat/orchestrator: k sweep + offsets, deadline, logging tabla k→costo. Depends T6.
- [ ] T8 cli-e2e — feat/cli-e2e: full CLI, validator gate, JSON/CSV writers, e2e tests vs official sim cost. Depends T2+T7.
- [ ] T9 capacidad — PENDING event guide (field name/semantics unconfirmed). Do NOT implement until guide arrives.

## Verification commands
pip install -e .[dev] ; pytest -q ; ruff check . ; ruff format --check
python -m planner tests/fixtures/practica_n23 -o out/plan.json
python -m quickdrop simular tests/fixtures/practica_n23 out/plan.json (run from ../quickdrop-sim via cwd or PYTHONPATH, for parity)

## Progress log
- 2026-10-30: feature doc created; plan: sequential tasks, merge each to main.
- 2026-10-30: T0 delegated to general writer (feat/scaffold).
- 2026-10-30 T0 scaffold done on feat/scaffold, commits: 72aa5e8 (docs), 208188a (fixture), + scaffold commit (this one). Verified: pip install -e .[dev] OK, pytest -q 2 passed, python -m planner --help OK, ruff check . clean, ruff format --check . clean, stub prints "no implementado".
