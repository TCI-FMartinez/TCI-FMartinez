# SORTING-Study

# Flujo de procesado

Este documento describe el comportamiento del pipeline tal como está organizado actualmente en el proyecto.

Está basado en el flujo real implementado en `main.py` y en los módulos auxiliares usados durante la ejecución.

Importante:
- este documento describe el funcionamiento actual, no solo el deseado
- si en el futuro se implementa deduplicación real entre piezas repetidas, este documento deberá actualizarse
- `OUT_ref_cache` no almacena resultados de `compute_ref`; se usa para reutilizar datos intermedios de `load_slot`

## Visión general

El pipeline completo tiene dos grandes etapas:

1. preparación de piezas a partir de programas de entrada
2. evaluación de cada pieza contra herramientas compatibles

La entrada parte de archivos `.lpp` o `.cnc` en `INPUT/`. A partir de ellos, el sistema genera piezas individuales, calcula metadata técnica, las clasifica por robot, produce salidas geométricas y después lanza `compute_ref.exe` por combinación pieza + herramienta.

## Resumen del flujo

```text
INPUT/*.lpp|*.cnc
  -> normalización de entrada
  -> separación en piezas individuales
  -> reescritura de cabecera META
  -> clasificación SCARA / ANTHRO
  -> generación de OUT_cnc / OUT_png / OUT_dxf
  -> selección de herramientas por robot
  -> generación de material.json y ref_*.json
  -> ejecución de compute_ref.exe
  -> lectura de solución y metadata
  -> generación de metadata_parser.json
  -> generación de overlays
  -> summary.json por robot
  -> report/ por robot
  -> limpieza final de temporales
```

## 1. Inicialización y limpieza

Al arrancar, `main.py` fuerza un estado limpio de trabajo.

### Directorios que limpia al inicio

- `_internal/parsed_parts`
- `OUTPUT/ANTHRO/OUT_cnc`, `OUT_dxf`, `OUT_png`, `OUT_solutions` según `root_dir` real configurado
- `OUTPUT/SCARA/OUT_cnc`, `OUT_dxf`, `OUT_png`, `OUT_solutions` según `root_dir` real configurado
- `OUT_ref_cache`

Consecuencia importante:
- el pipeline actual no está pensado como ejecución incremental sobre salidas previas
- cada ejecución reconstruye los resultados desde cero

## 2. Carga de configuración

Antes de procesar piezas, el sistema carga `config.json`.

Comportamiento actual:
- si `config.json` no existe, intenta crearlo automáticamente con una plantilla por defecto
- si existe, mezcla sus valores con la configuración por defecto interna
- si faltan claves, se heredan de los defaults

De esta carga salen principalmente:
- rutas raíz de `ANTHRO` y `SCARA`
- flag `scara.enabled`
- filtros `robots.scara.filters`
- `default_tool` de cada robot
- `allow_other_tools` de cada robot
- parámetros `compute_ref.max_compute_time` y `compute_ref.enhance_opti`

## 3. Normalización de entrada

### 3.1 Renombrado de `.lpp` a `.cnc`

El primer paso operativo sobre `INPUT/` es renombrar los archivos con extensión `.lpp` a `.cnc`.

Esto ocurre en la propia carpeta `INPUT/`.

Implicación práctica:
- el pipeline modifica el nombre del archivo de entrada cuando detecta `.lpp`
- no trabaja con una copia temporal del `.lpp`; lo transforma en `.cnc` dentro del directorio de entrada

### 3.2 Descubrimiento de archivos de entrada

Una vez hecho el renombrado, el sistema lista los `.cnc` presentes en `INPUT/` y procesa cada uno de forma independiente.

Si no encuentra archivos `.cnc`, termina sin continuar a las fases posteriores.

## 4. Lectura del programa y separación en piezas

Para cada archivo fuente:

1. lee el archivo completo
2. analiza la cabecera general con `parse_gcode_head`
3. separa las piezas con `parse_gcode_parts`
4. guarda provisionalmente las piezas en `_internal/parsed_parts`

Ese directorio temporal se limpia antes y después de procesar cada programa de entrada.

## 5. Reescritura de cabecera y metadata por pieza

Cada pieza separada pasa por una fase de enriquecimiento de metadata.

La función `rewrite_piece_header(...)` recalcula y reescribe la cabecera `META` de la pieza con información como:
- archivo fuente original
- material
- familia de material
- ferromagnetismo
- densidad
- espesor
- bounding box
- área
- peso estimado

