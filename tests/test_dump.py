import gzip
import io

import pytest

from backup import dump
from backup.dump import DbConfig, DumpError, build_filename, create_dump


class FakePopen:
    returncode = 0

    def __init__(self, cmd, stdout=None, stderr=None, stdin=None, env=None):
        self.cmd = cmd
        self.stdout = io.BytesIO(b"CREATE TABLE t (id int);")
        self.stdin = io.BytesIO()
        self.env = env

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_build_filename():
    from datetime import datetime

    assert build_filename(datetime(2026, 1, 2, 3, 4, 5)) == "backup-20260102-030405.sql.gz"


def test_create_dump_gera_gzip(tmp_path, monkeypatch):
    monkeypatch.setattr(dump.subprocess, "Popen", FakePopen)
    path = create_dump(DbConfig(password="segredo", database="app"), tmp_path)
    assert path.suffixes[-2:] == [".sql", ".gz"]
    with gzip.open(path) as f:
        assert f.read() == b"CREATE TABLE t (id int);"


def test_create_dump_falha_remove_arquivo(tmp_path, monkeypatch):
    class Failing(FakePopen):
        returncode = 1

    monkeypatch.setattr(dump.subprocess, "Popen", Failing)
    with pytest.raises(DumpError):
        create_dump(DbConfig(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_senha_vai_por_env_e_nao_no_comando(tmp_path, monkeypatch):
    captured = {}

    class Spy(FakePopen):
        def __init__(self, cmd, **kw):
            super().__init__(cmd, **kw)
            captured["cmd"], captured["env"] = cmd, kw["env"]

    monkeypatch.setattr(dump.subprocess, "Popen", Spy)
    create_dump(DbConfig(password="segredo"), tmp_path)
    assert "segredo" not in " ".join(captured["cmd"])
    assert captured["env"]["PGPASSWORD"] == "segredo"
