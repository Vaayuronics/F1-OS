import RPi.GPIO as GPIO

class Light:

    def __init__(self, pin : int, name: str = "Light"):
        self.pin = pin
        self.name = name
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.state = False

    def turn_on(self):
        GPIO.output(self.pin, GPIO.HIGH)
        self.state = True

    def turn_off(self):
        GPIO.output(self.pin, GPIO.LOW)
        self.state = False

    def toggle(self):
        if self.state:
            self.turn_off()
        else:
            self.turn_on()

    def get_name(self):
        return self.name
    
    def set_name(self, name: str):
        self.name = name

    def get_state(self):
        return self.state

    def cleanup(self):
        GPIO.cleanup(self.pin)