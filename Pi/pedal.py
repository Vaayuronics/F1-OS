from machine import Pin, I2C

class Pedal:
    
    def __init__(self, adcPins : tuple):
        self.adc = Pin()