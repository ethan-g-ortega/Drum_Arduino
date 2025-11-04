import threading
from collections import defaultdict
from dh_types import ExpectedHit, PerHitScore, Notifier
from config import PERFECT_MS, GREAT_MS, GOOD_MS
from typing import Optional
from typing import Callable

def grade_for_dt(dt_ms: float) -> str:
    a = abs(dt_ms)
    if a <= PERFECT_MS: return "Perfect"
    if a <= GREAT_MS:   return "Great"
    if a <= GOOD_MS:    return "Good"
    return "Miss"

class Judge:
    def __init__(self, expected_hits: list[ExpectedHit], tol_ms: int, notifier: Optional[Notifier] = None):
        self.expected = expected_hits
        self.tol = tol_ms / 1000.0
        self.lock = threading.Lock()
        self.cursor = 0
        self.scores: list[PerHitScore] = []
        self.per_kind = defaultdict(list)
        self.combo = 0
        self.max_combo = 0
        self.total = 0
        self.misses = 0
        self.notifier = notifier

    def _register_silent_misses_until(self, t_actual: float):
        while self.cursor < len(self.expected) and self.expected[self.cursor].t < t_actual - self.tol:
            if not self.expected[self.cursor].matched:
                self.misses += 1
                self.combo = 0
                if self.notifier:
                    self.notifier.send_miss_pulse()
            self.cursor += 1

    def register_hit(self, t_actual: float, note: int, vel: int, note_to_kind: Callable[[int], Optional[str]]):
        kind = note_to_kind.get(note)
        if not kind:
            return
        with self.lock:
            self._register_silent_misses_until(t_actual)

            best_idx, best_dt = None, None
            lo = max(0, self.cursor - 20)
            hi = min(len(self.expected), self.cursor + 50)
            for i in range(lo, hi):
                e = self.expected[i]
                if e.matched or e.kind != kind:
                    continue
                dt = t_actual - e.t
                if abs(dt) <= self.tol:
                    if best_dt is None or abs(dt) < abs(best_dt):
                        best_idx, best_dt = i, dt

            if best_idx is None:
                self.combo = 0
                return

            e = self.expected[best_idx]
            e.matched = True
            dt_ms = best_dt * 1000.0
            grade = grade_for_dt(dt_ms)
            if grade == "Miss":
                self.combo = 0
                self.misses += 1
            else:
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)

            if self.notifier:
                self.notifier.send_grade(grade)

            result = PerHitScore(kind=e.kind, dt_ms=dt_ms, vel=vel, vel_target=e.vel, grade=grade)
            self.scores.append(result)
            self.per_kind[e.kind].append(result)
            self.total += 1
            print(f"[{e.kind:12s}] {grade:7s}  Δt={dt_ms:+6.1f} ms   vel={vel:3d} (target≈{e.vel:3d})   combo={self.combo}")

    def finalize(self):
        with self.lock:
            for i in range(self.cursor, len(self.expected)):
                if not self.expected[i].matched:
                    self.misses += 1
                    self.combo = 0
                    if self.notifier:
                        self.notifier.send_miss_pulse()

            acc = sum(1 for s in self.scores if s.grade in ("Perfect","Great","Good"))
            perfects = sum(1 for s in self.scores if s.grade == "Perfect")
            avg_abs_dt = (sum(abs(s.dt_ms) for s in self.scores)/len(self.scores)) if self.scores else 0.0
            return {
                "played": len(self.scores),
                "notes_in_chart": len(self.expected),
                "hits_landed": acc,
                "perfects": perfects,
                "misses": self.misses,
                "avg_abs_dt_ms": avg_abs_dt,
                "max_combo": self.max_combo,
            }
