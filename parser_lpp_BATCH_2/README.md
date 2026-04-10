
# SORTING-Study

Pipeline para separar programas `.lpp` y `.cnc` en piezas individuales, clasificarlas por robot, generar sus salidas geométricas y evaluar cada pieza con herramientas compatibles mediante `compute_ref.exe`.

## Qué hace el proyecto

`main.py` ejecuta dos fases principales:

1. Parsing y clasificación por robot
   - renombra programas `.lpp` a `.cnc` dentro de `INPUT`
   - lee la cabecera del programa origen
   - separa cada pieza en un `.cnc` individual
   - recalcula y reescribe la cabecera `META` de cada pieza
   - clasifica cada pieza hacia `SCARA` o `ANTHRO`
   - si `robots.scara.enabled = false`, todas las piezas se asignan a `ANTHRO`
   - genera salidas geométricas por pieza (`OUT_png` y `OUT_dxf`)

2. Evaluación pieza + herramienta
   - recorre las piezas generadas para cada robot
   - selecciona herramientas según la configuración del robot
   - genera versiones procesadas de herramientas en `TOOLS/processed`
   - construye el `ref_*.json` de cada pieza
   - ejecuta `module_ai2/compute_ref.exe`
   - guarda resultados por combinación pieza + herramienta
   - genera `metadata_parser.json`, `summary.json` y los informes por robot
   - genera overlays PNG cuando existe geometría real de solución

## Flujo general

```text
INPUT/*.lpp|*.cnc
   -> parsing por pieza
   -> clasificación por robot
   -> OUTPUT/<robot>/OUT_cnc/*.cnc
   -> OUTPUT/<robot>/OUT_png/*.png
   -> OUTPUT/<robot>/OUT_dxf/*.dxf
   -> OUTPUT/<robot>/OUT_solutions/<pieza>/<herramienta>/
```

## Estructura principal

```text
SORTING-Study/
├── docs/
├── INPUT/
├── config.json
├── OUTPUT/
│   ├── ANTHRO/
│   │   ├── OUT_cnc/
│   │   ├── OUT_dxf/
│   │   ├── OUT_png/
│   │   └── OUT_solutions/
│   └── SCARA/
│       ├── OUT_cnc/
│       ├── OUT_dxf/
│       ├── OUT_png/
│       └── OUT_solutions/
├── OUT_ref_cache/
├── TOOLS/
│   ├── *.json
│   └── processed/
├── module_ai2/
│   ├── compute_ref.exe
│   └── compute_tool.py
├── modules/
├── main.py
└── README.md
```


## Requisitos

- matplotlib==3.10.3
- numpy==2.2.6
- openpyxl==3.1.5
- opencv-python==4.12.0.88
- scipy==1.16.2
- shapely==2.1.1

Instalación:

```bash
pip install -r requirements.txt
```

## Ejecución

Desde la raíz del proyecto:

```bash
python main.py
```

## Documentación relacionada

- `docs/configuracion.md`
- `docs/flujo_procesado.md`
- `docs/cache_y_limpieza.md`
- `docs/troubleshooting.md`

## Entradas

### Programas de corte

Coloca los archivos de corte en `INPUT/`.

Formatos admitidos:
- `.lpp`
- `.cnc`

### Herramientas

Coloca las herramientas en `TOOLS/` en formato JSON.

El pipeline admite distintas variantes de estructura y las normaliza.

### Configuración

Edita `config.json` para controlar:
- tiempo máximo de solver
- parámetro `enhance_opti`
- rutas de salida por robot
- filtros de clasificación a SCARA
- herramienta por defecto de cada robot
- posibilidad de probar otras herramientas
- materiales conocidos y alias

## Configuración de robots y herramientas

La lógica de selección de herramientas se controla en `config.json`, dentro de `robots`.

Resumen:
- `default_tool` define la herramienta montada por defecto
- `allow_other_tools` indica si el robot puede probar alternativas
- `allowed_tools` limita explícitamente las herramientas permitidas en SCARA
- `enabled=false` en SCARA desactiva por completo su participación en el pipeline

Comportamiento práctico:
- si `SCARA.enabled=false`, todas las piezas van a `ANTHRO`
- si `allow_other_tools=false`, el robot solo prueba su `default_tool`
- si `allow_other_tools=true`, prueba primero la herramienta por defecto y luego el resto permitido
- si `allowed_tools` tiene elementos, SCARA solo puede usar esa lista

--> Para el detalle completo de cada parámetro, ver `docs/configuracion.md`.

## Materiales

Para cada pieza, el pipeline genera un `material.json` temporal a partir de los `META` del `.cnc` separado, usando principalmente:
- `MATERIAL`
- `THICKNESS`
- `DENSITY_G_CM3`
- `FERROMAGNETIC`

No hace falta mantener un `material.json` global.

## Salidas

### OUT_cnc
Un `.cnc` por pieza, con cabecera `META` reescrita.

### OUT_png
PNG de contorno por pieza. Con información de dimensiones y peso unitario.

### OUT_dxf
DXF por pieza.

### OUT_solutions
Resultados por combinación pieza + herramienta.

Estructura de este directorio:

```text
OUTPUT/SCARA/OUT_solutions/
└── ID11_W56240401/
    ├── material.json
    └── tool_17682099861849268/
        ├── ref_ID11_W56240401.json
        ├── ref_ID11_W56240401_solution.json
        ├── metadata.json
        ├── metadata_parser.json
        └── ID11_W56240401__tool_17682099861849268.png
```

Además, cada robot genera:

```text
OUTPUT/<robot>/OUT_solutions/
├── png/
├── summary.json
└── report/
    ├── tool_report.xlsx
    ├── tool_report.md    
    └── tool_report_summary.json
```

## Qué contiene metadata_parser.json

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

## Requisitos del solver

`compute_ref.exe` es un binario de Windows.

- en Windows se ejecuta directamente
- en Linux o macOS requiere `wine` o solicitar la compilación para Linux o macOS.

## Criterio de clasificación hacia SCARA

La decisión se toma a partir de la metadata calculada de la pieza y de `robots.scara.filters`.

Filtros soportados:
- `max_bbox_x`
- `max_bbox_y`
- `max_weight_kg`
- `ferromagnetic`
- `material_family_any`
- `material_contains_any`

Si la pieza pasa esos filtros, va a `SCARA`. Si no, va a `ANTHRO`.

## Qué revisar primero al validar un lote

1. `OUTPUT/SCARA/OUT_solutions/summary.json`
2. `OUTPUT/ANTHRO/OUT_solutions/summary.json`
3. `OUTPUT/SCARA/OUT_solutions/report/`
4. `OUTPUT/ANTHRO/OUT_solutions/report/`
5. `OUTPUT/SCARA/OUT_solutions/png/`
6. `OUTPUT/ANTHRO/OUT_solutions/png/`

## Documentación relacionada

- `docs/configuracion.md`
- `docs/flujo_procesado.md`
- `docs/cache_y_limpieza.md`
- `docs/troubleshooting.md`

---