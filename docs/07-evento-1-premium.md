# 07 · Evento 1: clientes premium (Nivel 3: obligatorio)

> Fuente de verdad: `ESPECIFICACION.md` del simulador oficial (ya actualizado con `git pull`). Si algo acá la contradice, gana ella.
> **Regla de oro del evento: cada etapa se evalúa con todas las reglas anteriores. No romper lo que ya andaba.** Un dataset sin premium debe dar **exactamente el mismo costo y plan** que antes.

## 1. Qué cambia (especificación)
- **Pedidos**: campo opcional `premium` (booleano). Si falta, `null` o vacío ⇒ **falso**.
  - JSON: `{"id": 2, "x": 6, "y": 14, "peso": 4, "premium": true}`
  - CSV: cabecera `id,x,y,peso,premium`; booleanos como `1`/`0`; también se aceptan `true`/`false` y `si`/`no` (sin distinguir mayúsculas; tolerar también `sí`, `yes`, `no`).
- **Mundo**: campo `costo_por_minuto_premium` (entero, **por defecto 1** si falta). JSON: clave plana. CSV: fila `costo_por_minuto_premium,<valor>`.
- **Costo**:
```
costo = costo_por_cuadra·cuadras + costo_por_vehiculo·vehículos_usados
      + costo_por_minuto_total·makespan + costo_por_falla·fallas
      + costo_por_minuto_premium · Σ (minutos desde hora_salida hasta que EMPIEZA la entrega de cada premium ENTREGADO)
```
Detalles que no son obvios:
- "Empieza su entrega" = momento de **llegada** a la parada (después del viaje, **antes** de sumar `tiempo_servicio`).
- Cuenta el tiempo **absoluto desde `hora_salida`**, incluyendo viajes previos, servicios previos y paradas `DEPOSITO` (+ `tiempo_carga`) si el premium va en un segundo viaje.
- Un premium **no entregado** (falla) no suma este término (sí suma `costo_por_falla`).
- Cada vehículo arranca a `hora_salida`; los minutos de un premium en V2 se miden desde esa misma hora, no desde cuando termine V1.
- Los pedidos no premium no suman nada.

### Ejemplo hecho a mano (usar como test unitario)
Depósito (0,0), 1 vehículo `V1`, valores por defecto (3 min/cuadra, servicio 5, costo cuadra 3, vehículo 60, minuto 1, premium 1). Pedido 1 en (2,0) **premium**, pedido 2 en (4,0) normal.

| Ruta | Cuadras | Makespan | Min. premium | Costo |
|---|---|---|---|---|
| `[1, 2]` | 8 (→24) | 34 | 6 (llega a los 6 min) | 24 + 60 + 34 + **6** = **124** |
| `[2, 1]` | 8 (→24) | 34 | 23 (12+5+6) | 24 + 60 + 34 + **23** = **141** |

Misma distancia y mismo makespan; solo cambia el término premium. Sin la regla, ambas costarían 118.

## 2. Diseño (no hardcodear: extender por contrato)
El premium **cambia la función de costo** y **necesita saber el instante de cada entrega**. Hoy `simulate` devuelve solo totales, así que se agregan dos extensiones mínimas y **genéricas** (servirán para ventanas horarias y prioridades después). Ambas con valores por defecto neutros para no romper nada:

1. **`Timeline`**: el simulador, además de totales, produce un registro inmutable por entrega: `Delivery(vehicle_id, order_id, start, end)` con `start` = minutos **desde `hora_salida`** en que empieza la entrega. Se incluye en `Evaluation`.
2. **`Rule.cost_terms(ds) -> Sequence[CostTerm]`** (default `()`): la regla aporta términos de costo componibles (patrón Composite de `objective.py`). `CostTerm.compute(timeline, ds) -> int`. Su valor aparece en `Evaluation.breakdown` con el nombre del término (`"premium"`).
3. **`Rule.urgent_orders(ds) -> frozenset[int]`** (default vacío): ids de pedidos que conviene atender temprano. Lo usan las estrategias del solver sin conocer la regla concreta (`PremiumRule` devuelve los premium).

