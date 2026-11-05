# 💾 Backup Tool

Ferramenta de backup de **PostgreSQL** com envio para **S3/MinIO**, **retenção GFS** (7 diários, 4 semanais, 6 mensais), **restore** e notificações no Slack (sucesso e falha).

## Arquitetura

```
 PostgreSQL ──pg_dump──► gzip (streaming) ──► S3 / MinIO  backups/backup-YYYYmmdd-HHMMSS.sql.gz
                                                  │
                          retenção GFS ◄──────────┘  (remove o que sai da política)
                                │
                                ▼
                         Slack: ✅ sucesso / ❌ falha
```

## Retenção

Mantém o backup **mais recente** de cada período: últimos 7 dias, últimas 4 semanas e últimos 6 meses. Backups fora disso são apagados. Os valores são configuráveis (`KEEP_DAILY`, `KEEP_WEEKLY`, `KEEP_MONTHLY`).

## Como rodar (ambiente local com MinIO)

```bash
docker compose up -d                 # Postgres + MinIO + bucket "backups"
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export $(grep -v '^#' .env | xargs)

python -m backup.main backup         # gera, envia e aplica retenção
python -m backup.main list           # lista backups
python -m backup.main restore        # restaura o mais recente (ou: restore <chave>)
python -m backup.main prune          # só aplica retenção
```

Requer `pg_dump`/`psql` instalados (versão ≥ à do servidor). Console do MinIO: http://localhost:9001 (minioadmin / minioadmin).

**Docker:** `docker build -t backup-tool . && docker run --rm --env-file .env --network host backup-tool backup`

**Agendamento:** `cron` (`0 3 * * * ...`) ou o workflow `.github/workflows/scheduled-backup.yml`.

## Segurança

- A senha vai por variável `PGPASSWORD`, nunca na linha de comando.
- Dumps são enviados em streaming; se o `pg_dump` falhar, o arquivo parcial é removido e um alerta é enviado.
- Em produção, use IAM role/credenciais mínimas e habilite *versioning* e criptografia no bucket.

## Testes

```bash
pytest -v && ruff check .
```
Os testes usam `moto` (S3 simulado) e mocks do `pg_dump`, então não precisam de banco nem AWS.
