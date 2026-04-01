# parser_lpp_BATCH

Pipeline para separar programas `.lpp`/`.cnc` en piezas individuales, generar sus salidas geométricas y evaluar cada pieza con todas las herramientas disponibles mediante `compute_ref.exe`.

## Qué hace ahora mismo

`main.py` ejecuta dos fases seguidas:

1. fase de parsing y salidas base
   - renombra `.lpp` a `.cnc` dentro de `INPUT`
   - lee cabecera del programa origen
   - separa cada pieza en un `.cnc` individual
   - reescribe la cabecera de cada pieza con metadata calculada
   - genera `OUT_png` y `OUT_dxf`
   - clasifica además si la pieza pasa o no los filtros de `SCARA`

2. fase de optimización pieza + herramienta
   - recorre todos los `.cnc` generados en `OUT_cnc`
   - recorre todas las herramientas JSON del directorio `TOOLS`
   - genera una versión procesada de cada herramienta en `TOOLS/processed`
   - construye un `ref_*.json` por pieza
   - llama a `module_ai2/compute_ref.exe`
   - guarda resultados por combinación en `OUT_solutions`
   - genera `metadata.json` por combinación
   - genera `OUT_solutions/summary.json` con el resumen global
   - genera PNG de overlay cuando existe geometría real de solución

## Idea general del flujo

```text
INPUT/*.lpp|*.cnc
   -> OUT_cnc/*.cnc
   -> OUT_png/*.png
   -> OUT_dxf/*.dxf
   -> OUT_solutions/<pieza>/<herramienta>/
        - ref_<pieza>.json
        - *_solution.json   (si compute_ref lo genera)
        - metadata.json
        - <pieza>__<herramienta>.png   (si hay solución dibujable)
```

## Estructura de carpetas relevante

```text
parser_lpp_BATCH/
├── INPUT/
├── OUT_cnc/
├── OUT_dxf/
├── OUT_png/
├── OUT_solutions/
├── SCARA/
│   ├── OUT_cnc/
│   ├── OUT_dxf/
│   └── OUT_png/
├── TOOLS/
│   ├── *.json
│   └── processed/
├── module_ai2/
│   ├── compute_ref.exe
│   ├── compute_tool.py
│   └── material.json
├── modules/
└── main.py
```

## Requisitos

- Python 3.10 o superior
- `numpy`
- `opencv-python`
- `shapely`

Instalación:

```bash
pip install numpy opencv-python shapely
```

## Requisitos del solver

`compute_ref.exe` es un binario de Windows.

- en Windows se ejecuta directamente
- en Linux o macOS necesitas `wine`

Uso esperado del solver:

```text
compute_ref.exe <refFileJson> <toolFileJson> <materialFileJson> <maxComputeTime> <enhanceOpti>
```

Importante: `compute_ref.exe` no recibe el `.cnc` directamente. Recibe el `ref_*.json` generado por `main.py`.

## Ejecución

Desde la raíz del proyecto:

```bash
python main.py
```

## Entradas

### 1. Programas de corte

Coloca los archivos fuente en `INPUT/`.

Se aceptan:
- `.lpp`
- `.cnc`

### 2. Herramientas

Coloca las herramientas en `TOOLS/` como JSON.

El script admite varias variantes de estructura y las aplana antes de llamar a `compute_tool.py`.

### 3. Material del solver

Debe existir:

```text
module_ai2/material.json
```

## Salidas

### OUT_cnc

Un `.cnc` por pieza. La cabecera de cada pieza se reescribe con líneas `META` como:

```text
( META SOURCE_FILE : archivo_origen.cnc )
( META MATERIAL : INOX )
( META THICKNESS : 10 )
( META DENSITY_G_CM3 : 7.9 )
( META FERROMAGNETIC : NO )
( META BBOX_X : 123.456 )
( META BBOX_Y : 78.9 )
( META AREA_MM2 : 5432.1 )
( META WEIGHT_KG : 0.4291 )
```

