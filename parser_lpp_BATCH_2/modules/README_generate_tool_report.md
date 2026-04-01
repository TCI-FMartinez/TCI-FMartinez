# Documentación de `generate_tool_report.py`

## 1. Propósito

`generate_tool_report.py` es un script de análisis que procesa un archivo `summary.json` con resultados de evaluación de piezas frente a distintas herramientas y genera un informe automático con:

- estadísticas globales de éxito y fallo
- estadísticas por herramienta
- resumen por pieza
- ranking global de herramientas orientado a minimizar cambios de herramienta
- recomendaciones automáticas de rediseño a partir de patrones de fallo

El objetivo principal es responder dos preguntas:

1. qué herramienta o familia de herramientas cubre más piezas
2. qué cambios de diseño tienen más sentido para los casos que no resuelven algunas herramientas

---

## 2. Entrada esperada

El script recibe como entrada un JSON con una lista de resultados, donde cada elemento representa la evaluación de una pieza con una herramienta concreta.

Ejemplo de campos relevantes por fila:

- `piece_file`
- `piece_id`
- `piece_reference`
- `piece_center_approx`
- `tool_file`
- `tool_elements_total`
- `solution_valid`
- `status`
- `tool_active_count`
- `solver_error_flag`
- `solver_xmin`
- `solver_fxmin`
- `center_distance_approx`

### Suposiciones importantes

- El JSON de entrada debe ser una lista.
- Cada fila representa una combinación pieza-herramienta.
- La validez final de la solución se toma desde `solution_valid`.
- El identificador lógico de pieza se obtiene, por orden de prioridad, de:
  - `piece_reference`
  - `piece_id`
  - `piece_file`

---

## 3. Salidas generadas

El script crea cuatro archivos en la carpeta de salida:

### 3.1 Markdown principal

Archivo:

- `<base-name>.md`

Contenido:

- resumen general
- configuración de pesos
- disponibilidad de distancia centro-centro
- estados agregados
- ranking global de herramientas
- rendimiento por herramienta
- estado por pieza
- recomendaciones automáticas
- piezas con una única herramienta válida

### 3.2 CSV resumen

Archivo:

- `<base-name>_overview.csv`

Contenido:

- métricas globales
- conteos por estado
- métricas resumidas por herramienta

### 3.3 CSV por pieza

Archivo:

- `<base-name>_pieces.csv`

Contenido:

- herramientas válidas por pieza
- herramientas inválidas por pieza
- mejor herramienta por `fxmin`
- herramienta preferida para minimizar cambios

### 3.4 JSON resumen estructurado

Archivo:

- `<base-name>_summary.json`

Contenido:

- `overview`
- `tool_stats`
- `piece_stats`
- `recommendations`

Este archivo es útil si más adelante quieres alimentar otro script, una UI o una fase posterior de análisis.

---

## 4. Flujo interno del script

## 4.1 Carga y enriquecimiento

La función `load_rows()`:

- carga el JSON
- deriva el nombre lógico de herramienta a partir de `tool_file`
- asigna el grupo de robot:
  - `SCARA` si `piece_file` empieza por `SCARA/`
  - `ANTHRO` en caso contrario
- prepara tres campos de distancia:
  - `center_distance_actual`
  - `center_distance_proxy`
  - `center_distance_used`

### Distancia centro-centro

El script intenta usar primero:

- `center_distance_approx`

Si no existe y se activa la opción `--use-distance-proxy`, calcula una distancia aproximada como:

- distancia euclídea entre `piece_center_approx` y `solver_xmin[:2]`

Esto se guarda como:

- `center_distance_proxy`

Y si se usa para puntuación:

- `center_distance_used`
- `center_distance_source = proxy_solver_xmin`

### Advertencia

Este proxy no siempre representa la distancia real entre el centro geométrico de herramienta y el centro de pieza. Solo es una aproximación útil si el origen usado por `solver_xmin` es comparable entre herramientas.

---

## 4.2 Agrupación por pieza

La función `group_by_piece()` agrupa las filas por pieza para poder responder:

- cuántas herramientas validan una misma pieza
- qué piezas no tienen ninguna solución válida
- qué piezas obligan a mantener una herramienta secundaria

---

## 4.3 Cálculo de estadísticas por herramienta

La función `build_stats()` calcula por herramienta:

- intentos
- válidas
- no válidas
- piezas cubiertas
- tasa de cobertura
- tasa de éxito
- media de activos en válidas
- media de activos en no válidas
- media de `solver_fxmin` en válidas
- media de `solver_fxmin` en no válidas
- media de distancia centro-centro válida
- conteo de estados

---

## 4.4 Ranking global de herramienta

La función `compute_tool_scores()` calcula una puntuación global por herramienta a partir de tres componentes normalizados:

1. cobertura global
2. distancia media al centro
3. calidad media del solver (`fxmin`)

### Sentido de cada criterio

- cobertura: cuanto mayor, mejor
- distancia: cuanto menor, mejor
- `fxmin`: cuanto menor, mejor

### Normalización

Se usan dos funciones:

- `normalize_benefit()` para métricas donde más es mejor
- `normalize_cost()` para métricas donde menos es mejor

