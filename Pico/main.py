import time
import sys
import include.fonts.font5x8 as font
from machine import Pin, I2C, reset

LED: Pin = Pin("LED", Pin.OUT)
#pico.setFunctionMode(NDOF_MODE)
#pico.setPowerMode(POWER_NORMAL)
OLED_STEP_HEIGHT = 8 #How much space each character takes height wise
OLED_STEP_WIDTH = 8

def setLED(boolOn) -> None:
    """Turns the LED on or off"""
    if(boolOn):
        LED.on()
    else:
        LED.off()

setLED(True)