# Parser CNC a piezas, PNG y DXF

Este proyecto separa archivos `.cnc` o `.lpp` con varias piezas, genera un `.cnc` independiente por pieza y crea salidas visuales y geométricas para cada una.

El flujo está pensado para láser de chapa y trabaja con la lógica de contornos definida por bloques `G65 P9102 ...` / `G65 P9104`, soportando movimientos `G0`, `G1`, `G2` y `G3`.

## Qué hace

- Renombra archivos `.lpp` a `.cnc` dentro de `INPUT`.
- Lee la cabecera del archivo original para extraer datos como material, espesor y formato de chapa.
- Separa cada pieza del archivo fuente y crea un `.cnc` individual en `OUTPUT`.
- Reescribe la cabecera de cada pieza con metadatos calculados.
- Genera un PNG encuadrado de cada pieza en `OUT_png`.
- Genera un DXF de cada pieza en `OUT_dxf`.
- Calcula para cada pieza:
  - bounding box en X e Y
  - área geométrica estimada
  - peso estimado
  - condición ferromagnética estimada según material

## Estructura esperada

```text
project/
├── INPUT/
├── OUTPUT/
├── OUT_png/
├── OUT_dxf/
├── main.py
└── modules/
    ├── parse_head.py
    ├── parse_parts.py
    ├── draw_part.py
    ├── cnc_to_dxf.py
    ├── discretiza_arco.py
    └── orientation.py
```


## Flujo de trabajo

### 1. Entrada

El script principal busca en `INPUT` archivos con extensión `.cnc`. Si encuentra `.lpp`, los renombra a `.cnc`.

### 2. Parseo de cabecera

`parse_head.py` extrae información del archivo fuente, por ejemplo:

- material
- espesor
- formato de chapa
- cantidad
- programa
- tipo

Estos datos se usan después para enriquecer cada pieza separada.

### 3. Separación de piezas

`parse_parts.py` detecta las piezas dentro del archivo y genera un `.cnc` por cada una en `OUTPUT`.

### 4. Enriquecimiento de cabecera por pieza

Cada pieza generada se reescribe con metadatos añadidos, por ejemplo:

```text
ID9
W86011504
( META SOURCE_FILE : SKRLJ-INOX-10.cnc )
( META MATERIAL : INOX )
( META THICKNESS : 10 )
( META DENSITY_G_CM3 : 7.9 )
( META FERROMAGNETIC : NO )
( META BBOX_X : 123.456 )
( META BBOX_Y : 78.9 )
( META AREA_MM2 : 5432.1 )
( META WEIGHT_KG : 0.4291 )
( META FORMAT_X : 1500 )
( META FORMAT_Y : 3000 )
```

### 5. Generación de PNG

`draw_part.py`:

- lee la geometría real de la pieza
- calcula el bounding box geométrico
- encuadra la pieza dentro del PNG
- opcionalmente cierra contornos abiertos para visualización
- superpone texto con métricas

En el PNG se puede mostrar:

- ID
- nombre
- tamaño del bounding box
- material
- espesor
- área
- peso
- si el material es ferromagnético o no

### 6. Generación de DXF

`cnc_to_dxf.py` convierte la geometría de cada pieza a DXF.

Soporta:

- líneas
- arcos
- círculos completos cuando el arco cierra sobre sí mismo
- simplificación de lead-in / lead-out según la lógica implementada
- cierre automático de contornos abiertos si se activa esa variante

## Cálculo de métricas

### Bounding box

Se calcula a partir de la geometría reconstruida de la pieza, no del texto de cabecera.

### Área

Se obtiene a partir de los contornos reconstruidos y discretizados, usando el área poligonal firmada.

### Peso

Se estima con:

```text
peso = área_mm2 × espesor_mm × densidad_kg_mm3
```

### Ferromagnetismo

Se estima heurísticamente a partir del material detectado en cabecera.

Ejemplos:

- acero al carbono: sí
- inox 304 / 316: no
- inox 430 / 409 / 441: sí
- aluminio, latón, cobre: no

Si el material no se reconoce con claridad, el estado puede quedar como `UNKNOWN`.

## Materiales y densidades heurísticas

Valores por defecto usados en el script:

- acero: `7.85 g/cm³`
- inox: `7.90 g/cm³`
- aluminio: `2.70 g/cm³`
- latón: `8.50 g/cm³`
- cobre: `8.96 g/cm³`

Estos valores son aproximados y sirven para clasificación y estimación rápida, no para metrología final.

## Requisitos

- Python 3.10 o superior recomendado
- `opencv-python`
- `numpy`

Instalación:

```bash
pip install opencv-python numpy
```

## Ejecución

Desde la carpeta raíz del proyecto:

```bash
python main.py
```

## Salidas

### Carpeta `OUT_cnc_`

Contiene un `.cnc` por pieza, con cabecera enriquecida.

Ejemplo:

```text
OUTPUT/
├── ID1_221785-7.cnc
├── ID2_217701-8.cnc
└── ...
```

### Carpeta `OUT_png`

Contiene una imagen por pieza.

Ejemplo:

```text
OUT_png/
├── ID1_221785-7_contours.png
├── ID2_217701-8_contours.png
└── ...
```

### Carpeta `OUT_dxf`

Contiene un DXF por pieza.

Ejemplo:

```text
OUT_dxf/
├── ID1_221785-7.dxf
├── ID2_217701-8.dxf
└── ...
```

## Detalles de implementación

### `main.py`

Responsable de:

- limpiar carpetas de salida
- renombrar extensiones
- recorrer archivos de `INPUT`
- leer cabecera del archivo fuente
- lanzar la separación de piezas
- detectar qué piezas nuevas se han generado
- reescribir metadatos por pieza
- crear PNG y DXF por cada pieza

### `parse_head.py`

Parsea la cabecera del programa CNC original.

### `parse_parts.py`

Separa las piezas del programa CNC original.

Importante: en la implementación actual, este módulo genera los archivos de pieza directamente en disco. No trabaja como parser puro que devuelva estructuras en memoria.

### `draw_part.py`

Genera la imagen PNG a partir de la geometría reconstruida.

### `cnc_to_dxf.py`

Reconstruye contornos y exporta DXF.

## Limitaciones conocidas

- El cálculo de peso depende de que el material y espesor estén bien definidos en la cabecera.
- La clasificación ferromagnética es heurística.
- Si el CNC contiene macros o variantes fuera del patrón esperado, puede requerir adaptación.
- El área se calcula a partir de geometría reconstruida y discretización de arcos, por lo que puede haber pequeñas diferencias respecto a CAD nativo.
- Si `parse_parts.py` no genera una cabecera mínima consistente por pieza, los módulos posteriores pueden fallar.

## Mejoras recomendadas

- Convertir `parse_parts.py` en un parser puro que devuelva piezas en memoria en vez de escribirlas directamente.
- Unificar definitivamente las variantes `draw_part_*` y `cnc_to_dxf_*` en una sola versión estable.
- Añadir filtrado automático por dimensiones, peso y ferromagnetismo antes de exportar.
- Guardar también CSV o JSON resumen de todas las piezas procesadas.
- Añadir tests con archivos CNC reales representativos.

## Uso típico

1. Copiar archivos `.cnc` o `.lpp` en `INPUT`.
2. Ejecutar `python main.py`.
3. Revisar piezas separadas en `OUTPUT`.
4. Revisar imágenes en `OUT_png`.
5. Revisar DXF en `OUT_dxf`.

