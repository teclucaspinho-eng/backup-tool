"""Upload/listagem/remoção no S3 (ou MinIO, via S3_ENDPOINT_URL)."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import boto3

PREFIX = "backups/"
_KEY_RE = re.compile(r"backup-(\d{8}-\d{6})\.sql\.gz$")


def make_client():
    return boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL") or None)


def parse_timestamp(key: str) -> datetime | None:
    match = _KEY_RE.search(key)
    return datetime.strptime(match.group(1), "%Y%m%d-%H%M%S") if match else None


def upload_file(client, bucket: str, path: str | Path) -> str:
    key = f"{PREFIX}{Path(path).name}"
    client.upload_file(str(path), bucket, key)
    return key


def download_file(client, bucket: str, key: str, dest: str | Path) -> Path:
    client.download_file(bucket, key, str(dest))
    return Path(dest)


def list_backups(client, bucket: str) -> list[tuple[str, datetime]]:
    """Lista (chave, data) ordenado do mais recente para o mais antigo."""
    entries = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            ts = parse_timestamp(obj["Key"])
            if ts:
                entries.append((obj["Key"], ts))
    return sorted(entries, key=lambda e: e[1], reverse=True)


def delete_keys(client, bucket: str, keys: list[str]) -> None:
    for i in range(0, len(keys), 1000):  # limite da API: 1000 por chamada
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
