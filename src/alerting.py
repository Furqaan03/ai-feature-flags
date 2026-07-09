"""Slack rollback notifications."""
from __future__ import annotations

import os

import httpx


def send_rollback_alert(flag_name: str, reason: str, quality_data: dict) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return  # alerting is optional; no-op if unconfigured
    text = (
        f":rotating_light: *Auto-rollback triggered* for flag `{flag_name}`\n"
        f"Reason: {reason}\n"
        f"Quality data: {quality_data}"
    )
    with httpx.Client(timeout=10) as client:
        client.post(webhook, json={"text": text}).raise_for_status()
