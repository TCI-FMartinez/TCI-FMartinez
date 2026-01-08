# Protocolo de ensayo: <NOMBRE>

ID: TP-YYYYMMDD-XX
Fecha: YYYY-MM-DD
Responsable: <nombre>
Versión: 0.1

Objetivo
- Qué quieres demostrar/medir (1-2 líneas)
- Métrica principal (ej: pico a pico, RMS, FRF, amplitud en Hz objetivo)

Alcance
- Qué incluye y qué no incluye (ej: solo eje X, solo puente, solo condición A)

Setup
Máquina
- Modelo:
- Estado (mantenimiento, holguras conocidas):
- Parámetros relevantes:

Montaje
- Descripción:
- Fotos: (link o ruta en hardware/photos/)
- Esquema: (ruta)

Instrumentación
- Sensores (modelo, rango, sensibilidad):
- Ubicación exacta:
- Orientación:
- Cableado / acondicionamiento:
- Frecuencia de muestreo:
- Filtro (si aplica):
- Calibración: (ruta en data/metadata/calibration-certificates/)

Condiciones del ensayo
- Condición A:
  - rpm:
  - avance:
  - profundidad/pasada:
  - herramienta/material:
- Condición B:
  - ...

Procedimiento paso a paso
1) Checklist previo
2) Arranque y warm-up (si aplica)
3) Captura baseline
4) Captura con TMD (o cambio)
5) Repeticiones (n):
6) Parada segura y guardado

Checklist
Antes
- [ ] Sensores firmes
- [ ] Canales correctos
- [ ] Ganancias correctas
- [ ] Calibración vigente
- [ ] Plan de seguridad / EPI

Durante
- [ ] No saturación
- [ ] Ruido/cable suelto
- [ ] Repetición consistente

Después
- [ ] Copia de datos
- [ ] Notas de incidencias
- [ ] Fotos finales

Datos y organización
Carpetas
- data/raw/YYYY-MM-DD/<ensayo>/
- data/interim/YYYY-MM-DD/<ensayo>/
- data/processed/YYYY-MM-DD/<ensayo>/

Nombres de archivo (ejemplos)
- 2026-01-08_baseline_run01.tdms
- 2026-01-08_tmd-v1_run01.tdms
- 2026-01-08_notes.md

Criterios de aceptación (pass/fail)
- Métrica 1: umbral:
- Métrica 2: umbral:
- Repetibilidad: variación máxima permitida:

Riesgos y mitigaciones
- Riesgo:
- Mitigación:
- Trigger para abortar:

Salida esperada
- Figuras mínimas:
- Tabla mínima:
- Decisión esperada (go/no-go):
