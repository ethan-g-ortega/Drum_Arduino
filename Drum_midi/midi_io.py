import time
import mido

class MidiInputLoop:
    def __init__(self, input_name: str):
        self.input_name = input_name

    def run(self, start_at: float, on_note):
        # on_note(t_song_seconds, note, velocity)
        with mido.open_input(self.input_name) as port:
            print(f"Listening to: {self.input_name}  (press Ctrl-C to stop)")
            while True:
                for msg in port.iter_pending():
                    if msg.type == 'note_on' and msg.velocity > 0:
                        t_song = time.monotonic() - start_at
                        on_note(t_song, msg.note, msg.velocity)
                time.sleep(0.001)
