"""AI feature flag schema — beyond boolean: rollout %, quality threshold, rollback trigger."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TargetingRules(BaseModel):
    allowlist: list[str] = Field(default_factory=list)   # always experimental
    blocklist: list[str] = Field(default_factory=list)   # always baseline
    segments: list[str] = Field(default_factory=list)    # e.g. ["internal", "beta"]


class RollbackTrigger(BaseModel):
    min_quality_score: float = 3.0        # P10 quality floor
    sustained_evaluations: int = 50       # consecutive evals below floor before rollback
    cooldown_seconds: float = 300.0       # prevent flapping


class AIFeatureFlag(BaseModel):
    name: str
    rollout_percentage: float = 0.0       # 0-100
    quality_threshold: float = 3.0
    rollback_trigger: RollbackTrigger = Field(default_factory=RollbackTrigger)
    baseline_config: dict = Field(default_factory=dict)      # served when flag is off
    experimental_config: dict = Field(default_factory=dict)  # the new AI feature
    targeting: TargetingRules = Field(default_factory=TargetingRules)
    status: str = "off"   # off | rolling_out | fully_on | rolled_back | paused


class Variant:
    BASELINE = "baseline"
    EXPERIMENTAL = "experimental"
