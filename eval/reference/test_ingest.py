from eval.reference.ingest import exclusion_reason, in_mvp_scope
from eval.reference.test_cricsheet_json import sample


def test_mvp_scope_accepts_mens_ipl_or_international_t20():
    payload = sample()
    payload["info"]["event"] = {"name": "Indian Premier League"}
    payload["info"]["team_type"] = "club"
    assert in_mvp_scope(payload)

    payload["info"]["event"] = {"name": "ICC Men's T20 World Cup"}
    payload["info"]["team_type"] = "international"
    assert in_mvp_scope(payload)


def test_scope_rejects_revised_target():
    payload = sample()
    payload["info"]["team_type"] = "international"
    payload["info"]["outcome"] = {"winner": "India", "method": "D/L"}
    assert exclusion_reason(payload) == "revised_target"
    assert not in_mvp_scope(payload)


def test_scope_rejects_no_result():
    payload = sample()
    payload["info"]["team_type"] = "international"
    payload["info"]["outcome"] = {"result": "no result"}
    assert exclusion_reason(payload) == "no_result"
    assert not in_mvp_scope(payload)


def test_scope_rejects_super_over_decider():
    payload = sample()
    payload["info"]["team_type"] = "international"
    payload["info"]["outcome"] = {"result": "tie", "eliminator": "India"}
    assert exclusion_reason(payload) == "super_over_or_bowl_out"
    assert not in_mvp_scope(payload)


def test_scope_rejects_pre_2022():
    payload = sample()
    payload["info"]["dates"] = ["2021-12-31"]
    assert exclusion_reason(payload) == "before_2022"
