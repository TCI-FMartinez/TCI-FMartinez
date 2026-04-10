
# SORTING-Study

# Troubleshooting

Este documento recoge los problemas más habituales detectados en `parser_lpp_BATCH`, junto con su causa probable, cómo verificarlos y qué hacer para corregirlos.

Importante:
- este documento está pensado para diagnóstico rápido
- cuando haya discrepancias entre este texto y el comportamiento real del código, manda siempre el código
- conviene revisar este documento cada vez que cambie la lógica de solver, routing, overlays o limpieza

## 1. No se dibuja la herramienta sobre la pieza aunque exista salida del solver

### Síntoma

Existe carpeta de solución, existe `solution.json` o `metadata.json`, pero el overlay no muestra la herramienta sobre la pieza.

### Causa probable

La existencia de un JSON de solución no implica automáticamente que la solución sea válida para renderizar.

El pipeline distingue entre:
- que exista archivo de solución
- que exista geometría útil
- que `solution_valid` sea verdadero

Si la metadata final interpreta que la solución no es válida, el renderer puede generar una imagen sin herramienta o con mensaje de “solución no encontrada”.

### Qué comprobar

1. abrir `metadata_parser.json`
2. revisar estos campos:
   - `solution_found`
   - `solution_geometry_found`
   - `solution_valid`
   - `status`
   - `solver_error_flag`
3. comprobar que exista realmente el archivo `ref_<pieza>_solution.json`
4. revisar si el PNG generado pertenece a una combinación válida o a una combinación completada sin geometría

### Interpretación rápida

- `solution_found=true` pero `solution_geometry_found=false`
  - el solver dejó rastro de salida, pero no hay geometría útil para dibujar
- `solution_geometry_found=true` pero `solution_valid=false`
  - hay geometría, pero la solución quedó invalidada por la interpretación del resultado
- `status=valid`
  - debería existir overlay correcto con herramienta dibujada

### Acción recomendada

La comprobación principal no debe hacerse solo sobre `metadata.json`, sino sobre `metadata_parser.json`, porque ahí queda la interpretación final que usa el pipeline para análisis y render.

## 2. Hay `solution_valid=True` en metadata, pero el overlay sigue sin aparecer

### Síntoma

Se observa una combinación aparentemente válida, pero la herramienta no se ve dibujada.

### Causas probables

- se está mirando la metadata equivocada
- el overlay que se está revisando no corresponde a la combinación correcta
- el PNG global de `OUT_solutions/png/` no coincide con el fichero individual esperado
- la solución válida existe en una herramienta, pero se está inspeccionando la de otra

### Qué comprobar

1. localizar la carpeta exacta de combinación pieza + herramienta
2. revisar que el PNG inspeccionado salga de esa misma combinación
3. abrir `metadata_parser.json` de esa carpeta exacta
4. confirmar que el estado sea `valid`
5. comprobar si el renderer ha generado el PNG individual dentro de la carpeta de combinación

### Acción recomendada

Verificar siempre la pareja exacta:
- pieza
- herramienta

No dar por hecho que un overlay global o un PNG con nombre parecido corresponde a la combinación que realmente fue válida.

## 3. `FLAG=-6`

### Síntoma

El solver devuelve `FLAG=-6` o en `metadata_parser.json` aparece `solver_error_flag = -6`.

### Interpretación

Ese caso se trata como una combinación inviable para agarre o levantamiento, no como un fallo genérico de ejecución del pipeline.

En términos prácticos significa que:
- la herramienta se ha evaluado
- el solver ha llegado a una conclusión
- pero esa combinación no puede resolver la pieza de forma utilizable

### Qué comprobar

1. revisar `status`
2. revisar `solver_error_flag`
3. revisar `tool_active_count`
4. revisar `center_distance_approx` si se usa luego como criterio de puntuación

### Acción recomendada

No tratar `FLAG=-6` como si el proceso hubiera fallado técnicamente.

Lo correcto es interpretarlo como combinación descartada por inviabilidad física o funcional.

## 4. SCARA no procesa ninguna pieza

### Síntoma

Todas las piezas terminan en `ANTHRO` y no aparece actividad en `OUTPUT/SCARA`.

