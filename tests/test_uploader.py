import boto3
from moto import mock_aws

from backup.uploader import (
    delete_keys,
    list_backups,
    parse_timestamp,
    upload_file,
)


def test_parse_timestamp():
    ts = parse_timestamp("backups/backup-20260131-030000.sql.gz")
    assert (ts.year, ts.month, ts.day, ts.hour) == (2026, 1, 31, 3)
    assert parse_timestamp("backups/outro-arquivo.txt") is None


@mock_aws
def test_upload_list_delete(tmp_path):
    client = boto3.client("s3")
    client.create_bucket(Bucket="bkt")

    for name in ("backup-20260101-030000.sql.gz", "backup-20260102-030000.sql.gz"):
        f = tmp_path / name
        f.write_bytes(b"dados")
        upload_file(client, "bkt", f)

    entries = list_backups(client, "bkt")
    assert [k for k, _ in entries] == [
        "backups/backup-20260102-030000.sql.gz",
        "backups/backup-20260101-030000.sql.gz",
    ]

    delete_keys(client, "bkt", [entries[1][0]])
    assert len(list_backups(client, "bkt")) == 1
