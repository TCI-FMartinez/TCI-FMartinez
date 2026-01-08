# SORTING / SORTING PLUS – Documentación técnica y Manual (v0.1)

Autor: F. Martínez  
Proyecto: Herramienta adaptable de ventosas/imanes para robot antropomórfico (Fanuc R‑2000iC‑125L) y SCARA/PLUS.

---

## 0) Resumen ejecutivo
Sistema software que, a partir de una **definición de herramienta** (pads + contorno) y una **rejilla de offsets** (barrido X/Y), genera configuraciones de agarre para piezas cortadas por láser y produce:

- Previsualizaciones **JPG** por variante.
- Un **DXF** por variante con la disposición de pads.
- Un **tools_data.json** con las posiciones resultantes para su consumo por otros módulos.

La herramienta combina **ventosas de vacío** (type=1) y **electroimanes/imanes** (type=2), con capacidad de “acompañar” o no los desplazamientos en X/Y mediante el campo `dependence`.

---

## 1) Alcance y límites del sistema

- **SORTING SCARA (herramienta base)**: piezas aprox. máx **500×500 mm**, mín 150×25 mm (sin taladros), **≤ 6 kg**.  
- **SORTING PLUS (antropomórfico)**: piezas aprox. máx **1500×900 mm**, mín 150×100 mm, **≤ 30 kg** (ejemplo sujeto a estudio específico).  
- El **software optimizador** elegirá automáticamente actuadores activos según material (ferromagnético o no) y verificará capacidad (fuerza útil, distancia al CG, márgenes).

> Nota: Los límites exactos deben confirmarse en el estudio del proyecto (espesor, material, rugosidad, factor de seguridad, etc.).

---

## 2) Estructura de carpetas

```
Proyecto/
├─ HERRAMIENTA01/
│  ├─ tool_M_entrada_ventosas.json   # SOT: pads + contorno
│  └─ posiciones_H01_movil.json      # Rejilla de offsets X/Y (opcionalmente: posiciones.json)
├─ OUTPUT/
│  ├─ JPGS/                          # Previews por variante
│  ├─ tools_data.json                # Resultado (todas las variantes)
│  └─ *_Herramienta_*.dxf            # Un DXF por variante
├─ main.py
├─ json_gen.py
└─ to_dxf.py                         # Exportador DXF (contrato explicado en §7)
```

---

## 3) Requisitos e instalación

- **Python** ≥ 3.10
- Dependencias: `opencv-python`, `numpy` (añadir otras si el `to_dxf` lo requiere)

