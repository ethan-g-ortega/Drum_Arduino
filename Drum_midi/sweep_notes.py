import time, mido
out = mido.open_output("Alesis Nitro Pro")
for note in range(52, 60):   # common GM drum range
    print("Sending note", note)
    out.send(mido.Message('note_on', channel=9, note=note, velocity=100))
    time.sleep(0.15)
    out.send(mido.Message('note_off', channel=9, note=note, velocity=0))
    time.sleep(0.1)
out.close()
