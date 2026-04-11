"""cast_vote + tests share CANONICAL_VOTES via shared.vote_vocabulary."""

from shared.vote_vocabulary import CANONICAL_VOTES, normalize_specialist_vote


def test_normalize_maps_legacy_buy_hold():
    assert normalize_specialist_vote("buy") == "AUTHENTICATE"
    assert normalize_specialist_vote("HOLD") == "VERIFY_FURTHER"


def test_normalize_accepts_canonical():
    for v in CANONICAL_VOTES:
        assert normalize_specialist_vote(v) == v
        assert normalize_specialist_vote(v.lower()) == v


def test_normalize_unknown_to_verify_further():
    assert normalize_specialist_vote("nonsense") == "VERIFY_FURTHER"
    assert normalize_specialist_vote("") == "VERIFY_FURTHER"
