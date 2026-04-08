
import json
import subprocess
from pathlib import Path


def build_single_ref_json(source_path: Path, index: int = 0) -> Path:
    """Create a single-reference JSON from a list-based refPartJson file."""
    data = json.loads(source_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        if not data:
            raise ValueError(f"No hay referencias en {source_path}")
        single_path = source_path.with_name(source_path.stem + "_single.json")
        single_path.write_text(json.dumps(data[index], indent=2, ensure_ascii=False), encoding="utf-8")
        return single_path
    return source_path


exe_path = Path("compute_ref.exe")
workdir_path = Path(".")
max_compute_time = 2
enhance_opti = 1
ref_source = Path("refPartJson_K563222s40.json")
ref_abs = str(build_single_ref_json(ref_source).resolve())
tool_abs = str(Path("tool_A_with_polygons.json").resolve())
material_abs = str(Path("material.json").resolve())


if not exe_path.exists():
       print(f"No existe '{exe_path.as_posix()}'")

exe_abs = str(exe_path.resolve())

cmd = [exe_abs, ref_abs, tool_abs, material_abs, str(max_compute_time), str(enhance_opti)]

print(f"    Ejecutando: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, cwd=str(workdir_path), capture_output=True, text=True)
    print("    Salida estándar:")
    print(result.stdout)
    print("    Error:")
    print(result.stderr)
except Exception as e:
    print(f"Error al ejecutar el comando: {e}")