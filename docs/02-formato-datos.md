# 02 · Formato de los datasets

Cada dataset es una carpeta con **tres archivos**, en JSON y/o CSV con los mismos campos:
`mundo`, `pedidos`, `vehiculos`. Ejemplo real: `tests/fixtures/practica_n23/` (40 pedidos, 5 vehículos, depósito en (0,0)).
**Es un ejemplo, no el contrato**: hay que soportar cualquier valor válido.

## mundo
**JSON** — objeto plano:
```json
{"grilla_ancho": 20, "grilla_alto": 20, "deposito_x": 0, "deposito_y": 0, "hora_salida": "08:00",
 "tiempo_servicio": 5, "tiempo_carga": 10, "min_por_cuadra": 3,
 "costo_por_cuadra": 3, "costo_por_vehiculo": 60, "costo_por_minuto_total": 1, "costo_por_falla": 200}
```
**CSV** — `clave,valor`, una fila por campo (12 campos + cabecera):
```
clave,valor
grilla_ancho,20
grilla_alto,20
deposito_x,0
...
hora_salida,08:00
```
- `hora_salida` es `"HH:MM"` → internamente minutos desde medianoche (08:00 = 480).
- Todos los demás son enteros. Los valores del CSV llegan como texto: castear.

## pedidos
**JSON** — lista de objetos: `[{"id": 1, "x": 8, "y": 17, "peso": 2}, ...]`
**CSV** — cabecera `id,x,y,peso`, una fila por pedido.
- `id`, `x`, `y`, `peso`: enteros. `id` único (en práctica 1..N, **no asumir**: pueden saltear números).
- `peso` existe pero hoy **no restringe nada**. Se carga como `int`; si faltara, `0`.
- Se tolera que `pedidos.json` sea también un dict con una lista adentro.

## vehiculos
**JSON** — lista: `[{"id": "V1"}, {"id": "V2"}, ...]`
**CSV** — cabecera `id`, una fila por vehículo.
- `id` es **string** (`"V1"`). Hoy es el único campo. Eventos futuros pueden agregar columnas (capacidad, costo propio, etc.): guardarlas en `Vehicle.extra` sin interpretarlas.

## Reglas de lectura (para `planner/io`)
1. Preferir JSON si existe; si no, CSV. Ambos deben producir **el mismo `Dataset`** (test obligatorio con el fixture).
2. Un campo opcional puede faltar, valer `null` o estar vacío → `None`/valor por defecto, nunca excepción.
3. Campos desconocidos: se ignoran en la lógica, pero se conservan en `extra` (los eventos los usarán).
4. Archivos con BOM o fin de línea CRLF deben leerse bien (`utf-8-sig`, `newline=""`).
5. Validar con mensajes claros: pedido fuera de la grilla, ids duplicados, depósito fuera de la grilla → `DatasetError`.
6. Tipos internos: `Order.id: int`, `Vehicle.id: str`, tiempos en `int` minutos.

## Formato del plan (escritura)
- JSON: `{"rutas":[{"vehiculo":"V1","paradas":[2,1,10,"DEPOSITO",8,3]}]}` — ids de pedido como **enteros**, `"DEPOSITO"` como string.
- CSV: `vehiculo,parada`.
- **No listar** vehículos sin entregas (no se usan; no se paga su costo fijo).
- Antes de escribir: `validator.validate(dataset, plan)`; si hay errores, no escribir y salir con código ≠ 0.
