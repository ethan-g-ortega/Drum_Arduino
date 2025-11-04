#!/usr/bin/env python3
import argparse, signal, sys
from mido import MidiFile
from config import MATCH_TOL_MS, GM
from chart import extract_chart
from judge import Judge
from scheduler import PlayScheduler
from midi_io import MidiInputLoop
from notifier import ArduinoNotifier, find_serial
from profiles import ALEsis_NITRO_PRO, build_active_map

STOP = False
def _on_sigint(signum, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGINT, _on_sigint)

note_to_kind = build_active_map(GM, ALEsis_NITRO_PRO)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Drum practice judge: play MIDI, listen to e-drum, score your hits.")
    ap.add_argument("midifile", help="Path to MIDI file")
    ap.add_argument("--input", required=False, help="MIDI input name (e-drum). If omitted, prints ports and exits.")
    ap.add_argument("--output", help="MIDI output name for guide notes (e.g., 'IAC Driver Bus 1')")
    ap.add_argument("--no-click", action="store_true", help="Disable metronome/count-in click")
    ap.add_argument("--tol", type=int, default=MATCH_TOL_MS, help=f"Match tolerance in ms (default {MATCH_TOL_MS})")
    ap.add_argument("--serial", help="Arduino serial (full path or substring, e.g. 'usbmodem', 'COM5')")
    ap.add_argument("--baud", type=int, default=115200, help="Arduino baud (default 115200)")
    args = ap.parse_args(argv)

    # MIDI file → expected chart
    mid = MidiFile(args.midifile)
    expected, tempo_map = extract_chart(mid)
    if not expected:
        print("No drum notes found on channel 10 in this MIDI.")
        return 1

    # Optional Arduino notifier
    notifier = None
    if args.serial:
        port = find_serial(args.serial)
        if not port:
            print("[WARN] Serial port not found. Proceeding without Arduino.")
        else:
            notifier = ArduinoNotifier(port, args.baud)

    # Judge
    judge = Judge(expected, tol_ms=args.tol, notifier=notifier)

    # Scheduler (click + guide notes)
    scheduler = PlayScheduler()
    start_at = scheduler.start(
        expected_hits=expected,
        tempo_map=tempo_map,
        play_click=(not args.no_click),
        midi_out_name=args.output,
        start_delay=2.0
    )

    # MIDI input loop
    if not args.input:
        print("Available MIDI inputs:")
        import mido
        for name in mido.get_input_names(): print("  -", name)
        print("\nAvailable MIDI outputs:")
        for name in mido.get_output_names(): print("  -", name)
        print("\nTip: re-run with --input 'Your E-Drum Port'")
        scheduler.stop(); scheduler.join()
        if notifier: notifier.close()
        return 0

    def on_note(t_song, note, vel):
        if STOP:
            raise KeyboardInterrupt
        judge.register_hit(t_song, note, vel, note_to_kind)

    midi_loop = MidiInputLoop(args.input)

    try:
        midi_loop.run(start_at, on_note)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop(); scheduler.join()
        stats = judge.finalize()
        if notifier: notifier.close()

        print("\n----- Results -----")
        for k, v in stats.items():
            if k == "avg_abs_dt_ms": print(f"{k:>18s}: {v:.1f}")
            else:                    print(f"{k:>18s}: {v}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
