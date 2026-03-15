# music_sorter/config.py
from dataclasses import dataclass, field
import os
import tomllib

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/music_sorter/config.toml")

@dataclass
class Config:
    db_path: str = os.path.expanduser("~/.local/share/music_sorter/state.db")
    metadata_cache_dir: str = os.path.expanduser("~/.local/share/music_sorter/metadata_cache")
    backup_dir: str = os.path.expanduser("~/music_sorter_backups")
    user_agent: str = "music-sorter/1.0 (contact: none)"
    musicbrainz_rate_limit: float = 1.0
    network_threads: int = 4
    file_threads: int = 4
    dry_run: bool = False
    debug: bool = False
    acoustid_api_key: str | None = None
    export_covers: bool = False
    duplicate_mode: str = "keep_both"  # options: keep_both, replace_singles_with_album_versions, replace_album_with_single_versions
    fingerprint_enabled: bool = True

def load_config(path: str | None = None) -> Config:
    p = path or DEFAULT_CONFIG_PATH
    cfg = Config()
    if os.path.exists(p):
        with open(p, "rb") as f:
            raw = tomllib.load(f)
        for k, v in raw.get("music_sorter", {}).items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    return cfg