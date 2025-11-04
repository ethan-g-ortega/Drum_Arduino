from mido import MidiFile
from dh_types import ExpectedHit
from config import GM, JUDGED_KINDS
from midi_time import build_tempo_map, ticks_to_seconds

def extract_chart(mid: MidiFile) -> tuple[list[ExpectedHit], list[tuple[int,int]]]:
    tpq = mid.ticks_per_beat
    tempo_map = build_tempo_map(mid)
    exp: list[ExpectedHit] = []

    for track in mid.tracks:
        abs_ticks = 0
        for msg in track:
            abs_ticks += msg.time
            if msg.is_meta: 
                continue
            if getattr(msg, "channel", None) != 9:  # GM drums = ch 10 -> index 9
                continue
            if msg.type == "note_on" and msg.velocity > 0:
                kind = GM.get(msg.note)
                if kind in JUDGED_KINDS:
                    t = ticks_to_seconds(abs_ticks, tpq, tempo_map)
                    exp.append(ExpectedHit(t=t, kind=kind, note=msg.note, vel=msg.velocity))
    exp.sort(key=lambda e: e.t)
    return exp, tempo_map
