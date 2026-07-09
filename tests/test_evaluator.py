from src.flags.evaluator import evaluate
from src.flags.schema import AIFeatureFlag, TargetingRules, Variant


def test_off_flag_serves_baseline():
    flag = AIFeatureFlag(name="f", status="off", rollout_percentage=100)
    assert evaluate(flag, "user-1") == Variant.BASELINE


def test_fully_on_serves_experimental():
    flag = AIFeatureFlag(name="f", status="fully_on")
    assert evaluate(flag, "user-1") == Variant.EXPERIMENTAL


def test_same_user_stable_assignment():
    flag = AIFeatureFlag(name="f", status="rolling_out", rollout_percentage=50)
    first = evaluate(flag, "user-42")
    assert all(evaluate(flag, "user-42") == first for _ in range(20))


def test_allowlist_forces_experimental():
    flag = AIFeatureFlag(name="f", status="rolling_out", rollout_percentage=0,
                         targeting=TargetingRules(allowlist=["vip"]))
    assert evaluate(flag, "vip") == Variant.EXPERIMENTAL


def test_blocklist_forces_baseline():
    flag = AIFeatureFlag(name="f", status="rolling_out", rollout_percentage=100,
                         targeting=TargetingRules(blocklist=["banned"]))
    assert evaluate(flag, "banned") == Variant.BASELINE


def test_segment_targeting():
    flag = AIFeatureFlag(name="f", status="rolling_out", rollout_percentage=0,
                         targeting=TargetingRules(segments=["internal"]))
    assert evaluate(flag, "u1", segment="internal") == Variant.EXPERIMENTAL
    assert evaluate(flag, "u1", segment="external") == Variant.BASELINE


def test_rollout_percentage_distribution():
    flag = AIFeatureFlag(name="f", status="rolling_out", rollout_percentage=30)
    exp = sum(1 for i in range(2000) if evaluate(flag, f"user-{i}") == Variant.EXPERIMENTAL)
    assert 500 < exp < 700  # ~30% of 2000
