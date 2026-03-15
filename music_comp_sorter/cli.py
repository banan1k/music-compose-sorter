# music_comp_sorter/cli.py
import click
import os
from .config import load_config
from music_comp_sorter.db import DB
from .scanner import scan_directory
from .logger import logger
from .cache import MetaCache
from .identifier import Identifier
from .restore import restore_from_backup
from .processor import Processor

@click.group()
@click.version_option("1.0")
@click.option("--config", "config_path", default=None, help="Path to config toml")
@click.pass_context
def cli(ctx, config_path):
    ctx.ensure_object(dict)
    cfg = load_config(config_path)
    ctx.obj["cfg"] = cfg
    ctx.obj["db"] = DB(cfg.db_path)
    ctx.obj["cache"] = MetaCache(cfg.metadata_cache_dir)
    ctx.obj["identifier"] = Identifier(cfg, ctx.obj["cache"])

@cli.command()
@click.argument("root", type=click.Path(exists=True))
@click.pass_context
def scan(ctx, root):
    db: DB = ctx.obj["db"]
    scan_directory(root, db)
    click.echo("Scan complete.")

@cli.command()
@click.option("--dry-run", is_flag=True, default=False, help="Do not write tags or move files")
@click.option("--limit", type=int, default=None, help="Limit number of files to process")
@click.option("--mode", "duplicate_mode", type=click.Choice(["keep_both", "replace_singles_with_album_versions", "replace_album_with_single_versions"]), default=None, help="Duplicate handling mode")
@click.pass_context
def process(ctx, dry_run, limit, duplicate_mode):
    """Process pending files (identify, write tags, move files)."""
    cfg = ctx.obj["cfg"]
    db = ctx.obj["db"]
    cache = ctx.obj["cache"]
    identifier = ctx.obj["identifier"]
    if duplicate_mode is None:
        duplicate_mode = cfg.duplicate_mode
    proc = Processor(cfg, db, cache, identifier)
    try:
        proc.process_pending(limit=limit, dry_run=dry_run, duplicate_mode=duplicate_mode)
        click.echo("Processing complete.")
    finally:
        proc.close()

@cli.command()
@click.pass_context
def status(ctx):
    """Print counts of files in DB grouped by status."""
    db = ctx.obj["db"]
    cur = db.conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM files GROUP BY status")
    rows = cur.fetchall()
    if not rows:
        click.echo("No files recorded. Run scan first.")
        return
    for status, count in rows:
        click.echo(f"{status}: {count}")

@cli.command()
@click.pass_context
def resume(ctx):
    """Alias for process (resume pending)."""
    ctx.invoke(process)

@cli.command()
@click.option("--dry-run", is_flag=True)
@click.pass_context
def restore(ctx, dry_run):
    file_path = click.prompt("Path to file to restore", type=click.Path())
    ok = restore_from_backup(file_path, backup_dir=ctx.obj["cfg"].backup_dir, dry_run=dry_run)
    if ok:
        click.echo("Restore done.")
    else:
        click.echo("Restore failed.")

if __name__ == "__main__":
    cli()