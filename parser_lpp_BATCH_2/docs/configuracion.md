
# SORTING-Study

# Configuración

Este documento describe la estructura y el comportamiento de `config.json`.

Muy importante:
- este documento distingue entre configuración declarada y comportamiento realmente aplicado por el código actual
- cuando haya discrepancias entre lo documentado y la implementación, debe prevalecer siempre el código
- en la versión actual del proyecto, no todos los campos presentes en `config.json` están siendo usados con la misma profundidad

## Objetivo

`config.json` controla:
- parámetros del solver
- rutas de salida por robot
- habilitación de SCARA
- selección de herramientas por robot
- filtros de clasificación de piezas
- catálogo de materiales conocidos
- nivel de depuración y metadatos de configuración

## Comportamiento general de carga

El archivo se trata con esta lógica:

1. si `config.json` no existe, el sistema intenta crearlo automáticamente con una plantilla por defecto
2. si existe, se carga y se mezcla con los valores por defecto internos del código
3. si faltan claves, esas claves se completan desde la configuración por defecto
4. si el JSON no puede leerse correctamente, el sistema cae a valores por defecto

Esto implica dos cosas:
- no hace falta que el usuario escriba absolutamente todas las claves si el código ya define defaults razonables
- la documentación debe indicar no solo la estructura ideal, sino también qué valores hereda el sistema cuando falta algo

## Estructura general

```json
{
  "_meta": {
    "config_version": 1,
    "generated_by": "@F_Martinez - TCI Cutting",
    "generated_at": "09/06/2024 12:00:00",
    "description": "Puedes editar los valores según tu instalación.",
    "debug_level": 1,
    "notes": [
            "Asegúrate de que las rutas de los robots sean correctas.",
            "Revisa los filtros para el robot SCARA según tus necesidades.",
            "Agrega o modifica materiales conocidos según tu inventario.",
            "el nivel de LOG es: 0 = sin LOG, 1 = LOG normal, 2 = LOG detallado (debug)."
        ]
  },
  "compute_ref": {
    "max_compute_time": 3,
    "enhance_opti": 1
  },
  "robots": {
    "anthro": {
      "root_dir": "OUTPUT/ANTHRO",
      "default_tool": "tool_H04_pos1.json",
      "allow_other_tools": true
    },
    "scara": {
      "root_dir": "OUTPUT/SCARA",
      "filters": {
        "max_bbox_x": 500.0,
        "max_bbox_y": 500.0,
        "max_weight_kg": 6.0,
        "ferromagnetic": null,
        "material_family_any": [],
        "material_contains_any": []
      },
      "enabled": true,
      "default_tool": "tool_A.json",
      "allow_other_tools": false,
      "allowed_tools": [
        "tool_A.json",
        "tool_B.json"
      ]
    }
  },
  "materials": {
    "known": {}
  }
}
```

## Diferencia entre plantilla interna y configuración actual

Conviene dejar esto documentado para evitar confusión:

- el `config.json` actual del proyecto usa `OUTPUT/ANTHRO` y `OUTPUT/SCARA`
- pero la plantilla interna por defecto en código todavía arrastra raíces por defecto `ANTHRO` y `SCARA`

Eso significa que:
- si el usuario ya tiene un `config.json` real, se usarán sus rutas configuradas
- si el sistema genera `config.json` automáticamente desde la plantilla interna.

Esto conviene corregir en código o remarcarlo en la documentación hasta que quede unificado.

## Bloque _meta

Bloque informativo para trazabilidad de la configuración.

### `config_version`
Versión del formato de configuración.

### `generated_by`
Autor o referencia de quien generó la plantilla.

### `generated_at`
Fecha de generación del archivo.

### `description`
Texto libre con contexto de uso.

### `debug_level`
Nivel de log del proceso.

Valores esperados:
- `0`: sin log
- `1`: log normal
- `2`: log detallado o debug

### `notes`
Lista de observaciones operativas para la instalación.

## Bloque compute_ref

Parámetros que se pasan al solver.

### `max_compute_time`
Tiempo máximo permitido por combinación pieza + herramienta.

