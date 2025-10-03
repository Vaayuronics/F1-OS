import RPi.GPIO as GPIO

class Light:

    def __init__(self, pin : int, name: str = "Light"):
        self.pin = pin
        self.name = name
        
        # Initialize GPIO only once for all Light instances
        if GPIO.getmode() is None or not GPIO.BCM:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False) #idc if channel in use cuh
            
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
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

    @classmethod
    def setup_gpio(cls):
        """Set up GPIO mode if not already set."""
        if GPIO.getmode() is None or not GPIO.BCM:
            GPIO.setmode(GPIO.BCM)

    @classmethod
    def cleanup_all(cls):
        """Clean up all GPIO pins at once.
        Dont use if you dont want floating states."""
        GPIO.cleanup()