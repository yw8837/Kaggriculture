from kaggriculture_lab.evaluation.metrics import mean, wilson_interval


def test_wilson_interval_contains_observed_rate() -> None:
    lower, upper = wilson_interval(60, 100)
    assert lower < 0.60 < upper


def test_mean() -> None:
    assert mean([1.0, 2.0, 3.0]) == 2.0