Ejemplo:
```json
"max_compute_time": 3
```

### `enhance_opti`
Quinto argumento que se entrega a `compute_ref.exe`.

Ejemplo:
```json
"enhance_opti": 1
```

## Bloque robots

Define el comportamiento por robot.

### robots.anthro

#### `root_dir`
Carpeta raíz de salidas de ANTHRO.

#### `default_tool`
Herramienta montada por defecto en ANTHRO.

El código la resuelve por nombre exacto o por `stem`, por lo que puede encontrarse con o sin extensión `.json`.

#### `allow_other_tools`
Indica si ANTHRO puede probar otras herramientas además de la montada.

Comportamiento:
- `true`: prueba primero `default_tool` y luego el resto de herramientas disponibles en `TOOLS`
- `false`: solo prueba `default_tool`
- si `false` y la herramienta por defecto no existe, ANTHRO no prueba ninguna herramienta

### robots.scara

#### `enabled`
Indica si SCARA participa en el pipeline.

Comportamiento:
- `true`: SCARA puede recibir piezas si pasan los filtros
- `false`: SCARA queda deshabilitado y todas las piezas se envían a ANTHRO

#### `root_dir`
Carpeta raíz de salidas de SCARA.

#### `default_tool`
Herramienta montada por defecto en SCARA.

El código la resuelve por nombre exacto o por `stem`, igual que en ANTHRO.

#### `allow_other_tools`
Indica si SCARA puede probar herramientas adicionales.

Comportamiento:
- `true`: prueba primero `default_tool` y luego el resto de herramientas detectadas en `TOOLS`
- `false`: solo prueba `default_tool`
- si `false` y la herramienta por defecto no existe, SCARA no probará alternativas

#### `allowed_tools`
Lista blanca declarativa de herramientas permitidas para SCARA.

Estado actual:
- este campo existe en `config.json`
- está documentado en el proyecto
- pero en la versión actual revisada del código no aparece aplicado en la selección real de herramientas

Consecuencia:
- hoy por hoy, `allowed_tools` debe entenderse como intención de configuración o campo reservado
- no puede darse por hecho que limite realmente las herramientas de SCARA mientras no se implemente su uso en el código

Dicho de forma directa:
- ahora mismo la selección efectiva depende de `default_tool` y `allow_other_tools`
- no he visto evidencia de que `allowed_tools` esté filtrando el conjunto final en ejecución

#### `filters`
Criterios para decidir si una pieza puede asignarse a SCARA.

Campos soportados por el enrutado actual:
- `max_bbox_x`
- `max_bbox_y`
- `max_weight_kg`
- `ferromagnetic`
- `material_family_any`
- `material_contains_any`

Comportamiento:
- si una pieza incumple alguno de estos criterios, no va a SCARA
- si SCARA está deshabilitado, la pieza va directamente a ANTHRO
- el enrutado usa la metadata calculada de la pieza, no solo el nombre del archivo

## Precedencia real de selección de herramientas

La resolución actual debe entenderse así:

1. Se determina si la pieza va a SCARA o ANTHRO.
2. Se obtiene la herramienta por defecto configurada para ese robot.
3. En SCARA, se construye primero el subconjunto permitido a partir de `allowed_tools`.
4. Se intenta resolver `default_tool` buscando coincidencia por nombre o por nombre sin extensión.
5. Si `default_tool` existe dentro del conjunto permitido, se coloca en primera posición.
6. Si `allow_other_tools = false`, el robot solo probará la herramienta por defecto resuelta.
7. Si `allow_other_tools = true`, el robot probará primero la herramienta por defecto y luego el resto de herramientas permitidas.
8. Si `allow_other_tools = false` y la herramienta por defecto no existe o no está permitida, el robot no probará alternativas.

Resumen práctico:
- en ANTHRO mandan `default_tool` y `allow_other_tools`
- en SCARA mandan `allowed_tools`, `default_tool` y `allow_other_tools`

## Casos prácticos

### Caso 1. SCARA deshabilitado

