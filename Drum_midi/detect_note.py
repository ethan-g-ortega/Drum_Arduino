from mido import MidiFile
path = "/Users/ethanortega/Drum_Arduino/Drum_midi/The Strokes-You Only Live Once-10-28-2025.mid"
mid = MidiFile(path)

notes = set()
for track in mid.tracks:
    for msg in track:
        if msg.type == "note_on" and msg.velocity > 0 and msg.channel == 9:  # drum channel
            notes.add(msg.note)

print("Drum notes found:", sorted(notes))