### Causas probables

- `robots.scara.enabled = false`
- las piezas no pasan los filtros de SCARA
- las rutas de salida de SCARA están mal configuradas
- SCARA no encuentra una herramienta por defecto válida y además no puede probar otras

### Qué comprobar

1. revisar en `config.json`:
   - `robots.scara.enabled`
   - `robots.scara.filters`
   - `robots.scara.default_tool`
   - `robots.scara.allow_other_tools`
2. revisar la metadata de alguna pieza:
   - `BBOX_X`
   - `BBOX_Y`
   - `WEIGHT_KG`
   - `MATERIAL`
   - `MATERIAL_FAMILY`
   - `FERROMAGNETIC`
3. comprobar que la herramienta por defecto exista realmente en `TOOLS/`

### Acción recomendada

Primero confirmar si SCARA está deshabilitado por configuración.

Si está habilitado, revisar los filtros uno por uno, porque basta con que falle uno para que la pieza vaya a `ANTHRO`.

## 5. SCARA está habilitado pero no prueba herramientas

### Síntoma

La pieza llega a SCARA, pero no aparecen combinaciones o no se ejecuta el solver para ese robot.

### Causas probables

- `default_tool` no existe en `TOOLS/`
- `allow_other_tools = false`
- no hay herramientas procesables en la carpeta de herramientas

### Qué comprobar

1. revisar `robots.scara.default_tool`
2. comprobar si el nombre coincide con el JSON real de `TOOLS/`
3. verificar si `allow_other_tools` está en `false`
4. revisar si `TOOLS/processed/` se genera correctamente

### Acción recomendada

Si SCARA solo puede usar su herramienta por defecto, esa herramienta debe existir sí o sí.

Si no existe, el robot puede quedarse sin combinaciones que evaluar.

## 6. `allowed_tools` está en config, pero parece no cambiar nada

## 6. `allowed_tools` no se comporta como esperabas

### Síntoma

Se define `allowed_tools` en SCARA, pero el resultado observado no coincide con lo esperado.

### Causas probables

- algún nombre de herramienta no coincide exactamente con el JSON real de `TOOLS/`
- `default_tool` no pertenece a la lista permitida
- `allow_other_tools = false` y se esperaba que SCARA probara más herramientas
- se está interpretando mal el efecto de prioridad frente al de restricción

### Qué comprobar

1. revisar `robots.scara.allowed_tools`
2. comprobar que todos los nombres existan realmente en `TOOLS/`
3. comprobar que `robots.scara.default_tool` pertenezca a esa lista
4. revisar el valor de `robots.scara.allow_other_tools`
5. comparar las combinaciones realmente generadas en `OUT_solutions` con la lista permitida

### Interpretación correcta

- `allowed_tools` limita el conjunto de herramientas que SCARA puede usar
- `default_tool` prioriza una dentro de ese conjunto
- `allow_other_tools=false` hace que SCARA se quede solo con la herramienta por defecto
- `allow_other_tools=true` permite probar las demás, pero solo dentro de la lista permitida

### Acción recomendada

Si el comportamiento no cuadra, revisar primero nombres exactos y pertenencia de `default_tool` a `allowed_tools`.

El fallo suele estar en la configuración, no en el concepto de la lista blanca.

## 7. `config.json` no existe

### Síntoma

Se intenta ejecutar el proyecto por primera vez y falta `config.json`.

### Comportamiento esperado

El sistema intenta crear automáticamente una plantilla base.

### Posibles problemas

- se crea una plantilla con rutas o defaults no alineados con la instalación real
- el usuario ejecuta sin revisar la configuración generada
- la herramienta por defecto creada por plantilla no existe en `TOOLS/`

### Qué comprobar

1. si el archivo se ha generado realmente
2. si las rutas `root_dir` coinciden con la estructura de carpetas usada en el proyecto
3. si `default_tool` existe en `TOOLS/`
4. si los filtros de SCARA son razonables para las piezas del lote

### Acción recomendada

Aunque el sistema genere `config.json`, hay que revisarlo antes de usarlo en producción.

La creación automática debe entenderse como plantilla inicial, no como configuración validada.

## 8. Las rutas documentadas no coinciden con las carpetas reales