Esta metadata es la base para casi todo lo demás:
- enrutado a SCARA o ANTHRO
- generación de `material.json`
- trazabilidad posterior
- análisis de resultados

## 6. Clasificación por robot

Cada pieza se clasifica entre:
- `SCARA`
- `ANTHRO`

La decisión la toma `modules/scara_router.py`.

### Regla de negocio actual

- si `robots.scara.enabled = false`, ninguna pieza va a SCARA
- si `robots.scara.enabled = true`, se evalúan los filtros configurados
- si la pieza pasa los filtros, va a `SCARA`
- si no los pasa, va a `ANTHRO`

### Filtros actuales soportados

- `max_bbox_x`
- `max_bbox_y`
- `max_weight_kg`
- `ferromagnetic`
- `material_family_any`
- `material_contains_any`

### Salida del routing

El routing no solo decide robot, también fija las rutas finales de la pieza:
- `OUT_cnc`
- `OUT_png`
- `OUT_dxf`

La pieza ya reescrita se mueve desde `_internal/parsed_parts` al `OUT_cnc` del robot asignado.

## 7. Generación de salidas geométricas básicas

Una vez asignada la pieza a un robot, se generan dos salidas geométricas básicas:

### 7.1 PNG de contorno

Se dibuja un PNG del contorno de la pieza en:
- `OUT_png/<pieza>_contours.png`

### 7.2 DXF de la pieza

Se genera un DXF simplificado de la pieza en:
- `OUT_dxf/<pieza>.dxf`

Estas salidas se generan inmediatamente después del routing, antes de entrar en la fase de solver.

## 8. Inicio de la fase pieza + herramienta

Una vez procesados todos los programas de entrada y generadas todas las piezas, el pipeline entra en la fase de optimización con `compute_ref.exe`.

Esta fase se ejecuta por robot.

Para cada robot:
- lee sus piezas desde `OUT_cnc`
- prepara `OUT_solutions`
- selecciona herramientas
- evalúa cada combinación pieza + herramienta

## 9. Selección de herramientas por robot

La selección real actual depende de:
- `default_tool`
- `allow_other_tools`

Comportamiento actual:
- si `allow_other_tools = false`, el robot solo prueba la herramienta por defecto
- si `allow_other_tools = true`, prueba primero la herramienta por defecto y luego el resto detectado en `TOOLS/`
- si la herramienta por defecto no existe y `allow_other_tools = false`, ese robot no procesa piezas
- si la herramienta por defecto no existe y `allow_other_tools = true`, el robot procesa con las herramientas disponibles

Nota importante:
- en SCARA, la selección efectiva sí queda limitada por `allowed_tools`
- `default_tool` marca prioridad dentro de ese subconjunto
- `allow_other_tools` decide si, además de la herramienta por defecto, se prueban o no otras herramientas permitidas
- SCARA no debe heredar herramientas fuera de su lista permitida

## 10. Preparación de herramientas procesadas

Antes de lanzar el solver, cada herramienta pasa por una fase de preparación con generación de polígonos.

La salida se guarda en:
- `TOOLS/processed/`

Esto permite normalizar la geometría de la herramienta antes de pasarla a `compute_ref.exe`.

## 11. Generación de material.json por pieza

Para cada pieza se genera un único `material.json` dentro de su carpeta en `OUT_solutions/<pieza>/material.json`.

Este archivo se construye a partir de la metadata de cabecera de la pieza, especialmente:
- `MATERIAL`
- `THICKNESS`
- `DENSITY_G_CM3`
- `FERROMAGNETIC`

Si faltan datos explícitos, el pipeline intenta completarlos a partir del perfil del material configurado en `config.json`.

## 12. Generación de ref JSON

Para cada combinación pieza + herramienta se genera:
- `ref_<pieza>.json`

La construcción del `ref` sigue esta lógica:

1. intenta reutilizar información procedente de `load_slot`
2. si no puede adaptarla correctamente, cae a una construcción legacy basada en la geometría de la pieza

Esto es importante porque el `ref` que consume `compute_ref.exe` no se construye siempre igual; hay una ruta preferente y una ruta de respaldo.

## 13. Uso real de OUT_ref_cache

`OUT_ref_cache` se utiliza para almacenar resultados intermedios de `load_slot` por programa fuente.

Concretamente, cachea información como:
- `refPartJson_<source>.json`
- `partJson_<source>.json`

Objetivo actual:
- evitar recalcular varias veces la extracción base desde el mismo programa fuente durante una misma ejecución
- reutilizar datos de referencia del programa origen para mapear correctamente piezas separadas

