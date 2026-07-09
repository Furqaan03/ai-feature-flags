from src.rollout.stages import StagedRollout, canary_analysis


def test_canary_blocks_when_experimental_worse():
    baseline = [5.0] * 30
    experimental = [2.0] * 30
    result = canary_analysis(baseline, experimental)
    assert result.experimental_no_worse is False


def test_canary_allows_when_comparable():
    baseline = [4.0, 5.0, 4.0, 5.0, 4.0, 5.0, 4.0, 5.0, 4.0, 5.0]
    experimental = [4.0, 5.0, 5.0, 4.0, 5.0, 4.0, 5.0, 4.0, 5.0, 5.0]
    result = canary_analysis(baseline, experimental)
    assert result.experimental_no_worse is True


def test_staged_rollout_advances_on_good_canary():
    rollout = StagedRollout()
    assert rollout.current_percentage == 1
    good = canary_analysis([4.0] * 10, [5.0] * 10)
    advanced, _ = rollout.try_advance(good)
    assert advanced is True
    assert rollout.current_percentage == 5


def test_staged_rollout_pauses_on_bad_canary():
    rollout = StagedRollout()
    bad = canary_analysis([5.0] * 30, [1.0] * 30)
    advanced, msg = rollout.try_advance(bad)
    assert advanced is False
    assert "paused" in msg
    assert rollout.current_percentage == 1  # stayed put
