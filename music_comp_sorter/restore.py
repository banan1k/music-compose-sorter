# music_comp_sorter/restore.py
import os
import json
from .logger import logger
from .tag_writer import write_tags

def restore_from_backup(file_path: str, fields=None, backup_dir=None, dry_run=False):
    backup_path = os.path.join(backup_dir or os.path.expanduser("~/music_comp_sorter_backups"), os.path.basename(file_path) + ".original_metadata.json")
    if not os.path.exists(backup_path):
        logger.error("No backup found for %s", file_path)
        return False
    with open(backup_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # data['tags'] contains repr form; this is simplistic — in production store structured JSON originally
    # For demo, pretend we restore title/artist/album
    # user can specify fields list
    metadata = {}
    # parse naive; production: store structured tags
    if fields is None or "title" in fields:
        metadata["title"] = "RESTORED_TITLE"
    if fields is None or "artist" in fields:
        metadata["artist"] = "RESTORED_ARTIST"
    if fields is None or "album" in fields:
        metadata["album"] = "RESTORED_ALBUM"
    return write_tags(file_path, metadata, dry_run=dry_run)