### Score global

La puntuación final se calcula con media ponderada:

```text
global_score = weighted_score([
    (weight_coverage, coverage_score),
    (weight_distance, distance_score),
    (weight_fxmin, fx_score),
])
```

Pesos por defecto:

- cobertura: `0.75`
- distancia: `0.15`
- fxmin: `0.10`

Esto hace que el criterio dominante sea minimizar variedad de herramienta, no optimizar solo una pieza aislada.

---

## 4.5 Selección preferida por pieza

La función `choose_preferred_tool_per_piece()` elige una herramienta preferida para cada pieza entre las válidas.

No se limita a escoger la de mejor `fxmin`. Combina:

- score global de la herramienta
- distancia local al centro para esa pieza
- `fxmin` local para esa pieza

Pesos locales:

- score global: `0.70`
- distancia local: `0.20`
- `fxmin` local: `0.10`

Así, una herramienta algo menos centrada puede seguir siendo preferida si reduce mucho los cambios de herramienta en el conjunto total.

---

## 4.6 Recomendaciones automáticas

La función `derive_recommendations()` genera conclusiones a partir de patrones detectados.

### Casos contemplados

#### a) Piezas sin solución global

Si ninguna herramienta resuelve una pieza:

- recomienda diseñar una herramienta dedicada o una variante específica

#### b) Fallos por `infeasible_cannot_lift`

Interpreta que:

- la geometría puede encajar
- pero la herramienta no consigue levantar o repartir bien la carga

Si además la herramienta está completamente activada, sugiere:

- más capacidad útil por punto
- mejor reparto de apoyo
- más puntos periféricos o mejor brazo resistente

#### c) Fallos por `-5` o `solver_error`

Los interpreta como problema geométrico, por ejemplo:

- paso entre actuadores demasiado grande
- huella rígida o poco adaptable
- interferencia local con la pieza

Y recomienda:

- compactar la matriz
- reducir paso
- usar módulos más pequeños
- diseñar variante específica para zonas estrechas

#### d) Patrón dominante de sustitución

Si detecta que unas herramientas fallan y otra familia resuelve repetidamente, lo indica como referencia para rediseño.

---

## 5. Interpretación del score

El ranking global no intenta decir qué herramienta es la mejor en una sola pieza.

Intenta responder:

- cuál conviene mantener como herramienta principal para abarcar el mayor número de piezas
- cuál permite reducir cambios de herramienta en producción

Por eso, una herramienta con mejor `fxmin` puntual puede quedar por debajo de otra que cubra más piezas.

Este comportamiento es intencional.

---

## 6. Uso por línea de comandos

## 6.1 Uso básico

```bash
python modules/generate_tool_report.py summary.json --output-dir report_out --base-name informe_herramientas
```

## 6.2 Uso con valores por defecto

```bash
python modules/generate_tool_report.py
```

Esto usará por defecto:

- `input_json = summary.json`
- `output_dir = report_out`
- `base_name = tool_report`

---

## 7. Parámetros disponibles

### Argumentos posicionales

#### `input_json`

Ruta al `summary.json` de entrada. Es opcional; si no se proporciona, se usa `summary.json`.

### Argumentos opcionales

#### `--output-dir`

Carpeta de salida.

Valor por defecto:

```text
report_out
```

#### `--base-name`

Prefijo usado para nombrar los archivos de salida.

Valor por defecto:

```text
tool_report
```

---

## 8. Limitaciones

### 8.1 Distancia centro-centro incompleta

Si `center_distance_approx` viene vacío o inconsistente:

- la comparación de distancia entre herramientas puede no ser fiable
- el proxy con `solver_xmin` debe interpretarse con cautela

### 8.2 Dependencia de la semántica de `fxmin`

El script asume que valores más bajos de `solver_fxmin` son mejores.

Si en una versión futura del solver cambia esa semántica, habrá que revisar la normalización.

### 8.3 No calcula centro geométrico real de herramienta

Ahora mismo no abre los JSON de definición geométrica de herramienta para calcular su centro real.

Si quieres una distancia centro-centro robusta entre familias, lo correcto sería:

- leer la geometría real de cada herramienta
- calcular su centro geométrico o centro funcional
- transformar ese centro con la pose final
- medir después la distancia a `piece_center_approx`

### 8.4 No optimiza parque mínimo multi-herramienta

El script rankea cada herramienta individualmente y propone una preferida por pieza, pero no resuelve todavía un problema formal de:

- cobertura mínima con el menor número de herramientas
- herramienta principal + secundaria óptima

Eso sería una versión posterior tipo set cover o greedy cover.



## 9. Mejoras recomendadas

Evoluciones lógicas para una siguiente versión:

1. cálculo real de distancia centro herramienta-centro pieza a partir de la geometría
2. análisis por familias de pieza
3. propuesta automática de parque mínimo de herramientas
4. exportación a Excel
5. inclusión de imágenes de solución en el informe
6. score configurable por perfil de negocio:
   - mínima variedad
   - máxima robustez
   - máxima cercanía al centro
   - mínimo número de actuadores activos



