import time
import sys
from machine import Pin, reset
import gyro
import button
import knob

LED: Pin = Pin("LED", Pin.OUT)

#pico.setFunctionMode(NDOF_MODE)
#pico.setPowerMode(POWER_NORMAL)

def setLED(boolOn) -> None:
    """Turns the LED on or off"""
    if(boolOn):
        LED.on()
    else:
        LED.off()

setLED(True)