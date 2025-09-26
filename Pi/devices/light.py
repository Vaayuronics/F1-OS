import RPi.GPIO as GPIO

class Light:
    _gpio_initialized = False

    def __init__(self, pin : int, name: str = "Light"):
        self.pin = pin
        self.name = name
        
        # Initialize GPIO only once for all Light instances
        if not Light._gpio_initialized:
            GPIO.setmode(GPIO.BCM)
            Light._gpio_initialized = True
            
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
        self.state = False

    def turn_on(self):
        try:
            GPIO.output(self.pin, GPIO.HIGH)
            self.state = True
            print(f"Light '{self.name}' on pin {self.pin} turned ON")
        except Exception as e:
            print(f"Error turning on light '{self.name}' on pin {self.pin}: {e}")

    def turn_off(self):
        try:
            GPIO.output(self.pin, GPIO.LOW)
            self.state = False
            print(f"Light '{self.name}' on pin {self.pin} turned OFF")

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
    def cleanup_all(cls):
        """Clean up all GPIO pins at once"""
        GPIO.cleanup()
        cls._gpio_initialized = False