from music_comp_sorter.scanner import scan_directory
import os

def test_scan_adds_supported(tmp_path, tmp_path_factory, tmp_db):
    root = tmp_path / "music"
    root.mkdir()
    f1 = root / "song.mp3"
    f1.write_text("dummy")
    f2 = root / "text.txt"
    f2.write_text("no")
    scan_directory(str(root), tmp_db)
    rows = tmp_db.conn.execute("SELECT path, status FROM files").fetchall()
    assert any("song.mp3" in r[0] and r[1] == "pending" for r in rows)
    assert any("text.txt" in r[0] and r[1] == "skipped" for r in rows)