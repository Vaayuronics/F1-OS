from machine import Pin
import time

class Button:
    def __init__(self, gpio : int, name : str = "Button", debounce_ms : int = 50):
        '''Creates a button object.\n
        Requires a gpio pin for the pull down.\n
        Optional debounce_ms parameter sets debounce time in milliseconds (default 50ms).'''
        self.gpio = Pin(gpio, Pin.IN, Pin.PULL_UP)
        self.button_down = False
        self.name = name
        self.debounce_ms = max(0, int(debounce_ms))
        self._last_read_time = 0.0
        self._last_state = self.gpio.value()
        self._prev_button_down = False  # Track previous state for edge detection

    def poll(self) -> bool:
        '''Wrapper for the update functions.\n
        This function should be included in the main while loop.\n
        Use get functions to access the values during compute.'''
        now = time.ticks_ms()
        raw = self.gpio.value()

        # Debounce: only accept changes that persist longer than debounce_ms
        if raw != self._last_state:
            # state changed; start timing
            self._last_read_time = now
            self._last_state = raw
            return self.button_down

        if time.ticks_diff(now, self._last_read_time) < self.debounce_ms:
            # not stable yet
            return self.button_down

        # stable read, update button_down. active-low: 0 == pressed
        self._prev_button_down = self.button_down
        if raw == 0 and not self.button_down:
            self.button_down = True
        elif raw == 1 and self.button_down:
            self.button_down = False

        return (self.button_down, self.was_pressed())

    def get_state(self) -> bool:
        '''Returns true if the button is down.\n
        Returns false otherwise.'''
        return self.button_down
    
    def was_pressed(self) -> bool:
        '''Returns True only on the moment the button was pressed (rising edge).\n
        This detects the transition from not-pressed to pressed.\n
        Call poll() before this to get current state.'''
        return self.button_down and not self._prev_button_down
    
    def was_released(self) -> bool:
        '''Returns True only on the moment the button was released (falling edge).\n
        This detects the transition from pressed to not-pressed.\n
        Call poll() before this to get current state.'''
        return not self.button_down and self._prev_button_down

    def get_name(self):
        '''Returns the name of the button.'''
        return self.name
    
    def set_name(self, name : str):
        '''Sets the name of the button.'''
        self.name = name