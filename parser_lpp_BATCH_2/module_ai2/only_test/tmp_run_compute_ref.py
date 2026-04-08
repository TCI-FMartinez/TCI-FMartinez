import subprocess
from pathlib import Path

cwd = Path(__file__).resolve().parent
cmd = [
    str(cwd / 'compute_ref.exe'),
    str(cwd / 'refPartJson_K563222s40.json'),
    str(cwd / 'tool_A_with_polygons.json'),
    str(cwd / 'material.json'),
    '2',
    '1'
]
print('CMD:', cmd)
res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
print('RETURN:', res.returncode)
print('STDOUT:')
print(res.stdout)
print('STDERR:')
print(res.stderr)
