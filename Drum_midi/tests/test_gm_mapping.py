from config import GM, JUDGED_KINDS

def test_gm_includes_core_drums():
    assert GM[36] == "kick"
    assert GM[38] == "snare"
    assert GM[42] == "hihat_closed"
    assert GM[46] == "hihat_open"
    assert GM[49] == "crash"
    assert GM[51] == "ride"

def test_judged_kinds_consistency():
    # All GM values used must be in JUDGED_KINDS
    for note, kind in GM.items():
        assert isinstance(kind, str)
        assert kind in JUDGED_KINDS, f"{note} maps to {kind} not in JUDGED_KINDS"
