import pytest
from eval.reference.team_identity import TeamResolver, UnknownTeamError

def resolver():
    return TeamResolver({"teams":[
        {"id":"ipl:royal-challengers-bengaluru","display_name":"Royal Challengers Bengaluru","aliases":["Royal Challengers Bengaluru","Royal Challengers Bangalore"]},
        {"id":"ipl:punjab-kings","display_name":"Punjab Kings","aliases":["Punjab Kings","Kings XI Punjab"]},
    ]})

def test_renamed_franchise_aliases_share_identity():
    r=resolver()
    assert r.resolve("Royal Challengers Bangalore")=="ipl:royal-challengers-bengaluru"
    assert r.resolve("Royal Challengers Bengaluru")=="ipl:royal-challengers-bengaluru"
    assert r.resolve("Kings XI Punjab")=="ipl:punjab-kings"

def test_whitespace_and_case_are_normalized():
    assert resolver().resolve("  PUNJAB   KINGS ")=="ipl:punjab-kings"

def test_unknown_team_fails_loudly():
    with pytest.raises(UnknownTeamError):
        resolver().resolve("Team That Does Not Exist")

def test_alias_collision_is_rejected():
    with pytest.raises(ValueError, match="alias collision"):
        TeamResolver({"teams":[
            {"id":"a","display_name":"A","aliases":["Same"]},
            {"id":"b","display_name":"B","aliases":["Same"]},
        ]})
