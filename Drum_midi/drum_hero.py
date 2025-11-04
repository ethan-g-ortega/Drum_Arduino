#!/usr/bin/env python3
import argparse
import time
import threading
from dataclasses import dataclass
from collections import defaultdict, deque
import math
import numpy as np
import simpleaudio as sa
import mido
from mido import MidiFile, MetaMessage

# --- NEW: clean Ctrl-C handling ---
import signal
STOP = threading.Event()
def _on_sigint(signum, frame):
    STOP.set()
signal.signal(signal.SIGINT, _on_sigint)

# --- NEW: Arduino serial support ---
import serial
import serial.tools.list_ports
from typing import Optional

def find_serial(name_like: Optional[str]) -> Optional[str]:
    """Return a device path by exact/partial match (e.g., 'usbmodem', 'COM5')."""
    if not name_like:
        return None
    s = name_like.lower()
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "")
        combo = (p.device + " " + desc).lower()
        if s in combo:
            return p.device
    # If user passed a full /dev/ path or COM port, just return it
    if name_like.startswith("/dev/") or name_like.upper().startswith("COM"):
        return name_like
    return None

class ArduinoNotifier:
    """
    Sends one byte per grade:
      'G' -> Perfect   (GREEN)
      'Y' -> Great/Good (YELLOW)
      'R' -> Miss      (RED)
    """
    def __init__(self, port: Optional[str], baud: int = 115200):
        self.ser = None
        if port:
            try:
                self.ser = serial.Serial(port, baudrate=baud, timeout=0)
                # Allow Arduino to reset on port open
                time.sleep(2.0)
                print(f"Arduino connected on {port} @ {baud} baud")
            except Exception as e:
                print(f"[WARN] Could not open Arduino serial '{port}': {e}")

    def send_grade(self, grade: str):
        if not self.ser:
            return
        try:
            if grade == "Perfect":
                self.ser.write(b'G')
            elif grade in ("Great", "Good"):
                self.ser.write(b'Y')
            elif grade == "Miss":
                self.ser.write(b'R')
        except Exception as e:
            print(f"[WARN] Serial write failed: {e}")

    def send_miss_pulse(self):
        if self.ser:
            try:
                self.ser.write(b'R')
            except:
                pass

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except:
                pass

# ---------------- Config ----------------
SR = 44100
MASTER_GAIN = 0.8
CLICK_HZ = 1000
CLICK_MS = 35
COUNT_IN_BARS = 1           # 1-bar count-in
MATCH_TOL_MS = 120          # window to accept a hit
PERFECT_MS = 30
GREAT_MS = 60
GOOD_MS = 90
MISS_MS = MATCH_TOL_MS
DEFAULT_TEMPO_USPQN = 500000  # 120 BPM

# Which drums to judge (GM mapping)
GM = {
    35:"kick", 36:"kick",
    37:"snare", 38:"snare", 40:"snare",
    41:"tom_low", 43:"tom_low",
    45:"tom_mid", 47:"tom_mid",
    48:"tom_high", 50:"tom_high",
    42:"hihat_closed", 44:"hihat_pedal", 46:"hihat_open",
    49:"crash", 57:"crash",
    51:"ride", 59:"ride",
}

JUDGED_KINDS = {
    "kick","snare","hihat_closed","hihat_open","hihat_pedal",
    "tom_low","tom_mid","tom_high","crash","ride"
}

# -------------- Audio helpers --------------
def sine_click(duration_ms=CLICK_MS, freq=CLICK_HZ):
    n = int(SR * (duration_ms/1000.0))
    t = np.arange(n)/SR
    wave = np.sin(2*np.pi*freq*t)
    env = np.linspace(1.0, 0.0, n)
    mono = (wave * env * 0.6).astype(np.float32)
    return mono

def play_mono(mono):
    stereo = np.stack([mono, mono], axis=1)
    audio = (stereo * 32767 * MASTER_GAIN).astype(np.int16)
    obj = sa.play_buffer(audio, 2, 2, SR)
    return obj

CLICK = sine_click()

# -------------- Timing / tempo map --------------
def build_tempo_map(mid: MidiFile):
    # returns list of (abs_ticks, tempo_us_per_qn)
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

