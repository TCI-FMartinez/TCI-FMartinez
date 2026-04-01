# dxf_to_tool_json.py

Script para convertir un archivo DXF de una herramienta en un JSON con el esquema:
- `pads`
- `contorno`

El objetivo es automatizar la conversión que estábamos haciendo manualmente a partir de la geometría del DXF.

Además, se incluye un segundo script para ejecutar la conversión por lotes sobre una carpeta completa de DXF.

## Archivos incluidos

- `dxf_to_tool_json.py` -> conversión de un único DXF a JSON (en desuso)
- `batch_convert_dxf_to_tool_json.py` -> conversión por lotes de una carpeta de DXF
- `dependencias.txt` -> dependencias Python necesarias

## Qué hace el script principal

El script `dxf_to_tool_json.py`:
- lee el DXF de entrada
- extrae todos los `CIRCLE` del model space
- convierte cada círculo en un `pad`
- detecta la zona central a partir de rectángulos `LWPOLYLINE`
- asigna dependencias según la posición del pad
- calcula el contorno exterior a partir de la geometría del dibujo
- genera un JSON compatible con el formato usado en tus herramientas

## Reglas implementadas

### 1. Conversión de círculos a pads
Cada entidad `CIRCLE` del DXF se convierte en un pad.

### 2. Clasificación por diámetro
Se contemplan estos diámetros:

- `36 mm` -> `type: 1` -> imán -> `force: 10.0`
- `50 mm` -> `type: 2` -> ventosa -> `force: 2.5`
- `80 mm` -> `type: 2` -> ventosa -> `force: 7.0`

Si aparece un diámetro fuera de tolerancia, el script falla con error.

### 3. Dependencias
La lógica actual es:

- pads dentro de la zona central -> `dependence: [0, 0]`
- pads laterales fuera de la zona central -> `dependence: [1, 0]`

Interpretación:
- `[0, 0]` = fijo, sin dependencia de ejes
- `[1, 0]` = lateral móvil en X

### 4. Detección de zona central
La zona central se obtiene buscando rectángulos `LWPOLYLINE` que crucen `X = 0`.
De esos candidatos, el script escoge el más ancho.

Esto está pensado para DXF con una estructura como la que has usado en `pos0` y `pos1`.

### 5. Orden de IDs
Los pads se numeran automáticamente con este criterio:
- primero por `Y` descendente
- luego por `X` ascendente

### 6. Contorno exterior
El contorno se calcula usando la caja exterior del dibujo a partir de:
- `LWPOLYLINE`
- `LINE`

El resultado se guarda como un rectángulo en este formato:

```json
"contorno": [
  [minX, maxY],
  [maxX, maxY],
  [maxX, minY],
  [minX, minY]
]
```

## Formato de salida

El JSON generado tiene esta estructura:

```json
{
  "pads": [
    {
      "id": 1,
      "posX": 0,
      "posY": 0,
      "type": 1,
      "force": 10.0,
      "is_active": false,
      "diameter": 36,
      "dependence": [0, 0]
    }
  ],
  "contorno": [
    [-250, 250],
    [250, 250],
    [250, -250],
    [-250, -250]
  ]
}
```

## Requisitos

- Python 3.10 o superior recomendado
- librería `ezdxf`

## Instalación

```bash
pip install -r dependencias.txt
```

## Uso del script principal

```bash
python dxf_to_tool_json.py entrada.dxf salida.json
```

Con salida legible:

```bash
python dxf_to_tool_json.py entrada.dxf salida.json --pretty
```

## Ejemplos del script principal

```bash
python dxf_to_tool_json.py "Herramienta H04_pos0.dxf" "Herramienta_H04_pos0_generado.json" --pretty
```

```bash
python dxf_to_tool_json.py "Herramienta H04_pos1.dxf" "Herramienta_H04_pos1_generado.json" --pretty
```

## Conversión por lotes

El script `batch_convert_dxf_to_tool_json.py` permite convertir todos los DXF de una carpeta usando `dxf_to_tool_json.py`.

### Qué hace

- recorre una carpeta de entrada
- busca archivos DXF según un patrón
- ejecuta el conversor para cada archivo
- genera un JSON de salida por cada DXF
- muestra un resumen final con conversiones correctas y fallidas

### Uso básico

```bash
python batch_convert_dxf_to_tool_json.py ./carpeta_dxf ./salida_json
```

Con salida legible:

```bash
python batch_convert_dxf_to_tool_json.py ./carpeta_dxf ./salida_json --pretty
```

### Ejemplos

```bash
python batch_convert_dxf_to_tool_json.py ./dxf ./json --pattern "Herramienta*.dxf" --pretty
```

```bash
python batch_convert_dxf_to_tool_json.py ./dxf ./json --pattern "*.dxf" --recursive --suffix "_generado"
```

### Opciones disponibles

- `--pattern "*.dxf"` -> filtra qué DXF convertir
- `--recursive` -> busca también en subcarpetas
- `--suffix "_generado"` -> sufijo del JSON de salida
- `--converter ruta/al/dxf_to_tool_json.py` -> permite indicar manualmente el conversor principal (en desuso)
- `--pretty` -> guarda el JSON con indentación

## Errores posibles

### No existe el DXF de entrada
Se produce si la ruta del archivo no es válida.

### El DXF no contiene entidades CIRCLE
Se produce si no hay círculos que puedan convertirse en pads.

### No se han encontrado rectángulos LWPOLYLINE
Se produce si el DXF no tiene la geometría necesaria para detectar la zona central.

### No se ha encontrado una zona central que cruce X=0
Se produce si el dibujo no tiene un bloque central reconocible con la lógica actual.

### Diámetro no soportado
Se produce si aparece un círculo con diámetro distinto de 36, 50 u 80 mm fuera de la tolerancia.

### El conversor principal no se encuentra al usar el script por lotes
Se produce si `batch_convert_dxf_to_tool_json.py` no encuentra `dxf_to_tool_json.py` y no se ha indicado con `--converter`.

## Limitaciones actuales

Este script funciona bien para DXF con una estructura similar a la que has usado hasta ahora.
No está pensado todavía para:
- detectar tipo por color
- detectar tipo por capa
- generar contornos complejos no rectangulares
- distinguir múltiples zonas móviles aparte de la central y laterales
- interpretar automáticamente diferentes lógicas mecánicas de dependencia

## Posibles mejoras

Siguientes versiones podrían incluir:
- detección por color del DXF
- detección por capa
- exportación de metadatos extra
- validación geométrica más estricta
- soporte para más diámetros o fuerzas personalizadas
- generación de CSV resumen tras la conversión por lotes

## Dependencias

Ver archivo:
- `dependencias.txt`
