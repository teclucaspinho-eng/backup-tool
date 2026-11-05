"""Notificação via Slack webhook (opcional)."""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("backup")


def notify(message: str) -> None:
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        log.info("Notificação (sem webhook configurado): %s", message)
        return
    try:
        requests.post(url, json={"text": message}, timeout=10).raise_for_status()
    except requests.RequestException:
        log.exception("Falha ao enviar notificação")
