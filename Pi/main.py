import transmission
from jerial import JSONSerialReader
import time

pico = JSONSerialReader("/dev/pico")
arduino = JSONSerialReader("/dev/arduino")

while True:
    pico.poll()
    arduino.poll()
    print(pico.get_latest())
    print(arduino.get_latest())
    
    cmd = input("Command: ")
    if(cmd == "poll pico"):
        pico.send({"command" : "poll"})
    if(cmd == "poll arduino"):
        arduino.send({"command" : "poll"})