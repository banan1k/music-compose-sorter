from music_comp_sorter.utils import normalize_string
def test_normalize():
    s = "Song Title (Official Video) - Artist"
    assert "Official Video" not in normalize_string(s)