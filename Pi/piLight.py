import RPi.GPIO as GPIO
import sys

# Set the GPIO mode (BCM uses the GPIO numbers, not pin numbers)
GPIO.setmode(GPIO.BCM)

# Set up the LED pin (GPIO 17)
led_pin = 17
GPIO.setup(led_pin, GPIO.OUT)

def main():
    # Check if we have the correct number of arguments
    if len(sys.argv) != 2:
        print("Usage: pylight [0|1]")
        print("  0: Turn LED off")
        print("  1: Turn LED on")
        sys.exit(1)
    
    # Get the command (0 or 1)
    command = sys.argv[1]
    
    if command == "1" or command.lower() == "on":
        # Turn on the LED
        GPIO.output(led_pin, GPIO.HIGH)
        print("LED turned ON")
    elif command == "0" or command.lower() == "off":
        # Turn off the LED
        GPIO.output(led_pin, GPIO.LOW)
        print("LED turned OFF")
        GPIO.cleanup()
    elif command == "help":
        print("1/on : Turn on RGB light\n0/off : Turn off RGB light")
    else:
        print("Invalid command. Use 0/off to turn off or 1/on to turn on.")
        sys.exit(1)

if __name__ == "__main__":
    main()