from mido import MidiFile, MetaMessage
from config import DEFAULT_TEMPO_USPQN

def build_tempo_map(mid: MidiFile):
    acc = 0
    tempos = [(0, DEFAULT_TEMPO_USPQN)]
    if not mid.tracks:
        return tempos
    for msg in mid.tracks[0]:
        acc += msg.time
        if isinstance(msg, MetaMessage) and msg.type == "set_tempo":
            tempos.append((acc, msg.tempo))
    tempos.sort(key=lambda x: x[0])
    return tempos

def ticks_to_seconds(abs_ticks: int, tpq: int, tempo_map: list[tuple[int,int]]):
    secs = 0.0
    prev_tick = 0
    prev_tempo = tempo_map[0][1]
    for i in range(1, len(tempo_map)+1):
        boundary = tempo_map[i][0] if i < len(tempo_map) else abs_ticks
        if abs_ticks <= boundary:
            dt = abs_ticks - prev_tick
            secs += (dt / tpq) * (prev_tempo / 1_000_000.0)
            return secs
        dt = boundary - prev_tick
        secs += (dt / tpq) * (prev_tempo / 1_000_000.0)
        prev_tick = boundary
        if i < len(tempo_map):
            prev_tempo = tempo_map[i][1]
    return secs

def estimate_bpm(tempo_map: list[tuple[int,int]]) -> float:
    us = tempo_map[0][1] if tempo_map else DEFAULT_TEMPO_USPQN
    return 60_000_000.0 / us
