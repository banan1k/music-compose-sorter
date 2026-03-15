# music_sorter/cache.py
import os
import json
import time
from .logger import logger

class MetaCache:
    def __init__(self, base_dir):
        self.base = base_dir
        os.makedirs(self.base, exist_ok=True)

    def path_for(self, mbid: str) -> str:
        return os.path.join(self.base, f"{mbid}.json")

    def has(self, mbid: str) -> bool:
        return os.path.exists(self.path_for(mbid))

    def get(self, mbid: str):
        p = self.path_for(mbid)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def set(self, mbid: str, data: dict):
        p = self.path_for(mbid)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"fetched_ts": int(time.time()), "data": data}, f, ensure_ascii=False, indent=2)