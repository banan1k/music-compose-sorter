# music_sorter/identifier.py
import time
import threading
from typing import List, Dict, Optional
from .logger import logger
from .cache import MetaCache
from .config import Config
from .utils import normalize_string
import musicbrainzngs

# Rate limiter for MusicBrainz
class RateLimiter:
    def __init__(self, rate_per_sec=1.0):
        self.lock = threading.Lock()
        self.rate = rate_per_sec
        self.last = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            delta = 1.0 / self.rate
            next_allowed = self.last + delta
            if now < next_allowed:
                time.sleep(next_allowed - now)
            self.last = time.time()

class Identifier:
    def __init__(self, cfg: Config, cache: MetaCache):
        self.cfg = cfg
        self.cache = cache
        musicbrainzngs.set_useragent(cfg.user_agent, "1.0")
        self.rl = RateLimiter(cfg.musicbrainz_rate_limit)

    def search_by_tags(self, title: str, artist: str) -> List[Dict]:
        self.rl.wait()
        title_s = normalize_string(title)
        artist_s = normalize_string(artist)
        try:
            res = musicbrainzngs.search_recordings(recording=title_s, artist=artist_s, limit=5)
            return res.get("recording-list", [])
        except Exception as e:
            logger.exception("MusicBrainz search failed: %s", e)
            return []

    def get_release_by_mbid(self, mbid: str) -> Optional[Dict]:
        if self.cache.has(mbid):
            return self.cache.get(mbid)
        self.rl.wait()
        try:
            r = musicbrainzngs.get_release_by_id(mbid, includes=["artists","recordings","release-groups"])
            self.cache.set(mbid, r)
            return r
        except Exception as e:
            logger.exception("MusicBrainz get_release_by_id failed: %s", e)
            return None

    # fingerprinting (optional)
    def fingerprint_identify(self, file_path: str, acoustid_key: str):
        try:
            import acoustid
            self.rl.wait()
            result = acoustid.match(acoustid_key, file_path)
            # result may contain multiple matches; return list of possible MBIDs
            mbids = []
            for score, rid, title, artist in result:
                if rid:
                    mbids.append({"mbid": rid, "score": score, "title": title, "artist": artist})
            return mbids
        except Exception as e:
            logger.exception("Fingerprint ident failed: %s", e)
            return []