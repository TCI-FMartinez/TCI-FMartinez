Param_editor v2.0

HECHO:
- Resueltos conflictos de merge del flujo activo.
- Busqueda recursiva de carpetas factory dentro de para_procesar.
- Un Excel independiente por factory; eliminado el acumulado global_table.
- Round-trip seguro con fuente original embebida en hoja oculta _SOURCE.
- Conservacion byte a byte si no hay ediciones.
- Conservacion del R/S real, orden, decimales, comentarios y lineas no reconocidas.
- Soporte de parametros repetidos mediante Nxxx#2, Nxxx#3, etc.
- Deteccion de colisiones antes de escribir ningun LPARAM.
- Validacion de valores modificados.
- Proteccion de rutas/campos de control.
- Metadata cargada desde todas las hojas, incluida FOCALES.
- Specs PyInstaller incluyen methadata.xlsx.
- Tests automatizados y smoke test con los datos reales de Param_editor.

PENDIENTE FUERA DE ESTE ENTORNO:
- Compilar y firmar los ejecutables Windows PARAMtoEXCEL.exe y EXCELtoPARAM.exe en Windows.
