# Checklist de release / prototipo

Versión: vX.Y.Z
Fecha: YYYY-MM-DD
Owner: <nombre>

Documentación
- [ ] Requisitos actualizados (docs/01_requirements/)
- [ ] Decisiones registradas (docs/00_admin/decisions/)
- [ ] Informe final de validación (docs/06_release/ o TR-...)
- [ ] Manual instalación (si aplica)
- [ ] Manual mantenimiento (si aplica)

Hardware
- [ ] BOM congelada (hardware/bom/)
- [ ] Planos 2D exportados y versionados (hardware/drawings/)
- [ ] CAD subido (hardware/cad/) y LFS ok
- [ ] Fotos del montaje final (hardware/photos/)
- [ ] Pares de apriete / tolerancias documentadas (hardware/manufacturing/)

Ensayos
- [ ] Protocolo(s) vinculados (TP-...)
- [ ] Datos raw guardados y etiquetados (data/raw/...)
- [ ] Resultados/figuras exportadas (results/figures/, results/exports/)
- [ ] Comparación contra baseline incluida
- [ ] Criterios pass/fail cumplidos

Software (si aplica)
- [ ] Scripts reproducibles (scripts/)
- [ ] Entorno/dependencias documentadas
- [ ] Tests básicos pasan

Tag y entrega
- [ ] Tag git creado (vX.Y.Z)
- [ ] Release notes (CHANGELOG)
- [ ] Zip/PDF exportado en results/exports/
