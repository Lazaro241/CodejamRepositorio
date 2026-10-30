# 01 · Contexto del problema

> Fuente de verdad: `ESPECIFICACION.md` del repo `quickdrop-sim`. Si algo acá la contradice, gana ella.

## Modelo
- Grilla (en práctica 20x20, coordenadas 0..19), distancia **Manhattan** `|x1-x2| + |y1-y2|`.
- Todos los vehículos salen del depósito a `hora_salida` y terminan en el depósito (la vuelta final **no** se escribe en el plan).
- Tiempos en minutos enteros; horas `"HH:MM"`.
- El depósito, los costos, la velocidad y los tiempos **pueden cambiar entre datasets**, incluida la ubicación del depósito.

## Plan (salida)
Por vehículo, lista ordenada de paradas: id de pedido o `"DEPOSITO"` (vuelve al depósito, `tiempo_carga`, y empieza un nuevo viaje).
- JSON: `{"rutas":[{"vehiculo":"V1","paradas":[2,1,10,"DEPOSITO",8,3]},{"vehiculo":"V2","paradas":[4,9,7]}]}`
- CSV: `vehiculo,parada` con una fila por parada, en orden (`V1,2` / `V1,DEPOSITO` …).
- **Inválido (vale 0 en ese dataset)**: vehículo inexistente o repetido; pedido inexistente o repetido.
- Un pedido que no aparece en el plan **no invalida**: falla (cuesta `costo_por_falla`).

## Simulación y costo
Por vehículo: viaje = cuadras × `min_por_cuadra`; entrega = `tiempo_servicio`; parada `DEPOSITO` = viaje al depósito + `tiempo_carga`; al final vuelve al depósito.
```
costo = costo_por_cuadra·cuadras_totales (todos los vehículos, incluida la vuelta final)
      + costo_por_vehiculo·vehículos_usados
      + costo_por_minuto_total·makespan      # minutos hasta que vuelve el último vehículo
      + costo_por_falla·pedidos_que_fallan
```
Menor es mejor. Hay más vehículos de los necesarios: **decidir cuántos usar es parte del problema**.
Ejemplo oficial de referencia: plan de 25 pedidos con 2 vehículos = **2641** (430 cuadras×3 + 2×60 + 1231 min + 0 fallas).

## Evaluación (para priorizar)
Nivel 3: 30 % calidad del plan (`100 × menor costo válido del nivel / tu costo`, promediado entre cierres) + 70 % pitch (decisiones con números, adaptabilidad, planificación, división de tareas, presentación).
El programa corre **sin pasos manuales** sobre un dataset nuevo y oculto en cada cierre (~mismo tamaño que la práctica). Se puede reentregar; **cuenta la última**, aunque sea peor.
Con cada evento llegan reglas nuevas y un simulador nuevo (`git pull`): **diseñar para agregar reglas**.

## Reglas futuras probables (diseñar para ellas, no implementarlas hasta que se pidan)
Capacidad de vehículo (los pedidos ya traen `peso`; en la práctica van de 1 a 20 y suman 455), múltiples viajes con `DEPOSITO`, ventanas horarias, prioridades, vehículos heterogéneos, fallas de vehículos.

## Eventos incorporados
- **Evento 1 (premium)**: pedidos con `premium` (bool, falso si falta) y mundo con `costo_por_minuto_premium` (def. 1). El costo suma `costo_por_minuto_premium × Σ minutos desde hora_salida hasta que empieza la entrega de cada premium entregado`. Detalle e implementación en `docs/07-evento-1-premium.md`.
