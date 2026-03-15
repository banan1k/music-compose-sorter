# music_comp_sorter/tag_writer.py
from mutagen import File
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, APIC, error as ID3Error
from mutagen.flac import Picture, FLAC
from .logger import logger
import json
import os
import time

def backup_original(file_path: str, dest_dir: str):
    os.makedirs(dest_dir, exist_ok=True)
    audio = File(file_path, easy=False)
    data = {}
    if audio:
        for k in audio.tags.keys() if audio.tags else []:
            try:
                data[k] = audio.tags.getall(k)
            except Exception:
                data[k] = str(audio.tags.get(k))
    backup_path = os.path.join(dest_dir, os.path.basename(file_path) + ".original_metadata.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump({"path": file_path, "timestamp": int(time.time()), "tags": repr(data)}, f, ensure_ascii=False, indent=2)
    return backup_path

def write_tags(file_path: str, metadata: dict, dry_run: bool = False):
    """
    metadata: {'title':..., 'artist':..., 'album':..., 'tracknumber': '1/10', 'cover_path': '/...'}
    """
    if dry_run:
        return True
    try:
        audio = File(file_path, easy=False)
        if audio is None:
            logger.warning("mutagen could not open file %s", file_path)
            return False

        # mp3 (ID3)
        if file_path.lower().endswith('.mp3'):
            try:
                tags = ID3(file_path)
            except ID3Error:
                tags = ID3()
            if metadata.get("title"):
                tags.add(TIT2(encoding=3, text=metadata["title"]))
            if metadata.get("artist"):
                tags.add(TPE1(encoding=3, text=metadata["artist"]))
            if metadata.get("album"):
                tags.add(TALB(encoding=3, text=metadata["album"]))
            if metadata.get("tracknumber"):
                tags.add(TRCK(encoding=3, text=str(metadata["tracknumber"])))
            if metadata.get("cover_path"):
                with open(metadata["cover_path"], "rb") as img:
                    tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img.read()))
            tags.save(file_path)
        elif file_path.lower().endswith('.flac'):
            fl = FLAC(file_path)
            if metadata.get("title"):
                fl["title"] = metadata["title"]
            if metadata.get("artist"):
                fl["artist"] = metadata["artist"]
            if metadata.get("album"):
                fl["album"] = metadata["album"]
            if metadata.get("tracknumber"):
                fl["tracknumber"] = str(metadata["tracknumber"])
            if metadata.get("cover_path"):
                pic = Picture()
                with open(metadata["cover_path"], "rb") as img:
                    pic.data = img.read()
                pic.type = 3
                pic.mime = "image/jpeg"
                fl.clear_pictures()
                fl.add_picture(pic)
            fl.save()
        else:
            # for m4a/ogg use mutagen.File generic API
            if metadata.get("title"):
                audio["title"] = metadata["title"]
            if metadata.get("artist"):
                audio["artist"] = metadata["artist"]
            if metadata.get("album"):
                audio["album"] = metadata["album"]
            if metadata.get("tracknumber"):
                audio["tracknumber"] = str(metadata["tracknumber"])
            if metadata.get("cover_path"):
                # mutagen for mp4 tags: add 'covr' atom - it's a bit more work; skip here for brevity
                pass
            audio.save()
        return True
    except Exception as e:
        logger.exception("Failed to write tags for %s: %s", file_path, e)
        return False