Instalación rápida:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install opencv-python numpy
```

Compilación opcional (binario):

```bash
pyinstaller --distpath DISTRO --collect-data palettable --onefile -n padstools main.py
```

---

## 4) Modelo de datos (SOT) – JSON de herramienta

### 4.1 Formato de entrada

```json
{
  "pads": [
    {
      "id": 1,
      "posX": -150,
      "posY": 100,
      "type": 2,            
      "force": 1.0,         
      "is_active": false,
      "diameter": 32,       
      "dependence": [1, 1]  
    }
  ],
  "contorno": [
    [-700, 450], [700, 450], [700, -450], [-700, -450]
  ]
}
```

**Convenciones**
- **Unidades**: posiciones y diámetros en **mm**; `force` en **N** (recomendado).
- **type**: `1` = ventosa, `2` = imán (reservar `>2` para extensiones: pinza, etc.).
- **dependence**: `[dx, dy]` ∈ {−1, 0, 1}. `1` acompaña el desplazamiento; `0` queda fijo; `−1` acompaña invertido (simetría).
- `is_active`: estado por defecto; el pipeline actual activa todos salvo que se indique lo contrario.

### 4.2 Rejilla de offsets (barrido)

```json
{
  "posX": [[-380, -280, -180, -140, 0, 140, 380]],
  "posY": [[ 330,  200,  100,    0, -100, -200, -330]]
}
```

> El software usa **el primer array** de `posX` y `posY`. Cada pareja `(x,y)` genera una variante.

### 4.3 Semántica de movimiento

Para cada pad:
```
new_pos.x = posX + x * dependence[0]
new_pos.y = posY + y * dependence[1]
```
- Permite bloques fijos (dependence = `[0,0]`) y bloques que acompañan parcial/totalmente.

---

## 5) Uso (operador)

1. **Preparar entradas**:
   - Verificar `tool_M_entrada_ventosas.json` (pads, contorno, unidades, dependencias).
   - Verificar `posiciones.json` o `posiciones_H01_movil.json` (rejilla de offsets).
2. **Ejecutar**:
   ```bash
   python main.py
   ```
3. **Resultados** en `OUTPUT/`:
   - `JPGS/`: previsualizaciones por variante.
   - `*_Herramienta_*.dxf`: export de cada variante para CAD.
   - `tools_data.json`: consolidado de variantes.
4. **Checklist de revisión en JPG**:
   - Pads dentro de `contorno` (no invadir zonas prohibidas).
   - Distancias mínimas entre pads ≥ diámetro/2 + margen.
   - Ubicación respecto a taladros/ranuras.
   - Coherencia de colores (tipo y estado).

---

## 6) Configuración avanzada (CLI opcional)

Se recomienda parametrizar rutas/ajustes mediante `argparse` en `main.py` (ver §9 – diffs propuestos):

- `--pads HERRAMIENTA01/tool_M_entrada_ventosas.json`
- `--grid HERRAMIENTA01/posiciones_H01_movil.json`
- `--out OUTPUT/`
- `--imgw 1500 --imgh 1125` (lienzo)
- `--previeww 800 --previewh 600`
- `--activate all|ids` (p. ej. `--activate 7,8,12`)

---

## 7) Contrato con el exportador DXF (`to_dxf.py`)

El exportador recibirá **la lista de pads con sus posiciones desplazadas** (recomendado) o la lista de instancias `Pad` **cuyo atributo `new_pos`** ya esté actualizado. Para evitar ambigüedad:

- Opción A (preferida): pasar estructura serializada explícita: `[{id, diameter, position:[x,y], type, force}, ...]` correspondiente a **`new_pos`**.
- Opción B: si se pasan objetos `Pad`, **`to_dxf` debe usar `new_pos`** (no `pos`).

Elementos a exportar (sugeridos):
- Círculos de pads (capa por tipo: VACIO, IMAN, OTROS).
- Etiquetas de ID y diámetro.
- Límite de `contorno` como capa GEOMETRY.
- Origen (0,0) y cajas de referencia, si aplica.

---

## 8) Control de calidad y validaciones

- **Schema**: tipos correctos; `dependence` de longitud 2 y valores en {−1,0,1}; IDs únicos; diámetros > 0.
- **Rangos**: posiciones en mm dentro de la ventana de trabajo (según robot/herramienta).
- **Solapamientos**: (opcional) comprobar superposición de pads (distancia entre centros ≥ (d1+d2)/2 + margen).
- **Cobertura**: con piezas no ferromagnéticas, exigir número mínimo de ventosas activas y radio de vacío efectivo.
- **Performance**: nº pads × nº offsets; documentar límites prácticos.

---

## 9) Incidencias conocidas y **fixes**

1) **Export de posiciones**: en `tools_data.json` se exportaban coordenadas **base** (`pos`) en lugar de las **desplazadas** (`new_pos`).
   - **Solución**: construir `pad_data.position` con `p.new_pos`.
2) **Rutas**: el código apunta a `HERRAMIENTA01/posiciones_H01_movil.json`; si se usa `posiciones.json` en raíz, parametrizar por CLI o ajustar constante.
3) **Tipografía**: función `coloize` vs `colorize`. Unificar a `colorize`.
4) **`json_gen.py`**: esperaba estructura `ventosas[{position, diameter, type}]`. Adaptar a SOT (`pads` → `ventosas` derivado) y mantener `contorno`.
5) **DXF**: verificar que consume `new_pos`. Si no, pasar lista serializada por variante o modificar `to_dxf`.

### 9.1 Parches (diffs sugeridos)

**A) `main.py` – usar `new_pos` al serializar y parametrizar rutas**

```diff
@@
-LIENZO_XY = (1500, 1125)
-FORMATO_SALIDA = (800, 600)
-RUTA_POS_JSON = f"HERRAMIENTA01{sep}posiciones_H01_movil.json"
-RUTA_PADS_JSON = f"HERRAMIENTA01{sep}tool_M_entrada_ventosas.json"
+LIENZO_XY = (1500, 1125)
+FORMATO_SALIDA = (800, 600)
+RUTA_POS_JSON = f"HERRAMIENTA01{sep}posiciones_H01_movil.json"  # override por CLI
+RUTA_PADS_JSON = f"HERRAMIENTA01{sep}tool_M_entrada_ventosas.json"  # override por CLI
@@
-            pad_data = {
-                "id": p.id,
-                "diameter": p.diameter,
-                "position": [p.pos[0], p.pos[1]],
-                "force": p.force,
-                "type": p._type
-            }
+            pad_data = {
+                "id": p.id,
+                "diameter": p.diameter,
+                "position": [p.new_pos[0], p.new_pos[1]],
+                "force": p.force,
+                "type": p._type
+            }
@@
-            generar_dxf(pads, f"OUTPUT{sep}{filename}.dxf")
+            # Recomendación: pasar datos ya desplazados al DXF
+            # generar_dxf(pads, f"OUTPUT{sep}{filename}.dxf")
+            generar_dxf(pads_data, f"OUTPUT{sep}{filename}.dxf")
```

*(Opcional)* añadir `argparse` para rutas y dimensiones:

```diff
@@
-import cv2
+import cv2
+import argparse
@@
-if __name__ == "__main__":
+if __name__ == "__main__":
+    parser = argparse.ArgumentParser()
+    parser.add_argument('--pads', default=RUTA_PADS_JSON)
+    parser.add_argument('--grid', default=RUTA_POS_JSON)
+    parser.add_argument('--out',  default='OUTPUT')
+    parser.add_argument('--imgw', type=int, default=LIENZO_XY[0])
+    parser.add_argument('--imgh', type=int, default=LIENZO_XY[1])
+    parser.add_argument('--previeww', type=int, default=FORMATO_SALIDA[0])
+    parser.add_argument('--previewh', type=int, default=FORMATO_SALIDA[1])
+    args = parser.parse_args()
+
+    RUTA_PADS_JSON = args.pads
+    RUTA_POS_JSON  = args.grid
+    LIENZO_XY      = (args.imgw, args.imgh)
+    FORMATO_SALIDA = (args.previeww, args.previewh)
```

**B) `json_gen.py` – aceptar SOT (`pads`) y unificar `colorize`**

```diff
@@
-def colorize(_type:int=0)->tuple:
+def colorize(_type:int=0)->tuple:
@@
-with open(f"HERRAMIENTA01{sep}tool_M_entrada_ventosas.json") as v:
-    herramienta_ = json.load(v)
-
-ventosas = herramienta_["ventosas"]
-contorno = herramienta_["contorno"]
+with open(f"HERRAMIENTA01{sep}tool_M_entrada_ventosas.json") as v:
+    herramienta_ = json.load(v)
+
+# Adaptar de SOT (pads → ventosas con {position, diameter, type})
+pads = herramienta_["pads"]
+ventosas = [
+    {
+        "position": [p["posX"], p["posY"]],
+        "diameter": p["diameter"],
+        "type": p["type"]
+    }
+    for p in pads
+]
+contorno = herramienta_["contorno"]
```

---

## 10) Manual del **Operador**

1. Cargar `tool_M_entrada_ventosas.json` y `posiciones.json` validados.
2. Ejecutar el generador; esperar `OUTPUT/`.
3. Verificar visualmente una muestra de JPGs (esquinas, centro, offsets extremos).
4. Enviar los DXF aprobados a ingeniería/robot para programación.
5. Mantener trazabilidad con `tools_data.json` (etiquetas de variante, timestamp).

### 10.1 Mensajes/errores frecuentes
- «Error al cargar PADS desde json» → ruta incorrecta o JSON inválido.
- «Error al decodificar JSON en posiciones» → sintaxis o arrays anidados mal formados.
- Salida vacía → rejilla vacía o pads inactivos.

---

## 11) Manual **Técnico/Integrador**

### 11.1 Clases y funciones clave
- `Pad`: `id, pos, _type, force, is_active, diameter, dependence, new_pos`.
- `Pad.move((x,y))`: aplica dependencias para generar `new_pos`.
- `Lienzo`, `invertY`, `colorize`.
- Cargadores JSON: `cargar_pads_desde_json`, `cargar_posiciones_desde_json`.

### 11.2 Extensiones
- **Nuevos tipos** (`type>2`): añadir color en `colorize` y capas DXF.
- **Reglas de activación**: filtrar por material/espesor/área; activar imanes sólo para ferromagnéticos.
- **Optimización**: introducir heurísticas (Voronoi, centroides, momento máximo, distancias mínimas).
- **Validaciones geométricas**: exclusión por agujeros, rebordes, nervios.

### 11.3 Integración con G-CODE / CAD
- Lectura de trayectorias, unión de segmentos, detección de orientación por matching.
- Uso de `contorno` y zonas prohibidas para determinar puntos válidos de agarre.

### 11.4 Seguridad y márgenes
- Factor de seguridad por tipo de actuador (coef. fricción al vacío, pérdidas por rugosidad, desmagnetización con temperatura, etc.).
- Velocidad y aceleraciones del robot (no superar fuerza de sujeción efectiva).
- Zona de exclusión respecto a bordes cortantes.

---

## 12) Plantillas de ejemplo

### 12.1 `tool_M_entrada_ventosas.json`

```json
{
  "pads": [
    {"id": 1, "posX": -150, "posY": 100, "type": 2, "force": 1.0, "is_active": false, "diameter": 32, "dependence": [1, 1]},
    {"id": 2, "posX": -100, "posY": 100, "type": 1, "force": 10.0, "is_active": false, "diameter": 36, "dependence": [1, 1]}
  ],
  "contorno": [[-700, 450], [700, 450], [700, -450], [-700, -450]]
}
```

### 12.2 `posiciones.json`

```json
{
  "posX": [[-380, -180, 0, 180, 380]],
  "posY": [[ 330,  100, 0, -100, -330]]
}
```

---

## 13) Roadmap
- CLI completa (`argparse`) y presets por proyecto.
- Validación de solapes y zonas prohibidas.
- Generación de informe por variante (CSV/JSON) con métricas (cobertura, distancias mínimas, equilibrio).
- Integración con selector automático de tool (SCARA vs PLUS) según peso/dimensión.
- Test unitarios de loader, dependencia y exportador.

---

## 14) Aceptación (DoD)
- Dada una herramienta válida y una rejilla no vacía, el sistema genera JPG + DXF + `tools_data.json`.
- `tools_data.json` refleja siempre **las posiciones desplazadas** (coincide con la vista JPG y el DXF).
- Sin errores de schema; logs claros; rutas parametrizables.

---

**Fin del documento v0.1**

