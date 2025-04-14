from machine import Pin
import time

led = Pin(17, Pin.OUT)

led.value(1)