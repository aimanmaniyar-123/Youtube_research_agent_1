import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except:
    pass

def setup_root_logger(level="INFO"):
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(level)

    fh = logging.FileHandler(LOG_DIR / f"log_{datetime.now().date()}.txt", encoding="utf-8")
    ch = logging.StreamHandler(sys.stdout)

    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    root.addHandler(fh)
    root.addHandler(ch)

def get_logger(name: str, level="INFO"):
    setup_root_logger(level)
    return logging.getLogger(name)
