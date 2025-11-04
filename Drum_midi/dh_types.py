from dataclasses import dataclass
from typing import Protocol

@dataclass
class ExpectedHit:
    t: float       # seconds from song start
    kind: str
    note: int
    vel: int
    matched: bool = False

@dataclass
class PerHitScore:
    kind: str
    dt_ms: float
    vel: int
    vel_target: int
    grade: str

class Notifier(Protocol):
    def send_grade(self, grade: str) -> None: ...
    def send_miss_pulse(self) -> None: ...
    def close(self) -> None: ...
