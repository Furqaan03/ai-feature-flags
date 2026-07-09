"""Staged rollout automation with canary analysis: only advance when experimental
is statistically no worse than baseline."""
from __future__ import annotations

from dataclasses import dataclass

from scipy import stats


@dataclass
class RolloutStage:
    percentage: float
    hold_seconds: float


# Default staged schedule: 1% -> 5% -> 25% -> 50% -> 100%.
DEFAULT_STAGES = [
    RolloutStage(1, 2 * 3600),
    RolloutStage(5, 6 * 3600),
    RolloutStage(25, 24 * 3600),
    RolloutStage(50, 24 * 3600),
    RolloutStage(100, 0),
]


@dataclass
class CanaryResult:
    experimental_no_worse: bool
    p_value: float
    experimental_mean: float
    baseline_mean: float
    reason: str


def canary_analysis(baseline_scores: list[float], experimental_scores: list[float], confidence: float = 0.95) -> CanaryResult:
    """Advance only if experimental is not significantly worse than baseline.
    Uses a one-sided Mann-Whitney U (is experimental < baseline?)."""
    if len(baseline_scores) < 5 or len(experimental_scores) < 5:
        return CanaryResult(False, 1.0, 0.0, 0.0, "insufficient_data")

    exp_mean = sum(experimental_scores) / len(experimental_scores)
    base_mean = sum(baseline_scores) / len(baseline_scores)

    # H1: experimental is worse (less) than baseline.
    _stat, p_value = stats.mannwhitneyu(experimental_scores, baseline_scores, alternative="less")

    # If p < alpha, experimental IS significantly worse -> do not advance.
    significantly_worse = p_value < (1 - confidence)
    no_worse = not significantly_worse

    return CanaryResult(
        experimental_no_worse=no_worse,
        p_value=float(p_value),
        experimental_mean=exp_mean,
        baseline_mean=base_mean,
        reason="experimental significantly worse" if significantly_worse else "experimental no worse than baseline",
    )


class StagedRollout:
    def __init__(self, stages: list[RolloutStage] | None = None):
        self.stages = stages or DEFAULT_STAGES
        self.current_index = 0

    @property
    def current_percentage(self) -> float:
        return self.stages[self.current_index].percentage

    def try_advance(self, canary: CanaryResult) -> tuple[bool, str]:
        """Advances to the next stage only if the canary says experimental is no worse."""
        if not canary.experimental_no_worse:
            return False, f"paused at {self.current_percentage}% — {canary.reason}"
        if self.current_index >= len(self.stages) - 1:
            return False, "already at final stage (100%)"
        self.current_index += 1
        return True, f"advanced to {self.current_percentage}%"
