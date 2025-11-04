import math
from dh_types import ExpectedHit
from judge import Judge, grade_for_dt
from config import GM

def test_grade_boundaries():
    # exact edge cases
    assert grade_for_dt(0) == "Perfect"
    assert grade_for_dt(30) == "Perfect"
    assert grade_for_dt(31) == "Great"
    assert grade_for_dt(60) == "Great"
    assert grade_for_dt(61) == "Good"
    assert grade_for_dt(90) == "Good"
    assert grade_for_dt(91) == "Miss"

def test_judge_ignores_unmapped_notes():
    # one expected snare at t=1.0s
    exp = [ExpectedHit(t=1.0, kind="snare", note=38, vel=100)]
    j = Judge(exp, tol_ms=120)

    # send an unmapped note (e.g., 39 if not translated)
    j.register_hit(t_actual=1.0, note=39, vel=100, note_to_kind=lambda n: GM.get(n))
    stats = j.finalize()
    # no played hits, 1 miss due to expected not matched
    assert stats["played"] == 0
    assert stats["misses"] == 1

def test_judge_matches_within_tolerance_and_grades():
    exp = [ExpectedHit(t=1.0, kind="snare", note=38, vel=100)]
    j = Judge(exp, tol_ms=120)
    # hit 20ms late -> Perfect
    j.register_hit(t_actual=1.020, note=38, vel=90, note_to_kind=lambda n: GM.get(n))
    stats = j.finalize()
    assert stats["played"] == 1
    assert stats["misses"] == 0
    assert stats["perfects"] == 1