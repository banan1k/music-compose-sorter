# music_comp_sorter/processor.py
import concurrent.futures
import threading
import time
import json
import os
import requests
from typing import Optional

from .db import DB
from .cache import MetaCache
from .config import Config
from .logger import logger
from .identifier import Identifier
from .tag_writer import backup_original, write_tags
from .organizer import move_file

# helper: input with timeout (works on Windows and Unix using thread)
def input_with_timeout(prompt: str, timeout: float) -> Optional[str]:
    result = {"value": None}
    def worker():
        try:
            result["value"] = input(prompt)
        except Exception:
            result["value"] = None
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None
    return result["value"]

class Processor:
    def __init__(self, cfg: Config, db: DB, cache: MetaCache, identifier: Identifier):
        self.cfg = cfg
        self.db = db
        self.cache = cache
        self.identifier = identifier
        self.network_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, cfg.network_threads))
        self.local_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, cfg.file_threads))

    def _download_cover(self, release_mbid: str) -> Optional[str]:
        """Download first cover from CoverArtArchive for given release MBID and save to cache; return path or None"""
        try:
            # use identifier.get_release_by_mbid() to ensure cached release info
            # musicbrainzngs provides get_image_list, but we can form CoverArtArchive URL:
            # Cover: https://coverartarchive.org/release/{mbid}/front-250.jpg (thumbnails) or /front
            url = f"https://coverartarchive.org/release/{release_mbid}/front"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                # ensure cache dir exists
                os.makedirs(self.cfg.metadata_cache_dir, exist_ok=True)
                fn = os.path.join(self.cfg.metadata_cache_dir, f"{release_mbid}.cover.jpg")
                with open(fn, "wb") as f:
                    f.write(resp.content)
                logger.info("Downloaded cover for %s -> %s", release_mbid, fn)
                return fn
            else:
                logger.info("CoverArtArchive returned %s for %s", resp.status_code, release_mbid)
                return None
        except Exception as e:
            logger.warning("Failed to download cover for %s: %s", release_mbid, e)
            return None

    def _export_cover_by_mode(self, cover_path: str, artist: str, album: str) -> None:
        mode = getattr(self.cfg, "cover_export_mode", "global")
        dest_root = getattr(self.cfg, "library_output_dir", None) or os.path.expanduser("~")
        # global: ~/.local/share/music_comp_sorter/covers/album - artist.jpg
        if mode == "global":
            outdir = os.path.join(os.path.expanduser("~/.local/share/music_comp_sorter"), "covers")
            os.makedirs(outdir, exist_ok=True)
            safe_name = f"{album} - {artist}".replace(os.sep, "_")
            dst = os.path.join(outdir, f"{safe_name}.jpg")
        elif mode == "artist":
            outdir = os.path.join(dest_root, artist, "covers")
            os.makedirs(outdir, exist_ok=True)
            dst = os.path.join(outdir, f"{album}.jpg")
        elif mode == "album":
            outdir = os.path.join(dest_root, artist, album)
            os.makedirs(outdir, exist_ok=True)
            dst = os.path.join(outdir, "cover.jpg")
        else:
            # fallback to global
            outdir = os.path.join(os.path.expanduser("~/.local/share/music_comp_sorter"), "covers")
            os.makedirs(outdir, exist_ok=True)
            safe_name = f"{album} - {artist}".replace(os.sep, "_")
            dst = os.path.join(outdir, f"{safe_name}.jpg")

        try:
            if os.path.abspath(cover_path) != os.path.abspath(dst):
                # copy file
                from shutil import copy2
                copy2(cover_path, dst)
            logger.info("Exported cover to %s (mode=%s)", dst, mode)
        except Exception as e:
            logger.warning("Failed to export cover %s -> %s: %s", cover_path, dst, e)

    def _choose_candidate_interactive(self, file_path: str, candidates: list) -> Optional[dict]:
        # if only one candidate -> choose it
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        # interactive prompt with 30s timeout
        print(f"Ambiguous matches for {file_path}:")
        for i, c in enumerate(candidates, start=1):
            title = c.get("title") or c.get("recording", {}).get("title")
            artist = None
            if "artist-credit" in c:
                artist = " & ".join(a.get("artist", {}).get("name", "") for a in c["artist-credit"])
            else:
                artist = c.get("artist") or c.get("artist-name") or ""
            release_title = ""
            if "release-list" in c and c["release-list"]:
                release_title = c["release-list"][0].get("title", "")
            print(f"{i}. {title} — {artist} ({release_title})")
        ans = input_with_timeout("Choose number (Enter to skip, auto-pick after 30s): ", 30.0)
        if ans and ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
        # auto pick first (heuristic)
        logger.info("No user choice for %s, auto-picking first candidate", file_path)
        # insert conflict record
        try:
            self.db.insert_conflict(file_path, json.dumps(candidates), auto_chosen=True, chosen_option_json=json.dumps(candidates[0]))
        except Exception:
            logger.exception("Failed to insert conflict")
        return candidates[0]

    def _process_one(self, file_path: str, dry_run: bool = False, duplicate_mode: str = "keep_both"):
        # Steps:
        # 1. update DB status
        try:
            self.db.update_file(file_path, status="processing", last_processed_timestamp=int(time.time()))
        except Exception:
            logger.exception("db update failed for %s", file_path)

        # 2. read current tags (using mutagen)
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(file_path, easy=True)
        except Exception as e:
            logger.warning("Mutagen open failed for %s: %s", file_path, e)
            self.db.update_file(file_path, status="error", error_message=str(e))
            return

        existing_title = None
        existing_artist = None
        existing_album = None
        if audio:
            existing_title = audio.get("title", [None])[0]
            existing_artist = audio.get("artist", [None])[0]
            existing_album = audio.get("album", [None])[0]

        # 3. attempt identification by tags
        candidates = []
        if existing_title and existing_artist:
            candidates = self.identifier.search_by_tags(existing_title, existing_artist)

        # 4. if no candidate and fingerprint enabled -> fingerprint
        if not candidates and self.cfg.fingerprint_enabled and self.cfg.acoustid_api_key:
            try:
                mbids = self.identifier.fingerprint_identify(file_path, self.cfg.acoustid_api_key)
                # mbids: list of dicts {'mbid':..., 'score':...}
                if mbids:
                    # convert to candidate objects by fetching recording/release details
                    for m in mbids:
                        if m.get("mbid"):
                            r = self.identifier.get_release_by_mbid(m["mbid"])
                            if r:
                                candidates.append(r.get("release", r))
            except Exception as e:
                logger.warning("Fingerprint step failed for %s: %s", file_path, e)

        chosen = self._choose_candidate_interactive(file_path, candidates)

        if not chosen:
            # no change
            logger.info("No candidate found for %s — leaving as is", file_path)
            self.db.update_file(file_path, status="done", error_message=None)
            return

        # extract metadata fields
        # chosen could be MusicBrainz recording or release structure
        mbid = chosen.get("id") or chosen.get("mbid")
        # title/artist/album heuristics
        title = chosen.get("title") or existing_title
        # artist extraction
        artist = None
        if "artist-credit" in chosen:
            artist = " & ".join(ac.get("artist", {}).get("name", "") for ac in chosen["artist-credit"])
        elif chosen.get("artist-credit-phrase"):
            artist = chosen.get("artist-credit-phrase")
        elif existing_artist:
            artist = existing_artist

        album = None
        # if release-list exists
        if "release-list" in chosen and chosen["release-list"]:
            album = chosen["release-list"][0].get("title")
            release_mbid = chosen["release-list"][0].get("id")
        else:
            album = existing_album
            release_mbid = None

        # 5. backup original
        try:
            backup_original(file_path, self.cfg.backup_dir)
        except Exception:
            logger.exception("Backup original failed for %s", file_path)

        # 6. optionally download cover and export
        cover_path = None
        if self.cfg.export_covers and release_mbid:
            # try get cached cover
            cover_cached = os.path.join(self.cfg.metadata_cache_dir, f"{release_mbid}.cover.jpg")
            if os.path.exists(cover_cached):
                cover_path = cover_cached
            else:
                # schedule download
                cover_path = self._download_cover(release_mbid)
            if cover_path:
                # export according to mode
                self._export_cover_by_mode(cover_path, artist or "Unknown", album or "Unknown")

        # 7. write tags (respecting existing tags: update only missing or different)
        metadata = {}
        if title and (existing_title != title):
            metadata["title"] = title
        if artist and (existing_artist != artist):
            metadata["artist"] = artist
        if album and (existing_album != album):
            metadata["album"] = album
        if cover_path:
            metadata["cover_path"] = cover_path

        if not metadata:
            logger.info("No tag changes for %s", file_path)
            self.db.update_file(file_path, status="done", mbid=mbid, fingerprint=None, last_processed_timestamp=int(time.time()))
            return

        ok = write_tags(file_path, metadata, dry_run=dry_run)
        if ok:
            # move file to library_output_dir if set
            dest_root = getattr(self.cfg, "library_output_dir", None)
            if dest_root:
                try:
                    new_path = move_file(file_path, os.path.expanduser(dest_root), artist or "Unknown Artist", album or "Unknown Album", keep_both=(duplicate_mode == "keep_both"))
                    file_path = new_path
                except Exception:
                    logger.exception("Failed to move file %s", file_path)
            self.db.update_file(file_path, status="done", mbid=mbid, last_processed_timestamp=int(time.time()))
        else:
            self.db.update_file(file_path, status="error", error_message="tag write failed")

    def process_pending(self, limit: Optional[int] = None, dry_run: bool = False, duplicate_mode: str = "keep_both"):
        files = self.db.get_pending_files(limit=limit)
        logger.info("Processing %d files (dry_run=%s)", len(files), dry_run)
        # process serially via threadpool for better responsiveness (local executor)
        futures = []
        for f in files:
            futures.append(self.local_executor.submit(self._process_one, f, dry_run, duplicate_mode))
        # wait for completion
        for fut in concurrent.futures.as_completed(futures):
            try:
                fut.result()
            except Exception:
                logger.exception("Processing task raised exception")

    def close(self):
        try:
            self.network_executor.shutdown(wait=False)
        except Exception:
            pass
        try:
            self.local_executor.shutdown(wait=False)
        except Exception:
            pass