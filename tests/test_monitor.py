from src.quality.monitor import QualityWindow, RollbackMonitor


def test_rollback_fires_after_sustained_low_quality():
    monitor = RollbackMonitor(min_quality=3.0, sustained=5)
    decisions = [monitor.record(2.0) for _ in range(5)]
    assert decisions[-1].should_rollback is True
    assert decisions[3].should_rollback is False  # not yet sustained


def test_good_score_resets_counter():
    monitor = RollbackMonitor(min_quality=3.0, sustained=3)
    monitor.record(2.0)
    monitor.record(2.0)
    monitor.record(5.0)  # reset
    d = monitor.record(2.0)
    assert d.should_rollback is False
    assert d.consecutive_below == 1


def test_p10_catches_tail():
    w = QualityWindow()
    for _ in range(90):
        w.record(5.0)
    for _ in range(10):
        w.record(1.0)   # 10% bad tail
    assert w.p10() == 1.0     # worst-decile surfaces the tail
    assert w.mean() > 4.0     # mean hides it


def test_trend_detects_degradation():
    w = QualityWindow()
    for _ in range(15):
        w.record(5.0)
    for _ in range(15):
        w.record(2.0)
    assert w.trend() == "degrading"
