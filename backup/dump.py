"""Dump e restore de PostgreSQL com compressão gzip (streaming, sem estourar memória)."""
from __future__ import annotations

import gzip
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class DumpError(RuntimeError):
    pass


@dataclass
class DbConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "postgres"

    @classmethod
    def from_env(cls) -> DbConfig:
        return cls(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", ""),
            database=os.getenv("PGDATABASE", "postgres"),
        )

    def _env(self) -> dict[str, str]:
        return {**os.environ, "PGPASSWORD": self.password}

    def _args(self) -> list[str]:
        return ["-h", self.host, "-p", str(self.port), "-U", self.user]


def build_filename(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"backup-{now:%Y%m%d-%H%M%S}.sql.gz"


def create_dump(cfg: DbConfig, output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / build_filename()
    cmd = ["pg_dump", "--no-owner", *cfg._args(), cfg.database]

    with tempfile.TemporaryFile() as err:
        with (
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, env=cfg._env()) as proc,
            gzip.open(path, "wb") as gz,
        ):
            shutil.copyfileobj(proc.stdout, gz)
        if proc.returncode != 0:
            err.seek(0)
            path.unlink(missing_ok=True)
            raise DumpError(err.read().decode(errors="replace").strip() or "pg_dump falhou")
    return path


def restore_dump(cfg: DbConfig, dump_path: str | Path) -> None:
    cmd = ["psql", "-v", "ON_ERROR_STOP=1", *cfg._args(), "-d", cfg.database]
    with tempfile.TemporaryFile() as err:
        with (
            subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err, env=cfg._env()) as proc,
            gzip.open(dump_path, "rb") as gz,
        ):
            shutil.copyfileobj(gz, proc.stdin)
            proc.stdin.close()
        if proc.returncode != 0:
            err.seek(0)
            raise DumpError(err.read().decode(errors="replace").strip() or "psql falhou")
