from pathlib import Path
from datetime import datetime


def LogThis(mess_code: str = "00", is_input: str = "", mess_str: str = "", value: str = ""):
    now = datetime.now()
    log_dir = Path.cwd() / "LOG"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{now:%Y-%m-%d}.log"
    line = f"{now:%Y-%m-%d %H:%M:%S} {is_input} [{mess_code}] = {mess_str} {value}\n"
    existed = log_file.exists()
    with log_file.open("a", encoding="utf-8", newline="") as f:
        f.write(line)
    return existed