```json
"scara": {
  "enabled": false,
  "root_dir": "OUTPUT/SCARA",
  "default_tool": "tool_A.json",
  "allow_other_tools": false,
  "allowed_tools": ["tool_A.json", "tool_B.json"]
}
```

Resultado real:
- ninguna pieza va a SCARA
- todo el lote se procesa con ANTHRO

### Caso 2. SCARA con una sola herramienta fija

```json
"scara": {
  "enabled": true,
  "root_dir": "OUTPUT/SCARA",
  "default_tool": "tool_A.json",
  "allow_other_tools": false,
  "allowed_tools": ["tool_A.json"]
}
```

Resultado real:
- SCARA solo probará `tool_A.json`
- en este caso el resultado coincide con lo esperado aunque `allowed_tools` no esté implementado, porque la restricción la provoca `allow_other_tools=false`

### Caso 3. SCARA con alternativas limitadas

```json
"scara": {
  "enabled": true,
  "root_dir": "OUTPUT/SCARA",
  "default_tool": "tool_A.json",
  "allow_other_tools": true,
  "allowed_tools": ["tool_A.json", "tool_B.json"]
}
```

Resultado real confirmado por la lógica actual:
- SCARA probará primero `tool_A.json`
- después podrá probar más herramientas detectadas en `TOOLS`
- no debe asegurarse que se limite solo a `tool_B.json`, porque eso no está implementado todavía

### Caso 4. Configuración actual del proyecto

```json
"anthro": {
  "root_dir": "OUTPUT/ANTHRO",
  "default_tool": "tool_H04_pos1.json",
  "allow_other_tools": true
},
"scara": {
  "root_dir": "OUTPUT/SCARA",
  "enabled": true,
  "default_tool": "tool_A.json",
  "allow_other_tools": false,
  "allowed_tools": ["tool_A.json", "tool_B.json"]
}
```

Resultado operativo real:
- ANTHRO empieza por `tool_H04_pos1.json` y puede probar otras herramientas
- SCARA empieza por `tool_A.json`
- como `allow_other_tools` está en `false`, SCARA solo probará `tool_A.json`
- que `tool_B.json` aparezca en `allowed_tools` no cambia nada en esta ejecución concreta

## Materiales conocidos

El bloque `materials.known` define familias de material con:
- alias reconocibles en la metadata
- densidad base en `g/cm3`
- comportamiento ferromagnético

Ejemplo conceptual:

```json
"STEEL": {
  "aliases": ["FE", "S235", "ACERO", "STEEL"],
  "density_g_cm3": 7.85,
  "ferromagnetic": true
}
```

Resolución actual del material:
1. se lee `MATERIAL` desde la metadata de la pieza
2. se compara contra los alias definidos
3. si algún alias está contenido en el texto del material, se aplica esa familia
4. si no hay coincidencia, se usa un perfil genérico con densidad `7.85` y ferromagnetismo desconocido

Esto permite, por ejemplo, que tokens como `FE`, `S235` o `INOX` se resuelvan sin lógica fija quemada fuera del config.

## Creación automática de config.json

Si `config.json` no existe, el sistema intenta crearlo automáticamente.

Esto conviene documentarlo explícitamente porque afecta al arranque inicial del proyecto.

Recomendación documental:
- el archivo generado automáticamente debe considerarse plantilla inicial
- el usuario debe revisarlo antes de ejecutar en una instalación real
- si la plantilla interna no coincide con las rutas o herramientas actuales del proyecto, hay que actualizar el código para evitar configuraciones incoherentes desde el primer arranque

## Recomendaciones de mantenimiento

- mantener sincronizados `README.md`, `docs/configuracion.md` y la plantilla interna `DEFAULT_CONFIG`
- no documentar como implementado nada que todavía no esté aplicado en código
- si `allowed_tools` va a ser una restricción real, conviene implementarlo y después actualizar este documento
- mantener nombres de herramientas con extensión `.json` en la documentación para evitar ambigüedad
- revisar cualquier cambio en filtros SCARA junto con ejemplos reales de piezas aceptadas y rechazadas

