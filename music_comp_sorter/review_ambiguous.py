# music_comp_sorter/review_ambiguous.py
import json
from .db import DB
from .logger import logger

def review_loop(db: DB):
    cur = db.conn.cursor()
    cur.execute("SELECT id, file_path, tried_options_json FROM conflicts WHERE chosen_option_json IS NULL")
    rows = cur.fetchall()
    for rid, file_path, tried in rows:
        options = json.loads(tried)
        print(f"File: {file_path}")
        for i, opt in enumerate(options):
            print(f"{i+1}. {opt.get('title')} - {opt.get('artist')} ({opt.get('release_title')})")
        choice = input("Choose (number) or skip (Enter): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            chosen = options[int(choice)-1]
            db.conn.execute("UPDATE conflicts SET chosen_option_json=?, reviewed_ts=strftime('%s','now') WHERE id=?", (json.dumps(chosen), rid))
            db.conn.commit()
            print("Saved.")
        else:
            print("Skipped.")