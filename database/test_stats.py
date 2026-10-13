import pytest

from database.stats import competition_key, phase_stats, top_batters, top_bowlers


def test_competition_key_is_stable_and_explicit():
    assert competition_key("Indian Premier League") == "competition:indian-premier-league"
    assert competition_key("International T20") == "competition:international-t20"
    assert competition_key(None) is None


@pytest.mark.parametrize("function,kwargs,message", [
    (top_batters, {"limit": 0}, "limit must be between 1 and 50"),
    (top_batters, {"limit": 51}, "limit must be between 1 and 50"),
    (top_batters, {"min_balls": -1}, "min_balls must be non-negative"),
    (top_bowlers, {"limit": 0}, "limit must be between 1 and 50"),
    (top_bowlers, {"min_legal_balls": -1}, "min_legal_balls must be non-negative"),
])
def test_leaderboard_parameters_fail_closed(function, kwargs, message):
    with pytest.raises(ValueError, match=message):
        function("postgresql://unused", **kwargs)


def test_unknown_phase_is_rejected_before_database_access():
    with pytest.raises(ValueError, match="phase must be powerplay, middle, or death"):
        phase_stats("postgresql://unused", phase="super-over")
