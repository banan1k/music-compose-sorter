# music_sorter/utils.py
import re
from typing import Tuple
import unicodedata

NORMALIZE_RE = re.compile(r'\b(official video|lyrics?|remaster(ed)?|radio edit|album version|extended|feat\.?|ft\.?)\b', re.I)

def normalize_string(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = s.strip()
    s = NORMALIZE_RE.sub("", s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip()

def is_supported(path: str) -> bool:
    path = path.lower()
    return path.endswith(('.mp3', '.flac', '.m4a', '.ogg'))