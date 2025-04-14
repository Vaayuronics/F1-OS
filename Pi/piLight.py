import RPi.GPIO as GPIO
import time

# Set the GPIO mode (BCM uses the GPIO numbers, not pin numbers)
GPIO.setmode(GPIO.BCM)

# Set up the LED pin (GPIO 17)
led_pin = 17
GPIO.setup(led_pin, GPIO.OUT)

# Turn on the LED
GPIO.output(led_pin, GPIO.HIGH)

time.sleep(10)

# Always clean up at the end of your script
GPIO.cleanup()
