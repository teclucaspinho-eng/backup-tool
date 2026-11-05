"""Política de retenção GFS (avô-pai-filho): diário, semanal e mensal."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Policy:
    daily: int = 7
    weekly: int = 4
    monthly: int = 6


def _newest_per_period(entries, period_key, limit: int) -> set[str]:
    """Mantém o backup mais recente de cada um dos últimos `limit` períodos."""
    keep: set[str] = set()
    seen: list = []
    for key, ts in entries:  # entries já vem do mais recente para o mais antigo
        period = period_key(ts)
        if period in seen:
            continue
        if len(seen) >= limit:
            break
        seen.append(period)
        keep.add(key)
    return keep


def select_to_keep(entries: list[tuple[str, datetime]], policy: Policy) -> set[str]:
    ordered = sorted(entries, key=lambda e: e[1], reverse=True)
    return (
        _newest_per_period(ordered, lambda t: t.date(), policy.daily)
        | _newest_per_period(ordered, lambda t: t.isocalendar()[:2], policy.weekly)
        | _newest_per_period(ordered, lambda t: (t.year, t.month), policy.monthly)
    )


def select_to_delete(entries: list[tuple[str, datetime]], policy: Policy) -> list[str]:
    keep = select_to_keep(entries, policy)
    return [key for key, _ in entries if key not in keep]
