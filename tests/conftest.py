import pytest
import tempfile
from music_comp_sorter.db import DB
from music_comp_sorter.cache import MetaCache
from music_comp_sorter.config import Config

@pytest.fixture
def tmp_db(tmp_path):
    p = tmp_path / "state.db"
    db = DB(str(p))
    yield db
    db.close()

@pytest.fixture
def cfg(tmp_path):
    c = Config()
    c.db_path = str(tmp_path / "state.db")
    c.metadata_cache_dir = str(tmp_path / "cache")
    return c

@pytest.fixture
def cache(tmp_path):
    return MetaCache(str(tmp_path / "cache"))