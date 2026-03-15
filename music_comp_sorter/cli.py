# music_comp_sorter/cli.py
import click
import os
from .config import load_config
from .db import DB
from .scanner import scan_directory
from .logger import logger
from .cache import MetaCache
from .identifier import Identifier
from .tag_writer import backup_original, write_tags
from .organizer import move_file
from .restore import restore_from_backup

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
@click.option("--dry-run", is_flag=True)
@click.pass_context
def restore(ctx, dry_run):
    # For convenience: example restore; in production add args
    file_path = click.prompt("Path to file to restore", type=click.Path())
    ok = restore_from_backup(file_path, backup_dir=ctx.obj["cfg"].backup_dir, dry_run=dry_run)
    if ok:
        click.echo("Restore done.")
    else:
        click.echo("Restore failed.")

if __name__ == "__main__":
    cli()