### OUT_png

PNG de contorno por pieza.

### OUT_dxf

DXF por pieza.

### OUT_solutions

Se crea una carpeta por combinación pieza + herramienta:

```text
OUT_solutions/
└── ID11_W56240401/
    └── tool_17682099861849268/
        ├── ref_ID11_W56240401.json
        ├── ref_ID11_W56240401_solution.json
        ├── metadata.json
        └── ID11_W56240401__tool_17682099861849268.png
```

Además:

```text
OUT_solutions/
├── png/
└── summary.json
```

## Qué guarda metadata.json

Cada combinación guarda metadata normalizada para poder compararla después.

Campos importantes:

- `piece_file`
- `piece_id`
- `piece_reference`
- `piece_material`
- `piece_thickness`
- `piece_center_approx`
- `tool_file`
- `tool_elements_total`
- `solution_json`
- `solution_found`
- `solution_geometry_found`
- `solution_valid`
- `status`
- `tool_center_approx`
- `center_distance_approx`
- `score_distance_centers_approx`
- `tool_active_indexes`
- `tool_active_count`
- `returncode_raw`
- `returncode_signed`
- `solver_error_flag`
- `time_limit_hit`
- `solver_xmin`
- `solver_fxmin`

## Significado de status

El campo `status` separa claramente casos que antes quedaban mezclados:

- `valid`
  - el solver devolvió una solución utilizable
- `infeasible_cannot_lift`
  - el solver encontró una colocación geométrica pero no puede levantar la pieza
  - corresponde al flag `-6`
- `solver_error`
  - el solver terminó con otro flag no válido
- `completed_without_geometry`
  - hay JSON de salida pero no se ha podido extraer geometría real de solución
- `completed_without_solution`
  - la ejecución terminó pero no apareció un fichero de solución usable
- `execution_error`
  - el proceso ni siquiera pudo ejecutarse correctamente

## Importante sobre el código 4294967290

En Windows, `compute_ref.exe` puede devolver `4294967290`.

Eso no es un código extraño nuevo: equivale a `-6` interpretado como entero sin signo de 32 bits.

El script lo normaliza automáticamente a:

```text
returncode_signed = -6
```

y lo clasifica como:

```text
status = infeasible_cannot_lift
```

## Criterio de puntuación actual

Por ahora el campo preparado para ranking es:

- `score_distance_centers_approx`

Ese valor coincide con la distancia aproximada entre:
- centro de la pieza
- centro aproximado de colocación de la herramienta

Más adelante se puede ampliar con penalizaciones por:
- cantidad de útiles activos
- tiempo de cómputo
- flags del solver
- offset respecto al centro geométrico

## Módulos clave

### main.py

Orquestación completa del pipeline.

### modules/parse_head.py

Extrae metadatos de cabecera del CNC original.

### modules/parse_parts.py

Separa el programa en piezas individuales.

### modules/draw_part.py

Reconstruye contornos y dibuja el PNG de la pieza.

### modules/cnc_to_dxf.py

Convierte la pieza a DXF.

### module_ai2/compute_tool.py

Preprocesa la herramienta para añadir polígonos.

### module_ai2/compute_ref.exe

Resuelve la colocación de la herramienta sobre la pieza.

## Limitaciones conocidas

- si falta `shapely`, no se podrá construir correctamente el `ref JSON`
- si falta `wine` fuera de Windows, `compute_ref.exe` no podrá ejecutarse
- una herramienta puede aparecer duplicada si en `TOOLS` conviven versiones equivalentes con distinto nombre
- la distancia entre centros es aproximada y depende de la geometría que el solver haya dejado en su JSON de salida
- `solution_found` no implica siempre `solution_valid`

## Análisis de resultados previos

Para revisar resultados, empieza por `OUT_solutions/summary.json` y filtra primero por:

1. `status == "valid"`
2. menor `score_distance_centers_approx`
3. menor `tool_active_count`
