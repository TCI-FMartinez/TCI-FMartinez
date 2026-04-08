# parser_lpp_BATCH

Pipeline para separar programas `.lpp`/`.cnc` en piezas individuales, generar sus salidas geométricas y evaluar cada pieza con todas las herramientas disponibles mediante `compute_ref.exe`.

## Principal

`main.py` ejecuta dos fases seguidas:

1. fase de parsing y clasificación por robot
   - renombra `.lpp` a `.cnc` dentro de `INPUT`
   - lee cabecera del programa origen
   - separa cada pieza en un `.cnc` individual
   - reescribe la cabecera de cada pieza con metadata calculada
   - clasifica cada pieza entre `SCARA` o `ANTHRO`
   - genera su `OUT_png` y `OUT_dxf` dentro de la carpeta del robot asignado

2. fase de optimización pieza + herramienta
   - recorre los `.cnc` generados en `ANTHRO/OUT_cnc` y `SCARA/OUT_cnc`
   - recorre todas las herramientas JSON del directorio `TOOLS`
   - genera una versión procesada de cada herramienta en `TOOLS/processed`
   - construye un `ref_*.json` por pieza
   - llama a `module_ai2/compute_ref.exe`
   - guarda resultados por combinación dentro de `ANTHRO/OUT_solutions` o `SCARA/OUT_solutions`
   - genera `metadata_parser.json` por combinación
   - genera `summary.json` y `report/` por robot
   - genera PNG de overlay cuando existe geometría real de solución

## FLUJO

```text
INPUT/*.lpp|*.cnc
   -> ANTHRO/OUT_cnc/*.cnc
   -> ANTHRO/OUT_png/*.png
   -> ANTHRO/OUT_dxf/*.dxf
   -> ANTHRO/OUT_solutions/<pieza>/<herramienta>/

INPUT/*.lpp|*.cnc
   -> SCARA/OUT_cnc/*.cnc
   -> SCARA/OUT_png/*.png
   -> SCARA/OUT_dxf/*.dxf
   -> SCARA/OUT_solutions/<pieza>/<herramienta>/
```

## Estructura de carpetas

