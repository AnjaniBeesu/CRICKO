import pytest

from eval.reference.cricsheet_json import normalize_match
from eval.reference.team_identity import TeamResolver, UnknownTeamError

def sample():
    return {
        "meta": {"data_version": "1.3.0", "created": "2026-01-01", "revision": 1},
        "info": {
            "dates": ["2026-01-01"],
            "event": {"name": "Test Competition"},
            "gender": "male",
            "match_type": "T20",
            "overs": 20,
            "registry": {"people": {"BAT": "aaaaaaaa", "NS": "bbbbbbbb", "BOW": "cccccccc", "OUT": "dddddddd"}},
            "teams": ["India", "Australia"],
            "outcome": {"winner": "India"},
        },
        "innings": [{
            "team": "India",
            "overs": [{
                "over": 0,
                "deliveries": [
                    {"batter":"BAT","bowler":"BOW","non_striker":"NS","runs":{"batter":4,"extras":0,"total":4}},
                    {"batter":"BAT","bowler":"BOW","non_striker":"NS","extras":{"wides":1},"runs":{"batter":0,"extras":1,"total":1}},
                    {"batter":"BAT","bowler":"BOW","non_striker":"NS","extras":{"byes":2},"runs":{"batter":0,"extras":2,"total":2}},
                    {"batter":"BAT","bowler":"BOW","non_striker":"NS","wickets":[{"kind":"bowled","player_out":"BAT"}],"runs":{"batter":0,"extras":0,"total":0}},
                ],
            }]
        }],
    }

def test_normalizes_legal_delivery_and_runs():
    rows = normalize_match(sample(), "match-1")
    assert len(rows) == 4
    assert rows[0].legal_delivery is True
    assert rows[0].batter_runs == 4
    assert rows[0].bowler_id == "cccccccc"
    assert rows[0].team_batting_id == "team:india"
    assert rows[0].team_bowling_id == "team:australia"

def test_wide_is_not_legal():
    assert normalize_match(sample(), "match-1")[1].legal_delivery is False

def test_bye_is_not_batter_run_but_remains_total():
    row = normalize_match(sample(), "match-1")[2]
    assert row.batter_runs == 0
    assert row.bye_runs == 2
    assert row.total_runs == 2

def test_wicket_preserves_kind_and_player_id():
    row = normalize_match(sample(), "match-1")[3]
    assert row.dismissal_kind == "bowled"
    assert row.dismissed_player_id == "aaaaaaaa"

def test_unknown_source_team_fails_loudly():
    payload = sample()
    payload["info"]["teams"] = ["India", "Mystery XI"]
    with pytest.raises(UnknownTeamError):
        normalize_match(payload, "match-unknown")
