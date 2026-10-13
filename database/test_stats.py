from database.stats import competition_key


def test_competition_key_is_stable_and_explicit():
    assert competition_key("Indian Premier League") == "competition:indian-premier-league"
    assert competition_key("International T20") == "competition:international-t20"
    assert competition_key(None) is None
