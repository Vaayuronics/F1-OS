import RPi.GPIO as GPIO
import time

class Button:
    def __init__(self, gpio: int, name: str = "Button", debounce_ms: int = 50):
        """Creates a button object for Raspberry Pi GPIO.

        - Uses BCM pin numbering.
        - Configures the pin with an internal pull-up and treats the button as
          active-low (pressed when GPIO reads LOW) to match the Pico behavior.
        - Optional debounce in milliseconds to avoid bounce-triggered flips.
        """
        self.gpio_pin = gpio
        self.name = name
        self.button_down = False
        self.debounce_ms = max(0, int(debounce_ms))

        # Ensure GPIO mode is BCM (keep compatibility with Light class)
        if GPIO.getmode() is None or GPIO.getmode() != GPIO.BCM:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

        GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # track last stable read for debounce
        self._last_read_time = 0.0
        self._last_state = GPIO.input(self.gpio_pin)

    def poll(self) -> bool:
        """Read the GPIO pin and update internal pressed state.

        Returns True when the button is considered pressed (button_down).
        Preserves original semantics: pressed when value == 0 (active-low).
        """
        now = time.time() * 1000.0
        raw = GPIO.input(self.gpio_pin)

        # Debounce: only accept changes that persist longer than debounce_ms
        if raw != self._last_state:
            # state changed; start timing
            self._last_read_time = now
            self._last_state = raw
            return self.button_down

        if (now - self._last_read_time) < self.debounce_ms:
            # not stable yet
            return self.button_down

        # stable read, update button_down. active-low: 0 == pressed
        if raw == 0 and not self.button_down:
            self.button_down = True
        elif raw == 1 and self.button_down:
            self.button_down = False

        return self.button_down

    def get_state(self) -> bool:
        """Returns True if the button is down (pressed)."""
        return self.button_down

    def get_name(self):
        return self.name

    def set_name(self, name: str):
        self.name = name

    def cleanup(self):
        """Cleanup GPIO for this pin only."""
        try:
            GPIO.cleanup(self.gpio_pin)
        except Exception:
            # best-effort cleanup
            pass

    @classmethod
    def cleanup_all(cls):
        """Cleanup all GPIO pins."""
        GPIO.cleanup()