Archivos nuevos / tocados:
```
planner/domain/parsing.py        parse_bool(value) -> bool          (nuevo, puro)
planner/simulation/timeline.py   Delivery, Timeline                  (nuevo)
planner/simulation/simulator.py  genera Timeline; suma cost_terms de reglas activas   (editar, retrocompatible)
planner/simulation/objective.py  protocolo CostTerm                  (editar)
planner/rules/base.py            + cost_terms, urgent_orders (defaults)  (editar)
planner/rules/premium.py         PremiumRule + PremiumTerm           (nuevo)
planner/rules/registry.py        registrar PremiumRule               (1 línea)
planner/solvers/construction/urgent_first.py   UrgentFirst, DedicatedUrgent   (nuevo)
planner/solvers/orchestrator.py  probar variantes y elegir por costo real      (editar mínimo)
```
**No se toca**: `LocalSearch`, operadores existentes, `cli`, `domain/models.py` (el premium viaja en `Order.extra["premium"]` y el precio en `World.extra["costo_por_minuto_premium"]`; `io` los conserva como vienen, sin interpretarlos).

## 3. Tareas (una rama/PR por tarea, en este orden)

### E1-A · `rule/premium-contrato` — extender contrato (sin premium todavía)
> Implementá `Timeline`/`Delivery`, `CostTerm`, y agregá a `Rule` los métodos `cost_terms` y `urgent_orders` con defaults neutros. Hacé que `simulate` genere el `Timeline` y sume los `cost_terms` de las reglas activas, reportando cada uno en `Evaluation.breakdown`. **No cambies ningún resultado existente.** Tests: (1) para `practica_n23` y los datasets de tests previos, `total` y `breakdown` son idénticos a los de antes; (2) con una regla falsa que aporta un `CostTerm` constante se suma al total y aparece en el breakdown; (3) el `Timeline` de un plan simple tiene `start` correctos (usá el ejemplo `[2,1]`: pedido 2 empieza en 12, pedido 1 en 23).

**Aceptación:** suite completa verde; sin diferencias de costo en tests previos.

### E1-B · `rule/premium-datos` — leer premium
> Agregá `planner/domain/parsing.py::parse_bool` (acepta `bool`, `1/0`, `"1"/"0"`, `true/false`, `si/sí/yes/no`, sin distinguir mayúsculas; `None`/vacío/ausente ⇒ `False`; cualquier otro valor ⇒ `DatasetError` con mensaje claro). Verificá que `io` conserve `premium` en `Order.extra` y `costo_por_minuto_premium` en `World.extra` tanto desde JSON como desde CSV, y que **dataset viejo (sin esos campos) siga leyéndose igual**. Fixture nueva en `tests/fixtures/practica_e1/` (JSON y CSV del dataset de práctica del evento, que descarga el usuario del simulador). Tests: premium ids de la práctica = `{2, 14, 17, 21, 30, 36}`; JSON y CSV dan el mismo `Dataset`; variantes `1/0/true/false/si/no/""/null/ausente`.

**Aceptación:** lectura equivalente JSON↔CSV; ningún cambio en la lectura de `practica_n23`.

### E1-C · `rule/premium-regla` — la regla y su costo
> Implementá `planner/rules/premium.py`: `PremiumRule` (`applies` = algún pedido premium según `parse_bool`; `cost_terms` = `[PremiumTerm(price)]` con `price = World.extra.get("costo_por_minuto_premium", 1)` casteado a int; `urgent_orders` = ids premium). `PremiumTerm.compute` suma `price · start` para cada `Delivery` cuyo pedido sea premium (solo entregados). Registrala en `registry.py`. Tests: el ejemplo a mano de la sección 1 (124 y 141); premium no entregado no suma; premium en segundo viaje (con `DEPOSITO`) cuenta el tiempo de recarga; `costo_por_minuto_premium = 0` ⇒ término 0; dataset sin premium ⇒ costo idéntico al de antes. **Paridad oficial**: corré el simulador actualizado (`git pull` en `quickdrop-sim`) sobre un plan fijo de `practica_e1` y fijá en `tests/simulation/test_parity.py` el costo total y el término premium que reporta; el nuestro debe coincidir. Si no podés ejecutar el simulador oficial, pedile al usuario el costo y no inventes el valor.

