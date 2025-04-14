import transmission
from jerial import JSONSerialReader
import time

pico = JSONSerialReader("/dev/pico")
arduino = JSONSerialReader("/dev/arduino")

while True:
    pico.poll()
    arduino.poll()
    print(f"Pico: {pico.get_latest()}")
    print(f"Arduino: {arduino.get_latest()}")
    pico.send({"command" : "poll"})
    arduino.send({"command" : "poll"})