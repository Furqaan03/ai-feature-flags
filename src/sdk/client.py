"""Lightweight client SDK — the 3-5 line integration apps use.

    flag_client.evaluate("my-flag", user_id="u123") -> "baseline" | "experimental"

Handles consistent assignment, local caching, and graceful degradation
(defaults to baseline) if the flag service is unreachable."""
from __future__ import annotations

from src.flags.evaluator import evaluate
from src.flags.schema import AIFeatureFlag, Variant


class FlagClient:
    def __init__(self, flags: dict[str, AIFeatureFlag] | None = None):
        self._flags = flags or {}

    def register(self, flag: AIFeatureFlag) -> None:
        self._flags[flag.name] = flag

    def evaluate(self, flag_name: str, user_id: str, segment: str | None = None) -> str:
        flag = self._flags.get(flag_name)
        if flag is None:
            # Graceful degradation: unknown/unreachable flag -> baseline, never crash the app.
            return Variant.BASELINE
        try:
            return evaluate(flag, user_id, segment)
        except Exception:  # noqa: BLE001 — the app must never break because of the flag layer
            return Variant.BASELINE
