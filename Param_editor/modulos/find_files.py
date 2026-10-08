from pathlib import Path

from .param_core import find_factory_dirs, find_parameter_files


def find_glob(ruta=""):
    p = Path(ruta)
    if not p.exists():
        print(f" >> No encontrada la ruta: {p}")
        return False, [], []
    files = sorted([x.name for x in p.iterdir() if x.is_file()], key=str.casefold)
    dirs = sorted([x.name for x in p.iterdir() if x.is_dir()], key=str.casefold)
    return True, files, dirs


def find_params_files(proces_path=""):
    return [p.name for p in find_parameter_files(Path(proces_path)) if p.parent == Path(proces_path)]


def find_param_dirs(proces_path=""):
    root = Path(proces_path)
    factory = []
    for directory in find_factory_dirs(root):
        subdirs = sorted([p.name for p in directory.iterdir() if p.is_dir()], key=str.casefold)
        factory.append((True, directory.relative_to(root).as_posix(), subdirs))
    return factory, []


if __name__ == "__main__":
    for item in find_param_dirs("para_procesar")[0]:
        print(item)