### Síntoma

La documentación habla de una estructura y el proyecto genera o espera otra.

### Causas probables

- evolución del proyecto sin actualizar README o docs
- plantilla interna de configuración desalineada con el `config.json` real
- mezcla de rutas antiguas y nuevas

### Qué comprobar

1. revisar `robots.anthro.root_dir`
2. revisar `robots.scara.root_dir`
3. comparar esos valores con las carpetas que realmente genera la ejecución
4. revisar si la documentación usa todavía rutas heredadas

### Acción recomendada

Usar siempre como referencia operativa las rutas que salgan de `config.json` y de la ejecución real.

Después, corregir la documentación para que deje de mezclar estructuras antiguas y nuevas.

## 9. `OUT_ref_cache` genera confusión

### Síntoma

Se espera que `OUT_ref_cache` reutilice resultados completos del solver o que evite reprocesar piezas equivalentes, pero no ocurre.

### Causa real

`OUT_ref_cache` no está pensado como caché persistente de soluciones de `compute_ref`.

Se usa para almacenar datos intermedios de `load_slot` asociados al programa fuente.

### Qué no hace

- no reutiliza resultados completos de solver entre ejecuciones
- no evita por sí mismo recalcular una pieza geométricamente equivalente con otro ID
- no sustituye una deduplicación real de piezas

### Acción recomendada

No interpretar `OUT_ref_cache` como sistema de cacheado global de soluciones.

Si se quiere evitar recomputación de piezas equivalentes, hace falta una deduplicación explícita basada en firma geométrica o criterio similar.

## 10. Se reprocesan piezas repetidas con IDs distintos

### Síntoma

Dos piezas iguales o muy parecidas se vuelven a evaluar varias veces porque provienen de distintos `.cnc` o aparecen con IDs distintos.

### Causa probable

El pipeline actual no implementa todavía una deduplicación geométrica real de piezas equivalentes.

### Qué comprobar

1. comparar geometría y metadata entre piezas repetidas
2. revisar si cambian solo el ID o también la forma real
3. comprobar si ambas han pasado por `compute_ref` por separado

### Acción recomendada

A día de hoy esto debe considerarse una limitación conocida del flujo.

Si no interesa estadística separada por ID, la mejora correcta es introducir deduplicación antes de lanzar solver.

## 11. El proyecto borra resultados anteriores al ejecutar

### Síntoma

Se lanza una nueva corrida y desaparecen salidas anteriores.

### Causa real

El pipeline actual limpia varios directorios al inicio para trabajar desde un estado limpio.

### Qué comprobar

1. revisar si se limpian `OUT_cnc`, `OUT_png`, `OUT_dxf`, `OUT_solutions`
2. revisar si se limpian `_internal/parsed_parts` y `OUT_ref_cache`
3. confirmar si la ejecución está pensada como reconstrucción total

### Acción recomendada

No usar este pipeline como si fuera incremental mientras no exista una política específica para conservar resultados.

Si hace falta trazabilidad por lotes, guardar copia de salida antes de ejecutar otra vez.

## 12. No aparece `summary.json`

### Síntoma

El solver se ha ejecutado parcialmente, pero no aparece `summary.json` en `OUT_solutions`.

### Causas probables

- la fase de evaluación no llegó a completarse
- el robot no tenía piezas o no tenía herramientas válidas
- falló la generación de resumen después de las combinaciones

### Qué comprobar

1. confirmar que existan carpetas de combinaciones pieza + herramienta
2. comprobar si el robot tenía piezas en `OUT_cnc`
3. comprobar si la selección de herramientas dio algún resultado
4. revisar logs o excepciones al final del proceso

### Acción recomendada

Si no existe `summary.json`, revisar primero si realmente hubo combinaciones procesadas.

Muchas veces el problema no está en el resumen, sino en que no hubo entradas válidas suficientes para generarlo.

## 13. El material no se interpreta como esperaba

### Síntoma

Una pieza aparece con densidad, ferromagnetismo o familia de material que no coincide con lo esperado.

### Causas probables

- el texto de `MATERIAL` no coincide con ningún alias conocido
- la familia configurada en `materials.known` no incluye ese token
- el pipeline cae a un perfil genérico

