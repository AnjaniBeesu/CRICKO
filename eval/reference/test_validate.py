import pytest

from eval.reference.cricsheet_json import normalize_match
from eval.reference.test_cricsheet_json import sample
from eval.reference.validate import validate_rows


def test_valid_rows_pass():
    validate_rows(normalize_match(sample(), "match-1"))


def test_duplicate_delivery_is_rejected():
    rows = normalize_match(sample(), "match-1")
    with pytest.raises(ValueError, match="duplicate"):
        validate_rows(rows + [rows[0]])


def test_run_total_mismatch_is_rejected():
    rows = normalize_match(sample(), "match-1")
    bad = rows[0].__class__(**{**rows[0].__dict__, "total_runs": 5})
    with pytest.raises(ValueError, match="run total"):
        validate_rows([bad])


def test_extras_breakdown_is_rejected():
    rows = normalize_match(sample(), "match-1")
    bad = rows[2].__class__(**{**rows[2].__dict__, "extras_total": 1})
    with pytest.raises(ValueError, match="extras breakdown"):
        validate_rows([bad])


def test_missing_actual_delivery_is_rejected():
    rows = normalize_match(sample(), "match-1")
    bad = rows[0].__class__(**{**rows[0].__dict__, "actual_delivery": ""})
    with pytest.raises(ValueError, match="actual_delivery"):
        validate_rows([bad])