def ticks_to_seconds(abs_ticks, tpq, tempo_map):
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

# -------------- Chart extraction --------------
@dataclass
class ExpectedHit:
    t: float        # seconds from song start
    kind: str       # kick/snare/etc
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

def extract_chart(mid: MidiFile):
    tpq = mid.ticks_per_beat
    tempo_map = build_tempo_map(mid)
    exp = []
    for track in mid.tracks:
        abs_ticks = 0
        for msg in track:
            abs_ticks += msg.time
            if msg.is_meta:
                continue
            if getattr(msg, "channel", None) != 9:  # GM drums on ch 10 -> index 9
                continue
            if msg.type == "note_on" and msg.velocity > 0:
                kind = GM.get(msg.note)
                if kind in JUDGED_KINDS:
                    t = ticks_to_seconds(abs_ticks, tpq, tempo_map)
                    exp.append(ExpectedHit(t=t, kind=kind, note=msg.note, vel=msg.velocity))
    exp.sort(key=lambda e: e.t)
    return exp, tempo_map

# -------------- Matching & Scoring --------------
def grade_for_dt(dt_ms):
    a = abs(dt_ms)
    if a <= PERFECT_MS: return "Perfect"
    if a <= GREAT_MS:   return "Great"
    if a <= GOOD_MS:    return "Good"
    if a <= MISS_MS:    return "Miss"
    return "Miss"

class Judge:
    def __init__(self, expected_hits, match_tol_ms=MATCH_TOL_MS, notifier: Optional[ArduinoNotifier]=None):
        self.expected = expected_hits
        self.tol = match_tol_ms/1000.0
        self.lock = threading.Lock()
        self.cursor = 0
        self.scores = []
        self.per_kind = defaultdict(list)
        self.combo = 0
        self.max_combo = 0
        self.total = 0
        self.misses = 0
        self.notifier = notifier

    def register_hit(self, t_actual, note, vel):
        kind = GM.get(note)
        if kind not in JUDGED_KINDS:
            return
        with self.lock:
            # advance cursor to nearby window (register silent misses)
            while self.cursor < len(self.expected) and self.expected[self.cursor].t < t_actual - self.tol:
                if not self.expected[self.cursor].matched:
                    self.misses += 1
                    self.combo = 0
                    if self.notifier:
                        self.notifier.send_miss_pulse()
                self.cursor += 1

            # search a small window around cursor for nearest matching kind
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
                # no match -> raw tap not on chart
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

            # notify Arduino
            if self.notifier:
                self.notifier.send_grade(grade)

            result = PerHitScore(kind=e.kind, dt_ms=dt_ms, vel=vel, vel_target=e.vel, grade=grade)
            self.scores.append(result)
            self.per_kind[e.kind].append(result)
            self.total += 1
            print(f"[{e.kind:12s}] {grade:7s}  Δt={dt_ms:+6.1f} ms   vel={vel:3d} (target≈{e.vel:3d})   combo={self.combo}")

    def finalize(self):
        with self.lock:
            # count remaining misses (and notify Arduino)
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

# -------------- Playback (click or MIDI out) --------------
def schedule_clicks(bpm, bars, start_time):
    sec_per_beat = 60.0 / bpm
    events = []
    total_beats = int(bars * 4)
    for i in range(total_beats):
        t = start_time + i * sec_per_beat
        events.append(("click", t))
    return events

def estimate_bpm(tempo_map):
    # use first tempo
    us = tempo_map[0][1] if tempo_map else DEFAULT_TEMPO_USPQN
    return 60_000_000.0 / us

