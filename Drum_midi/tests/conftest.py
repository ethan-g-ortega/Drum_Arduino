import pytest
from mido import MidiFile, MidiTrack, MetaMessage, Message

# # tests/conftest.py
# import sys
# from pathlib import Path

# # Add project root to sys.path so `import chart`, `import config`, etc. work
# ROOT = Path(__file__).resolve().parents[1]
# if str(ROOT) not in sys.path:
#     sys.path.insert(0, str(ROOT))


@pytest.fixture
def simple_drum_midi(tmp_path):
    """
    Creates a tiny MIDI with tempo and a few drum hits on channel 10 (index 9).
    Returns path to file and a list of (t_beats, note, vel).
    """
    path = tmp_path / "mini.mid"
    mid = MidiFile(ticks_per_beat=480)

    track = MidiTrack()
    mid.tracks.append(track)

    # Tempo 120 BPM
    track.append(MetaMessage('set_tempo', tempo=500000, time=0))

    # events in beats -> convert to ticks (480 tpq)
    def beats_to_ticks(b): return int(b * mid.ticks_per_beat)

    events = [
        (1.0, 36, 100),  # kick
        (1.5, 38, 100),  # snare
        (2.0, 42, 100),  # hihat closed
        (2.5, 49, 100),  # crash
        (3.0, 39, 100),  # hand clap (unmapped in your GM set by default)
    ]

    last_ticks = 0
    for b, note, vel in events:
        t = beats_to_ticks(b)
        dt = t - last_ticks
        last_ticks = t
        track.append(Message('note_on', channel=9, note=note, velocity=vel, time=dt))
        # Note-off immediately (short)
        track.append(Message('note_off', channel=9, note=note, velocity=0, time=10))

    mid.save(str(path))
    return str(path), events
