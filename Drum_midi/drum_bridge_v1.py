#!/usr/bin/env python3
import time
import mido
import serial

SERIAL_PORT = "/dev/cu.usbmodem1201"
BAUD = 115200
VELMIN = 1
START = 0xAA

def pick_alesis_input():
    for name in mido.get_input_names():
        if "alesis" in name.lower():
            print("✅ MIDI input:", name)
            return mido.open_input(name)
    names = mido.get_input_names()
    print("⚠️ Alesis not found. Using default. Available:", names)
    return mido.open_input()  # first available

ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0)
time.sleep(1.0)  # let Arduino reset
port = pick_alesis_input()
print("🎵 Bridging MIDI → Arduino. Ctrl+C to quit.\n")

for msg in port:
    if msg.type == "note_on" and msg.velocity >= VELMIN:
        # packet: [START, note, velocity] (7-bit safe)
        ser.write(bytes([START, msg.note & 0x7F, msg.velocity & 0x7F]))
        print(f"sent note={msg.note} vel={msg.velocity}")  # uncomment to debug
