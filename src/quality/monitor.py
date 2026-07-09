"""Rolling quality windows + automatic rollback trigger."""
from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field


@dataclass
class QualityWindow:
    """Tracks recent quality scores for one variant of one flag."""
    maxlen: int = 100
    scores: deque = field(default_factory=lambda: deque(maxlen=100))

    def record(self, score: float) -> None:
        self.scores.append(score)

    def mean(self) -> float | None:
        return statistics.mean(self.scores) if self.scores else None

    def p10(self) -> float | None:
        """Worst-10th-percentile score — catches tail failures a mean would hide.
        Uses ceil(0.10*n)-1 so a bottom-10% bad tail is captured, not the first
        good value just past it."""
        import math

        if not self.scores:
            return None
        if len(self.scores) < 10:
            return min(self.scores)
        ordered = sorted(self.scores)
        idx = max(0, math.ceil(0.10 * len(ordered)) - 1)
        return ordered[idx]

    def trend(self) -> str:
        if len(self.scores) < 20:
            return "insufficient_data"
        half = len(self.scores) // 2
        first = statistics.mean(list(self.scores)[:half])
        second = statistics.mean(list(self.scores)[half:])
        if second > first + 0.2:
            return "improving"
        if second < first - 0.2:
            return "degrading"
        return "stable"


@dataclass
class RollbackDecision:
    should_rollback: bool
    reason: str
    consecutive_below: int


class RollbackMonitor:
    """Fires a rollback when experimental P10 quality stays below the floor for
    a sustained number of consecutive evaluations."""

    def __init__(self, min_quality: float, sustained: int):
        self.min_quality = min_quality
        self.sustained = sustained
        self._consecutive_below = 0

    def record(self, score: float) -> RollbackDecision:
        if score < self.min_quality:
            self._consecutive_below += 1
        else:
            self._consecutive_below = 0

        if self._consecutive_below >= self.sustained:
            return RollbackDecision(
                should_rollback=True,
                reason=f"{self._consecutive_below} consecutive evals below quality floor {self.min_quality}",
                consecutive_below=self._consecutive_below,
            )
        return RollbackDecision(should_rollback=False, reason="", consecutive_below=self._consecutive_below)
