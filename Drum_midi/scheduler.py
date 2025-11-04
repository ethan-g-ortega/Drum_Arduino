import time, threading
import mido
from audio import CLICK, play_mono
from midi_time import estimate_bpm
from config import COUNT_IN_BARS

def schedule_clicks(bpm: float, bars: int, start_time: float):
    sec_per_beat = 60.0 / bpm
    events = []
    total_beats = int(bars * 4)
    for i in range(total_beats):
        t = start_time + i * sec_per_beat
        events.append(("click", t))
    return events

class PlayScheduler:
    def __init__(self):
        self._stop = False
        self._thread: threading.Thread|None = None

    def stop(self):
        self._stop = True

    def start(self, expected_hits, tempo_map, play_click=True, midi_out_name=None, start_delay=2.0):
        bpm = estimate_bpm(tempo_map)
        start_at = time.monotonic() + start_delay
        events = schedule_clicks(bpm, COUNT_IN_BARS, start_at)

        port_out = None
        if midi_out_name:
            try:
                port_out = mido.open_output(midi_out_name)
                print(f"Sending MIDI to: {midi_out_name}")
            except Exception as e:
                print(f"Could not open MIDI out '{midi_out_name}': {e}")

        for e in expected_hits:
            t = start_at + e.t
            events.append(("note", t, e.note, e.vel))
        events.sort(key=lambda x: x[1])

        def worker():
            nonlocal port_out
            for ev in events:
                if self._stop: break
                now = time.monotonic()
                delay = ev[1] - now
                if delay > 0:
                    end_at = now + delay
                    while not self._stop and time.monotonic() < end_at:
                        time.sleep(min(0.01, end_at - time.monotonic()))
                if self._stop: break
                if ev[0] == "click" and play_click:
                    play_mono(CLICK)
                elif ev[0] == "note" and port_out is not None:
                    port_out.send(mido.Message('note_on', channel=9, note=ev[2], velocity=ev[3]))
                    port_out.send(mido.Message('note_off', channel=9, note=ev[2], velocity=0, time=0))
            if port_out:
                try: port_out.close()
                except: pass

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
        return start_at

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)
