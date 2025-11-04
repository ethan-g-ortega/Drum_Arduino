from mido import MidiFile
from chart import extract_chart

def test_extract_chart_filters_to_channel10_and_sorts(simple_drum_midi):
    path, events = simple_drum_midi
    mid = MidiFile(path)
    exp, tempo_map = extract_chart(mid)
    # Should include mapped drums (kick/snare/hihat/crash), but not 39 by default
    kinds = [e.kind for e in exp]
    assert "kick" in kinds
    assert "snare" in kinds
    assert "hihat_closed" in kinds
    assert "crash" in kinds
    # Hand clap 39 not in your GM -> excluded
    assert all(e.note != 39 for e in exp)

    # Sorted in time
    times = [e.t for e in exp]
    assert times == sorted(times)
