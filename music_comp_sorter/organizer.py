# music_comp_sorter/organizer.py
import os
import shutil
from .logger import logger

def target_path(root_dest: str, artist: str, album: str, fname: str) -> str:
    safe_artist = "".join(c for c in artist if c not in r'\/:*?"<>|')
    safe_album = "".join(c for c in album if c not in r'\/:*?"<>|')
    newdir = os.path.join(root_dest, safe_artist, safe_album)
    os.makedirs(newdir, exist_ok=True)
    return os.path.join(newdir, fname)

def move_file(src: str, dest_root: str, artist: str, album: str, keep_both=True):
    dest = target_path(dest_root, artist, album, os.path.basename(src))
    if os.path.exists(dest):
        if keep_both:
            base, ext = os.path.splitext(dest)
            i = 1
            while os.path.exists(f"{base} ({i}){ext}"):
                i += 1
            dest = f"{base} ({i}){ext}"
        else:
            os.replace(src, dest)
            return dest
    shutil.move(src, dest)
    return dest