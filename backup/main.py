"""CLI: backup | restore | prune | list"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

from .dump import DbConfig, create_dump, restore_dump
from .notify import notify
from .retention import Policy, select_to_delete
from .uploader import (
    delete_keys,
    download_file,
    list_backups,
    make_client,
    upload_file,
)

log = logging.getLogger("backup")


def policy_from_env() -> Policy:
    return Policy(
        daily=int(os.getenv("KEEP_DAILY", "7")),
        weekly=int(os.getenv("KEEP_WEEKLY", "4")),
        monthly=int(os.getenv("KEEP_MONTHLY", "6")),
    )


def prune(client, bucket: str) -> list[str]:
    to_delete = select_to_delete(list_backups(client, bucket), policy_from_env())
    if to_delete:
        delete_keys(client, bucket, to_delete)
    return to_delete


def cmd_backup(bucket: str) -> None:
    client = make_client()
    with tempfile.TemporaryDirectory() as tmp:
        dump = create_dump(DbConfig.from_env(), tmp)
        size_mb = dump.stat().st_size / 1_048_576
        key = upload_file(client, bucket, dump)
    removed = prune(client, bucket)
    notify(f"✅ Backup concluído: {key} ({size_mb:.1f} MB). {len(removed)} antigo(s) removido(s).")


def cmd_restore(bucket: str, key: str | None) -> None:
    client = make_client()
    key = key or (list_backups(client, bucket) or [(None, None)])[0][0]
    if not key:
        raise SystemExit("Nenhum backup encontrado")
    with tempfile.TemporaryDirectory() as tmp:
        local = download_file(client, bucket, key, Path(tmp) / "restore.sql.gz")
        restore_dump(DbConfig.from_env(), local)
    notify(f"♻️ Restore concluído a partir de {key}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="backup", description="Backup PostgreSQL → S3")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("backup", help="gera dump, envia e aplica retenção")
    restore = sub.add_parser("restore", help="restaura um backup (padrão: o mais recente)")
    restore.add_argument("key", nargs="?")
    sub.add_parser("prune", help="aplica a política de retenção")
    sub.add_parser("list", help="lista os backups")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        raise SystemExit("Defina S3_BUCKET")

    try:
        if args.command == "backup":
            cmd_backup(bucket)
        elif args.command == "restore":
            cmd_restore(bucket, args.key)
        elif args.command == "prune":
            print(f"{len(prune(make_client(), bucket))} backup(s) removido(s)")
        elif args.command == "list":
            for key, ts in list_backups(make_client(), bucket):
                print(f"{ts:%Y-%m-%d %H:%M:%S}  {key}")
    except Exception as exc:
        log.exception("Falha na operação '%s'", args.command)
        notify(f"❌ Falha no {args.command}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
