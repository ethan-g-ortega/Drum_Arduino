import numpy as np
import simpleaudio as sa
from config import SR, MASTER_GAIN, CLICK_HZ, CLICK_MS

def sine_click(duration_ms=CLICK_MS, freq=CLICK_HZ):
    n = int(SR * (duration_ms/1000.0))
    t = np.arange(n)/SR
    wave = np.sin(2*np.pi*freq*t)
    env = np.linspace(1.0, 0.0, n)
    mono = (wave * env * 0.6).astype(np.float32)
    return mono

def play_mono(mono: np.ndarray):
    stereo = np.stack([mono, mono], axis=1)
    audio = (stereo * 32767 * MASTER_GAIN).astype(np.int16)
    return sa.play_buffer(audio, 2, 2, SR)

CLICK = sine_click()