Importante:
- `OUT_ref_cache` no es caché de resultados de `compute_ref`
- no evita todavía recalcular combinaciones pieza + herramienta ya resueltas en otra ejecución
- tampoco implementa por sí mismo deduplicación geométrica entre piezas repetidas con distinto ID

## 14. Estado actual de la deduplicación

A día de hoy, no se observa en el pipeline una deduplicación real de piezas repetidas entre distintos `.cnc` o distintos IDs.

Eso significa que:
- si dos piezas son geométricamente equivalentes pero llegan con identificadores distintos, se siguen procesando como piezas independientes
- no existe todavía una caché de soluciones por firma geométrica de pieza
- `OUT_ref_cache` no cubre ese caso

Esto encaja con la necesidad que ya se había identificado en el proyecto: evitar lanzar `compute_ref` varias veces para piezas equivalentes cuando no interesa una estadística separada por ID.

## 15. Ejecución de compute_ref.exe

Por cada combinación pieza + herramienta, el pipeline llama a `compute_ref.exe` con:
- `refFileJson`
- `toolFileJson`
- `materialFileJson`
- `maxComputeTime`
- `enhanceOpti`

La ejecución se realiza dentro del directorio de la combinación:
- `OUT_solutions/<pieza>/<herramienta>/`

## 16. Descubrimiento de solución y normalización de metadata

Tras ejecutar el solver, el pipeline intenta localizar:
- JSON de solución
- metadata del solver

Con eso construye `metadata_parser.json`, que es la capa de metadata normalizada para análisis posterior.

Campos relevantes:
- estado final de la combinación
- si hubo ejecución real
- si existe solución
- si existe geometría de solución
- si la solución se considera válida
- distancias aproximadas entre centros de pieza y herramienta
- índices activos de herramienta
- flags y códigos devueltos por solver

## 17. Interpretación del resultado

La lógica actual distingue varios estados.

### Casos principales

- `valid`
  - hubo ejecución
  - no hay flag de error bloqueante
  - existe geometría de solución

- `completed_without_geometry`
  - el solver dejó rastro de solución pero no se detectó geometría útil

- `completed_without_solution`
  - terminó sin solución utilizable

- `infeasible_cannot_lift`
  - caso especial para flag `-6`
  - se interpreta como solución inviable, no como error de ejecución del proceso

- `solver_error`
  - el solver devolvió un flag de error distinto del caso especial tratado

- `execution_error`
  - la ejecución no se completó correctamente

### Significado de `solution_valid`

`solution_valid = true` solo cuando el estado final queda en `valid`.

Esto exige más que la mera existencia de un archivo JSON de salida:
- debe existir geometría interpretable
- no debe haber un flag de error que invalide la solución

## 18. Generación de overlays

Para cada combinación, el pipeline intenta generar overlay si existe `solution_json`.

Se generan dos PNG potenciales:
- uno dentro del directorio de la combinación
- otro en `OUT_solutions/png/` como colección global por robot

### Regla real

- si no existe `solution_json`, no se intenta dibujar overlay
- si existe `solution_json`, el renderer recibe también metadata
- el módulo de overlay decide si dibuja herramienta real o deja un mensaje como “solución no encontrada” según el valor de `solution_valid`

Esto aclara una diferencia importante:
- la presencia de `solution_json` no garantiza que haya overlay de herramienta válida
- el criterio final depende de la metadata interpretada

## 19. Generación de summary.json

Cada robot genera un `summary.json` en:
- `OUT_solutions/summary.json`

Este archivo contiene la colección completa de combinaciones procesadas para ese robot y sirve como base para:
- análisis estadístico
- ranking de herramientas
- informes posteriores
- trazabilidad de fallos, flags y soluciones válidas

## 20. Generación de informes

Tras completar la fase de solver, el pipeline intenta generar informes por robot a partir de `summary.json`.

Salida esperada:
- `OUT_solutions/report/`
- ficheros de informe en Excel y JSON, según el generador actual

Esta fase se ejecuta por separado para:
- `ANTHRO`
- `SCARA`

## 21. Limpieza final

Al terminar, el pipeline ejecuta limpieza final en bloque `finally`.

Directorios temporales eliminados:
- `_internal/parsed_parts`
- `OUT_ref_cache`

Consecuencia:
- la caché de `load_slot` solo vive durante la ejecución actual
- no queda persistida entre corridas
- la siguiente ejecución vuelve a empezar limpia