**Aceptación:** coincide con el oficial en el plan fijo; `practica_n23` sin cambios.

### E1-D · `feat/solver-urgent` — que el solver aproveche el premium
La búsqueda local ya mide el costo real (incluye premium), pero la construcción por barrido ignora el orden temporal y puede quedar en un mínimo local malo. Se agregan **estrategias nuevas** (patrón Strategy), sin editar `LocalSearch` ni operadores:
- `UrgentFirst(base_constructor)`: toma las rutas de cualquier constructor y, dentro de cada ruta, pone **primero** los pedidos de `rules.urgent_orders(ds)` (ordenados por cercanía entre sí/al depósito) y luego el resto en el orden que ya tenían.
- `DedicatedUrgent(base_constructor, n_dedicated)`: asigna los urgentes a 1..n vehículos dedicados (agrupados por cercanía) y reparte el resto con el constructor base entre los demás.
> Implementalas con la interfaz `Constructor.build(ds, k, offset)` más acceso al `RuleSet` (inyectado, no global). En el orquestador, **además de las construcciones actuales**, probá estas variantes (solo si `urgent_orders` no está vacío), pasá cada candidato por `LocalSearch` y elegí por costo real vía `simulate`. Loguear una tabla `variante → k → costo (breakdown)`. Tests: nunca plan inválido; con premium el costo total nunca es peor que el de la construcción sin variantes; sin premium el orquestador devuelve **el mismo plan que antes** (misma semilla); `UrgentFirst` deja los urgentes al inicio de cada ruta; respeta `deadline`.

**Aceptación:** sobre `practica_e1` el costo es ≤ al de "solver anterior sin variantes"; la tabla de variantes queda en el log.

### E1-E · `feat/e1-e2e` — extremo a extremo y no regresión
> Test e2e del CLI sobre `practica_e1` (JSON y CSV) y sobre `practica_n23`. Verificá: plan válido; costo del CLI = costo del simulador oficial (`python -m quickdrop simular ... --detalle`, incluido el término premium); `practica_n23` conserva el costo registrado en `BITACORA.md` (regresión). Variantes derivadas: depósito en (10,10); todos los pedidos premium; ningún premium; `costo_por_minuto_premium` en 0, 1 y 20 (con 20 los premium deben quedar más temprano que con 0).

**Aceptación:** todas las verificaciones; `ruff` limpio.

### E1-F · `docs/e1` — bitácora (evidencia para el pitch)
> Completá `docs/BITACORA.md` con: costo de `practica_e1` antes (solver del evento 0, evaluado con el costo nuevo), después, y la tabla de variantes (UrgentFirst, DedicatedUrgent, base) con sus costos y el desglose del término premium. Anotá las dos extensiones de `Rule` (`cost_terms`, `urgent_orders`) y por qué eran la modificación mínima.

## 4. Criterios de aceptación globales del evento
- [ ] Dataset **sin** premium ⇒ plan y costo idénticos al evento anterior (misma semilla).
- [ ] `practica_e1` leída igual desde JSON y CSV; premium ids `{2, 14, 17, 21, 30, 36}`.
- [ ] Costo local = costo oficial (total y término premium) en planes fijos.
- [ ] Diff de solvers limitado a archivos **nuevos** + el cambio mínimo del orquestador; `LocalSearch` y operadores intactos.
- [ ] El plan nunca es inválido (vehículo/pedido inexistente o repetido).
- [ ] Sin hardcodear premium, precio, depósito ni cantidades.

## 5. Preguntas de diseño que conviene poder responder en el pitch
- **¿Vehículo dedicado o premium al principio de cada ruta?** No se decide a priori: se generan ambas variantes y gana la de menor costo real. Registrar en la bitácora cuál ganó y por cuánto.
- **¿Cuánto vale adelantar un premium?** Depende de `costo_por_minuto_premium`: con precio alto conviene sacrificar distancia; con precio bajo, no. Mostrar la prueba con precio 0, 1 y 20.
- **¿Se rompió algo?** No: la regla se activa solo si hay premium y hay un test de no regresión.
