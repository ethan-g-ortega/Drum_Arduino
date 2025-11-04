SR = 44100
MASTER_GAIN = 0.8

# Metronome / count-in
CLICK_HZ = 1000
CLICK_MS = 35
COUNT_IN_BARS = 1

# Grading windows (ms)
PERFECT_MS = 30
GREAT_MS   = 60
GOOD_MS    = 90
# Match window for accepting a hit at all (ms)
MATCH_TOL_MS = 120

# Default tempo if none in MIDI
DEFAULT_TEMPO_USPQN = 500_000  # 120 BPM

# GM drum mapping
GM = {
    35:"kick", 36:"kick",
    37:"snare", 38:"snare", 40:"snare",
    41:"tom_low", 43:"tom_low",
    45:"tom_mid", 47:"tom_mid",
    48:"tom_high", 50:"tom_high",
    42:"hihat_closed", 44:"hihat_pedal", 46:"hihat_open",
    49:"crash", 57:"crash",
    51:"ride", 59:"ride",
    53:"ride",          # ride bell → treat as ride
    54:"hihat_closed",  # tambourine → treat as closed hat (choose any judged kind you want)
    # 58 removed (it was incorrectly set to tom_low)
}


JUDGED_KINDS = {
    "kick","snare","hihat_closed","hihat_open","hihat_pedal",
    "tom_low","tom_mid","tom_high","crash","ride"
}

# For guide-note playback only: translate rare GM notes to something your module plays
OUTPUT_NOTE_MAP = {
    53: 51,  # ride bell -> ride cymbal
    54: 42,  # tambourine -> hihat closed
}
