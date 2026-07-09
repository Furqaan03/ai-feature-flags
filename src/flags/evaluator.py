"""Flag evaluation: consistent user assignment, targeting rules, percentage rollout."""
from __future__ import annotations

import hashlib

from src.flags.schema import AIFeatureFlag, Variant


def _bucket(flag_name: str, user_id: str) -> float:
    digest = hashlib.sha256(f"{flag_name}:{user_id}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF  # stable float in [0, 1)


def evaluate(flag: AIFeatureFlag, user_id: str, segment: str | None = None) -> str:
    """Returns which variant to serve. Same (flag, user) is always stable.
    Precedence: rolled_back/off -> baseline; allow/block lists -> forced;
    segment targeting -> experimental; else percentage bucket."""
    if flag.status in ("off", "rolled_back"):
        return Variant.BASELINE
    if flag.status == "fully_on":
        return Variant.EXPERIMENTAL

    if user_id in flag.targeting.blocklist:
        return Variant.BASELINE
    if user_id in flag.targeting.allowlist:
        return Variant.EXPERIMENTAL
    if segment and flag.targeting.segments and segment in flag.targeting.segments:
        return Variant.EXPERIMENTAL

    # Percentage-based rollout via consistent hashing.
    if _bucket(flag.name, user_id) < (flag.rollout_percentage / 100.0):
        return Variant.EXPERIMENTAL
    return Variant.BASELINE