```text
parser_lpp_BATCH/
├── INPUT/
├── config.json
├── ANTHRO/
│   ├── OUT_cnc/
│   ├── OUT_dxf/
│   ├── OUT_png/
│   └── OUT_solutions/
├── SCARA/
│   ├── OUT_cnc/
│   ├── OUT_dxf/
│   ├── OUT_png/
│   └── OUT_solutions/
├── OUT_ref_cache/
├── TOOLS/
│   ├── *.json
│   └── processed/
├── module_ai2/
│   ├── compute_ref.exe
│   └── compute_tool.py
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

## Configuración runtime

El comportamiento de `main.py` se controla desde `config.json`.

Ejemplo:

```json
{
  "compute_ref": {
    "max_compute_time": 2,
    "enhance_opti": 1
  },
  "robots": {
    "anthro": {
      "root_dir": "ANTHRO"
    },
    "scara": {
      "root_dir": "SCARA",
      "filters": {
        "max_bbox_x": 500.0,
        "max_bbox_y": 500.0,
        "max_weight_kg": 6.0,
        "ferromagnetic": null,
        "material_family_any": [],
        "material_contains_any": []
      }
    }
  },
  "materials": {
    "known": {
      "STEEL": {
        "aliases": ["FE", "S235", "ACERO", "STEEL"],
        "density_g_cm3": 7.85,
        "ferromagnetic": true
      }
    }
  }
}
```

### Descripciones

- `compute_ref.max_compute_time`
  - tiempo máximo que se pasa a `compute_ref.exe` por combinación pieza + herramienta
- `compute_ref.enhance_opti`
  - quinto argumento del solver
- `robots.anthro.root_dir`
  - carpeta raíz de salidas del robot antropomórfico
- `robots.scara.root_dir`
  - carpeta raíz de salidas del robot SCARA
- `robots.scara.filters`
  - filtros para decidir si una pieza va a `SCARA`; si no pasa, va a `ANTHRO`
- `materials.known`
  - catálogo de materiales conocidos
- `materials.known.<FAMILIA>.aliases`
  - tokens compatibles para reconocer el material real en los META

Nota:
Si en la cabecera de una pieza aparece `FE`, `material_profile()` no necesita lógica fija en código para entenderlo: lo resolverá con `config.json` como familia `STEEL`, densidad base `7.85 g/cm3` y `ferromagnetic=true`.

### Orden de resolución del material

1. Se lee `MATERIAL` desde la metadata real de la pieza.
2. Se compara contra los alias definidos en `config.json`.
3. Si hay match, se aplican sus propiedades.
4. Si no hay match, se cae a un perfil genérico.

## Entradas

### 1. Programas de corte

Coloca los archivos fuente en `INPUT/`.

Se aceptan:
- `.lpp`
- `.cnc`

### 2. Herramientas

Coloca las herramientas en `TOOLS/` como JSON.

El script admite varias variantes de estructura y las aplana antes de llamar a `compute_tool.py`.

### 3. Configuración del solver, rutas y alias de material

Edita `config.json` para controlar:
- tiempo máximo de compute
- parámetro `enhance_opti`
- rutas de `SCARA` y `ANTHRO`
- filtros de clasificación a SCARA
- equivalencias de material

### 4. Material del solver

No hace falta un `material.json` global.

Para cada pieza, `main.py` genera automáticamente un `material.json` temporal a partir de las líneas `META` de su `.cnc` separado, usando sobre todo:

- `MATERIAL`
- `THICKNESS`
- `DENSITY_G_CM3`
- `FERROMAGNETIC`

Ese JSON por pieza es el que se pasa a `compute_ref.exe`.

Unidad de densidad:
- en metadata y `config.json`: `g/cm3` (`DENSITY_G_CM3`)
- en el `material.json` que se entrega a `compute_ref.exe`: `kg/mm3`
- conversión aplicada por `main.py`: `Density = DENSITY_G_CM3 * 1e-6`

## Salidas

### ANTHRO/OUT_cnc y SCARA/OUT_cnc

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

### ANTHRO/OUT_png y SCARA/OUT_png

PNG de contorno por pieza.

### ANTHRO/OUT_dxf y SCARA/OUT_dxf

DXF por pieza.

### ANTHRO/OUT_solutions y SCARA/OUT_solutions

Se crea una carpeta por combinación pieza + herramienta:

```text
SCARA/OUT_solutions/
└── ID11_W56240401/
    ├── material.json
    └── tool_17682099861849268/
        ├── ref_ID11_W56240401.json
        ├── ref_ID11_W56240401_solution.json
        ├── metadata.json
        ├── metadata_parser.json
        └── ID11_W56240401__tool_17682099861849268.png
```

Además, cada robot tiene:

```text
SCARA/OUT_solutions/
├── png/
├── summary.json
└── report/
```

Y lo mismo para `ANTHRO/OUT_solutions/`.

## Qué guarda metadata_parser.json

Cada combinación guarda metadata normalizada para poder compararla después.

Campos importantes:

- `robot`
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

## Criterio de clasificación SCARA

La decisión la toma `modules/scara_router.py` usando la metadata calculada de la pieza y los filtros configurados en:

```json
robots.scara.filters
```

Filtros soportados:

```json
{
  "max_bbox_x": 500.0,
  "max_bbox_y": 500.0,
  "max_weight_kg": 6.0,
  "ferromagnetic": null,
  "material_family_any": ["STEEL", "STAINLESS"],
  "material_contains_any": ["INOX", "S235"]
}
```

Si la pieza pasa esos filtros, va a `SCARA/`.
Si no los pasa, va a `ANTHRO/`.

## Qué mirar primero al revisar resultados

Para revisar resultados, empieza por:

- `SCARA/OUT_solutions/summary.json`
- `ANTHRO/OUT_solutions/summary.json`

Y luego por los informes:

- `SCARA/OUT_solutions/report/`
- `ANTHRO/OUT_solutions/report/`
