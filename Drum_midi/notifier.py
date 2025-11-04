import time
import serial, serial.tools.list_ports
from typing import Optional
from dh_types import Notifier as NotifierProtocol

def find_serial(name_like: Optional[str]) -> Optional[str]:
    if not name_like:
        return None
    s = name_like.lower()
    for p in serial.tools.list_ports.comports():
        combo = (p.device + " " + (p.description or "")).lower()
        if s in combo:
            return p.device
    if name_like.startswith("/dev/") or name_like.upper().startswith("COM"):
        return name_like
    return None

class ArduinoNotifier(NotifierProtocol):
    def __init__(self, port: Optional[str], baud: int = 115200):
        self.ser = None
        if port:
            try:
                self.ser = serial.Serial(port, baudrate=baud, timeout=0)
                time.sleep(2.0)
                print(f"Arduino connected on {port} @ {baud} baud")
            except Exception as e:
                print(f"[WARN] Could not open Arduino serial '{port}': {e}")

    def send_grade(self, grade: str):
        if not self.ser: return
        try:
            if grade == "Perfect": self.ser.write(b'G')
            elif grade in ("Great","Good"): self.ser.write(b'Y')
            elif grade == "Miss": self.ser.write(b'R')
        except Exception as e:
            print(f"[WARN] Serial write failed: {e}")

    def send_miss_pulse(self):
        if self.ser:
            try: self.ser.write(b'R')
            except: pass

    def close(self):
        if self.ser:
            try: self.ser.close()
            except: pass
