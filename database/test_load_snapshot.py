import pytest

from database.load_snapshot import competition_id, resolve_team, team_resolver


def test_competition_ids_are_stable_slugs():
    assert competition_id("Indian Premier League") == "competition:indian-premier-league"
    assert competition_id(None) is None


def test_team_resolution_uses_explicit_aliases_case_insensitively():
    aliases, teams = team_resolver({
        "teams": [
            {"id": "ipl:delhi-capitals", "display_name": "Delhi Capitals",
             "aliases": ["Delhi Daredevils"]},
        ]
    })
    assert resolve_team("Delhi Daredevils", aliases, context="test") == "ipl:delhi-capitals"
    assert resolve_team("DELHI CAPITALS", aliases, context="test") == "ipl:delhi-capitals"
    assert teams["ipl:delhi-capitals"]["display_name"] == "Delhi Capitals"


def test_unknown_team_does_not_fuzzy_match():
    aliases, _ = team_resolver({
        "teams": [{"id": "team:india", "display_name": "India", "aliases": ["India"]}]
    })
    with pytest.raises(ValueError, match="Unmapped team"):
        resolve_team("Inda", aliases, context="test")


def test_conflicting_aliases_fail_closed():
    with pytest.raises(ValueError, match="Ambiguous team alias"):
        team_resolver({
            "teams": [
                {"id": "team:one", "display_name": "Team One", "aliases": ["Same"]},
                {"id": "team:two", "display_name": "Team Two", "aliases": ["same"]},
            ]
        })
