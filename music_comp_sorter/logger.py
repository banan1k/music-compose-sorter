# music_comp_sorter/logger.py
import logging
import os

LOG_DIR = os.path.expanduser("~/.local/share/music_sorter/logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("music_sorter")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

fh = logging.FileHandler(os.path.join(LOG_DIR, "errors.log"))
fh.setLevel(logging.WARNING)
fh.setFormatter(fmt)
logger.addHandler(fh)

ch = logging.StreamHandler()
ch.setFormatter(fmt)
logger.addHandler(ch)