def realtime_runner(expected_hits, tempo_map, play_click=True, midi_out_name=None, port_out=None, start_delay=2.0):
    bpm = estimate_bpm(tempo_map)
    start_at = time.monotonic() + start_delay

    # optional count-in clicks
    events = schedule_clicks(bpm, COUNT_IN_BARS, start_at)

    # optional MIDI out for drum notes (to IAC or module)
    if midi_out_name and port_out is None:
        try:
            port_out = mido.open_output(midi_out_name)
            print(f"Sending MIDI to: {midi_out_name}")
        except Exception as e:
            print(f"Could not open MIDI out '{midi_out_name}': {e}")
            port_out = None

    # add note events (as MIDI out times)
    for e in expected_hits:
        t = start_at + e.t
        events.append(("note", t, e.note, e.vel))

    events.sort(key=lambda x: x[1])

    def worker():
        for ev in events:
            if STOP.is_set():
                break
            now = time.monotonic()
            delay = ev[1] - now
            if delay > 0:
                # sleep in small chunks so Ctrl-C remains responsive
                end_at = now + delay
                while not STOP.is_set() and time.monotonic() < end_at:
                    time.sleep(min(0.01, end_at - time.monotonic()))
            if STOP.is_set():
                break
            if ev[0] == "click" and play_click:
                play_mono(CLICK)
            elif ev[0] == "note" and port_out is not None:
                # send a short note for guidance (channel 10)
                port_out.send(mido.Message('note_on', channel=9, note=ev[2], velocity=ev[3]))
                port_out.send(mido.Message('note_off', channel=9, note=ev[2], velocity=0, time=0))
        if port_out:
            try: port_out.close()
            except: pass

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    return start_at, th

# -------------- MIDI input listener --------------
def input_loop(judge: Judge, input_name: str, start_at: float):
    with mido.open_input(input_name) as port:
        print(f"Listening to: {input_name}  (press Ctrl-C to stop)")
        while not STOP.is_set():
            for msg in port.iter_pending():
                if msg.type == 'note_on' and msg.velocity > 0:
                    # use arrival time as performance time
                    t_now = time.monotonic()
                    t_song = t_now - start_at
                    judge.register_hit(t_song, msg.note, msg.velocity)
            time.sleep(0.001)

# -------------- Main --------------
def main():
    ap = argparse.ArgumentParser(description="Drum practice judge: play MIDI, listen to e-drum, score your hits.")
    ap.add_argument("midifile", help="Path to MIDI file")
    ap.add_argument("--input", help="MIDI input name (your e-drum). If omitted, prints available ports and exits.")
    ap.add_argument("--output", help="MIDI output name (e.g., IAC Driver or your module) to play guide notes")
    ap.add_argument("--no-click", action="store_true", help="Disable metronome / count-in click")
    ap.add_argument("--tol", type=int, default=MATCH_TOL_MS, help="Match tolerance in ms (default 120)")
    # --- NEW: serial args ---
    ap.add_argument("--serial", help="Arduino serial device or substring (e.g., '/dev/tty.usbmodem1101', 'usbserial', or 'COM5')")
    ap.add_argument("--baud", type=int, default=115200, help="Arduino baud rate (default 115200)")
    args = ap.parse_args()

    # List ports when not specified
    if not args.input:
        print("Available MIDI inputs:")
        for name in mido.get_input_names():
            print("  -", name)
        print("\nAvailable MIDI outputs:")
        for name in mido.get_output_names():
            print("  -", name)
        print("\nAvailable Serial ports:")
        for p in serial.tools.list_ports.comports():
            print("  -", p.device, "|", p.description)
        print("\nRe-run with --input 'Your E-Drum Port' [--output 'IAC Driver Bus 1'] [--serial usbmodem].")
        return

    # Resolve serial / open Arduino
    serial_port = find_serial(args.serial) if args.serial else None
    notifier = ArduinoNotifier(serial_port, args.baud)

    mid = MidiFile(args.midifile)
    expected, tempo_map = extract_chart(mid)
    if not expected:
        print("No drum notes found on channel 10 in this MIDI.")
        if notifier: notifier.close()
        return

    judge = Judge(expected, match_tol_ms=args.tol, notifier=notifier)

    # Start playback scheduling
    start_at, play_thread = realtime_runner(
        expected, tempo_map,
        play_click=(not args.no_click),
        midi_out_name=args.output
    )

    # Run input loop (blocking)
    try:
        input_loop(judge, args.input, start_at)
    except KeyboardInterrupt:
        pass
    finally:
        stats = judge.finalize()
        if notifier: notifier.close()
        print("\n----- Results -----")
        for k, v in stats.items():
            if k == "avg_abs_dt_ms":
                print(f"{k:>18s}: {v:.1f}")
            else:
                print(f"{k:>18s}: {v}")

if __name__ == "__main__":
    main()
