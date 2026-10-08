import pytest

from stats_reference import Ball, batting_summary, bowling_summary, phase_for_over, require_min_sample


def test_standard_t20_phases():
    assert phase_for_over(1) == "powerplay"
    assert phase_for_over(6) == "powerplay"
    assert phase_for_over(7) == "middle"
    assert phase_for_over(15) == "middle"
    assert phase_for_over(16) == "death"
    assert phase_for_over(20) == "death"


def test_shortened_ten_over_phases():
    assert phase_for_over(1, 10) == "powerplay"
    assert phase_for_over(6, 10) == "powerplay"
    assert phase_for_over(7, 10) == "death"
    assert phase_for_over(10, 10) == "death"


def test_shortened_six_over_innings_has_only_powerplay():
    assert all(phase_for_over(over, 6) == "powerplay" for over in range(1, 7))


def test_batting_excludes_non_faced_wide_and_keeps_runs():
    balls = [
        Ball("m1", 1, 1, True, "p1", "b1", 4, 4, 4, True, False, False),
        Ball("m1", 1, 1, False, "p1", "b1", 0, 1, 1, False, False, False),
        Ball("m1", 1, 2, True, "p1", "b1", 1, 1, 1, True, False, False),
    ]
    result = batting_summary(balls, "p1")
    assert result["runs"] == 5
    assert result["legal_balls"] == 2
    assert result["strike_rate"] == 250.0


def test_bowling_includes_wides_but_not_byes_or_leg_byes():
    balls = [
        Ball("m1", 1, 1, True, "p1", "b1", 0, 4, 4, True, False, False),
        Ball("m1", 1, 2, False, "p1", "b1", 0, 1, 1, False, False, False),
        Ball("m1", 1, 3, False, "p1", "b1", 0, 1, 0, False, False, False),
    ]
    result = bowling_summary(balls, "b1")
    assert result["runs_conceded"] == 5
    assert result["legal_balls"] == 1


def test_sample_gate_is_explicit():
    assert require_min_sample(29, 30)["thin_sample"] is True
    assert require_min_sample(30, 30)["eligible"] is True
