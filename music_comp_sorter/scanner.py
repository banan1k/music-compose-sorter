# music_sorter/scanner.py
import os
from .db import DB
from .utils import is_supported
from .logger import logger

def scan_directory(root: str, db: DB):
    for dirpath, dirs, files in os.walk(root):
        for fname in files:
            full = os.path.join(dirpath, fname)
            if is_supported(full):
                db.add_file(full, status="pending")
            else:
                # log unsupported
                logger.warning("Unsupported format: %s", full)
                db.add_file(full, status="skipped")