### Qué comprobar

1. revisar el valor real de `MATERIAL` en la cabecera `META`
2. revisar `materials.known` y sus `aliases`
3. comprobar si el token esperado está realmente incluido

### Acción recomendada

Añadir o corregir alias en `config.json`.

No meter lógica fija nueva en código si el problema se resuelve mejor ampliando los alias del material.

## 14. La herramienta por defecto no se encuentra aunque el nombre parece correcto

### Síntoma

`default_tool` parece bien escrito, pero el robot no la usa.

### Causas probables

- el nombre no coincide con el fichero real
- hay diferencias entre usar nombre con extensión o sin extensión
- el JSON existe, pero está mal ubicado
- la herramienta falla antes de llegar a estar procesada

### Qué comprobar

1. nombre exacto del fichero dentro de `TOOLS/`
2. presencia o ausencia de `.json`
3. ruta real del fichero
4. si aparece resultado correspondiente en `TOOLS/processed/`

### Acción recomendada

Usar en `config.json` el nombre exacto del fichero con extensión `.json` para evitar ambigüedades documentales.

## 15. Hay salida de solver, pero la solución sigue siendo mala o poco útil

### Síntoma

La combinación no falla técnicamente, pero la calidad de la solución no convence.

### Posibles causas

- herramienta poco centrada respecto a la pieza
- agarre válido pero subóptimo
- excesiva distancia entre centro de herramienta y centro de pieza
- número de elementos activos poco favorable

### Qué comprobar

1. `center_distance_approx`
2. `score_distance_centers_approx`
3. `tool_active_count`
4. comparar varias herramientas válidas para la misma pieza

### Acción recomendada

No quedarse solo con la primera solución válida.

Para análisis de calidad o recomendaciones de herramienta, conviene comparar todas las combinaciones válidas y priorizar las que mejor centren la herramienta y cubran más piezas con menos cambios.

## 16. No se sabe por dónde empezar a revisar un lote problemático

### Orden recomendado de diagnóstico

### Paso 1. Confirmar entrada

- revisar que existan `.cnc` en `INPUT/`
- comprobar si hubo renombrado desde `.lpp`

### Paso 2. Confirmar routing

- revisar `OUT_cnc` de ANTHRO y SCARA
- confirmar dónde ha acabado cada pieza

### Paso 3. Confirmar herramientas

- revisar `default_tool`
- revisar `allow_other_tools`
- comprobar existencia real de herramientas en `TOOLS/`

### Paso 4. Confirmar solver

- revisar carpetas en `OUT_solutions/<pieza>/<herramienta>/`
- comprobar presencia de `metadata_parser.json`

### Paso 5. Confirmar resultado final

- revisar `status`
- revisar `solution_valid`
- revisar overlays y `summary.json`

## 17. Checklist corto de diagnóstico

Cuando algo falle, este es el orden mínimo recomendado:

1. existe entrada válida en `INPUT/`
2. existe `config.json` coherente
3. SCARA está realmente habilitado o no
4. las herramientas configuradas existen en `TOOLS/`
5. la pieza llega al robot esperado
6. se genera carpeta de combinación en `OUT_solutions`
7. existe `metadata_parser.json`
8. `status` y `solution_valid` explican el resultado
9. el overlay revisado corresponde a la combinación correcta
10. `summary.json` refleja lo observado

## 18. Problemas que hoy son limitaciones conocidas, no fallos puntuales

Estos puntos conviene tratarlos como limitaciones actuales del sistema:

- no hay deduplicación geométrica real de piezas repetidas
- `OUT_ref_cache` no es caché persistente de soluciones
- si `allowed_tools` no da el resultado esperado, suele ser por desajuste de nombres o por combinación con `default_tool` y `allow_other_tools`
- la ejecución no es incremental y rehace salidas principales

## 19. Qué ficheros mirar primero

Cuando algo no cuadre y después de revisar logs, empezar por este orden:

1. `config.json`
2. `OUT_cnc/<pieza>.cnc`
3. `OUT_solutions/<pieza>/<herramienta>/metadata_parser.json`
4. `OUT_solutions/summary.json`
5. `OUT_solutions/report/`



