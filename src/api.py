"""FastAPI management API: create flags, evaluate, record quality, auto-rollback."""
from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.alerting import send_rollback_alert
from src.flags.evaluator import evaluate
from src.flags.schema import AIFeatureFlag
from src.quality.monitor import QualityWindow, RollbackMonitor

load_dotenv()

app = FastAPI(title="AI Feature Flag System")

_flags: dict[str, AIFeatureFlag] = {}
_windows: dict[str, QualityWindow] = {}       # flag_name -> experimental quality window
_monitors: dict[str, RollbackMonitor] = {}


@app.post("/flags")
def create_flag(flag: AIFeatureFlag) -> dict:
    _flags[flag.name] = flag
    _windows[flag.name] = QualityWindow()
    _monitors[flag.name] = RollbackMonitor(
        min_quality=flag.rollback_trigger.min_quality_score,
        sustained=flag.rollback_trigger.sustained_evaluations,
    )
    return {"name": flag.name, "status": flag.status}


class EvaluateRequest(BaseModel):
    user_id: str
    segment: str | None = None


@app.post("/flags/{name}/evaluate")
def evaluate_flag(name: str, req: EvaluateRequest) -> dict:
    flag = _flags.get(name)
    if flag is None:
        raise HTTPException(404, "Flag not found")
    return {"variant": evaluate(flag, req.user_id, req.segment)}


class QualityReport(BaseModel):
    score: float


@app.post("/flags/{name}/quality")
def record_quality(name: str, report: QualityReport) -> dict:
    flag = _flags.get(name)
    if flag is None:
        raise HTTPException(404, "Flag not found")

    _windows[name].record(report.score)
    decision = _monitors[name].record(report.score)

    if decision.should_rollback and flag.status != "rolled_back":
        flag.status = "rolled_back"
        flag.rollout_percentage = 0.0
        quality_data = {"p10": _windows[name].p10(), "mean": _windows[name].mean(), "trend": _windows[name].trend()}
        send_rollback_alert(name, decision.reason, quality_data)
        return {"status": "rolled_back", "reason": decision.reason, "quality": quality_data}

    return {"status": flag.status, "consecutive_below": decision.consecutive_below}


class RolloutUpdate(BaseModel):
    percentage: float


@app.post("/flags/{name}/rollout")
def update_rollout(name: str, update: RolloutUpdate) -> dict:
    flag = _flags.get(name)
    if flag is None:
        raise HTTPException(404, "Flag not found")
    flag.rollout_percentage = max(0.0, min(100.0, update.percentage))
    flag.status = "fully_on" if flag.rollout_percentage >= 100 else "rolling_out"
    return {"name": name, "rollout_percentage": flag.rollout_percentage, "status": flag.status}


@app.post("/flags/{name}/rollback")
def manual_rollback(name: str) -> dict:
    flag = _flags.get(name)
    if flag is None:
        raise HTTPException(404, "Flag not found")
    flag.status = "rolled_back"
    flag.rollout_percentage = 0.0
    return {"status": "rolled_back"}


@app.get("/flags/{name}")
def get_flag(name: str) -> dict:
    flag = _flags.get(name)
    if flag is None:
        raise HTTPException(404, "Flag not found")
    window = _windows[name]
    return {
        "flag": flag.model_dump(),
        "quality": {"mean": window.mean(), "p10": window.p10(), "trend": window.trend()},
    }
