from eval.reference.cricsheet_json import normalize_match


def sample():
    return {
        "meta": {"data_version": "1.3.0", "created": "2026-01-01", "revision": 1},
        "info": {
            "dates": ["2026-01-01"],
            "event": {"name": "Test Competition"},
            "gender": "male",
            "match_type": "T20",
            "overs": 20,
            "registry": {
                "people": {
                    "BAT": "aaaaaaaa",
                    "NS": "bbbbbbbb",
                    "BOW": "cccccccc",
                    "OUT": "dddddddd",
                }
            },
            "teams": ["Alpha", "Beta"],
            "outcome": {"winner": "Alpha"},
        },
        "innings": [
            {
                "team": "Alpha",
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            {
                                "batter": "BAT",
                                "bowler": "BOW",
                                "non_striker": "NS",
                                "runs": {"batter": 4, "extras": 0, "total": 4},
                            },
                            {
                                "batter": "BAT",
                                "bowler": "BOW",
                                "non_striker": "NS",
                                "extras": {"wides": 1},
                                "runs": {"batter": 0, "extras": 1, "total": 1},
                            },
                            {
                                "batter": "BAT",
                                "bowler": "BOW",
                                "non_striker": "NS",
                                "extras": {"byes": 2},
                                "runs": {"batter": 0, "extras": 2, "total": 2},
                            },
                            {
                                "batter": "BAT",
                                "bowler": "BOW",
                                "non_striker": "NS",
                                "wickets": [{"kind": "bowled", "player_out": "BAT"}],
                                "runs": {"batter": 0, "extras": 0, "total": 0},
                            },
                        ],
                    }
                ],
            }
        ],
    }


def test_normalizes_legal_delivery_and_runs():
    rows = normalize_match(sample(), "match-1")
    assert len(rows) == 4
    assert rows[0].legal_delivery is True
    assert rows[0].batter_runs == 4
    assert rows[0].bowler_id == "cccccccc"


def test_wide_is_not_legal():
    rows = normalize_match(sample(), "match-1")
    assert rows[1].legal_delivery is False
    assert rows[1].wide_runs == 1


def test_bye_is_not_batter_run_but_remains_total():
    rows = normalize_match(sample(), "match-1")
    assert rows[2].batter_runs == 0
    assert rows[2].bye_runs == 2
    assert rows[2].total_runs == 2


def test_wicket_preserves_kind_and_player_id():
    rows = normalize_match(sample(), "match-1")
    assert rows[3].dismissal_kind == "bowled"
    assert rows[3].dismissed_player_id == "aaaaaaaa"
