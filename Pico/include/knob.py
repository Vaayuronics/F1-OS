from machine import Pin
import time

class Knob:
    def __init__(self, dt : int, clk : int, sw : int = -1, name : str = "Knob", debounce_ms : int = 50, default_count : int = 0):
        '''Creates a Rotary Encoder (Knob) object.\n
        Requires the dt pin : direction.\n
        Requires the clk pin : change pin.\n
        Optional sw pin : knob button.\n
        Optional debounce_ms parameter sets debounce time for the switch in milliseconds (default 50ms).'''
        self.clk = Pin(clk, Pin.IN, Pin.PULL_UP)
        self.dt = Pin(dt, Pin.IN, Pin.PULL_UP)
        if(sw == -1):
            self.sw = None
        else:
            self.sw = Pin(sw, Pin.IN, Pin.PULL_UP)
        self.counter = default_count
        self.last_clk = self.clk.value()
        self.button_down = False
        self.name = name
        self.debounce_ms = max(0, int(debounce_ms))
        self._last_read_time = 0.0
        self._last_sw_state = self.sw.value() if self.sw else 1
        self._prev_button_down = False  # Track previous state for edge detection
        self.button_pressed = False  # Persistent pressed state for external use

    def update_encoder(self) -> int:
        '''Checks the clk and dt pins to increment the encoder.\n
        This function is wrapped by self.poll().\n
        Returns the current encoder count.'''
        current_clk = self.clk.value()
        current_dt = self.dt.value()

        if current_clk != self.last_clk:
            if current_dt != current_clk:
                self.counter += 1
            else:
                self.counter -= 1

        self.last_clk = current_clk

        return self.counter

    def update_switch(self) -> bool:
        '''Checks the sw pin to determine button position.\n
        This function is wrapped by self.poll().\n
        Returns if the button is pressed.'''
        if self.sw == None:
            return False
        
        now = time.ticks_ms()
        raw = self.sw.value()

        # Debounce: only accept changes that persist longer than debounce_ms
        if raw != self._last_sw_state:
            # state changed; start timing
            self._last_read_time = now
            self._last_sw_state = raw
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

        if self.switch_was_pressed():
            self.button_pressed = True

        return self.button_down

    def poll(self) -> dict:
        '''Wrapper for the update functions.\n
        This function should be included in the main while loop.\n
        Returns a dict with Count, Down state, and Pressed state.'''
        self.update_encoder()
        self.update_switch()
        return {
            "Count": self.counter,
            "Down": self.button_down,
            "Pressed": self.switch_was_pressed(),
            "Press State": self.button_pressed
        }

    def get_count(self) -> int:
        '''Returns the current encoder count.\n
        Does not check encoder state.'''
        return self.counter
    
    def set_count(self, val : int = 0) -> int:
        '''Sets the counter to be the given parameter.\n
        Defaults to zero if no parameter passed in.\n
        Returns the previous parameter.'''
        prev = self.counter
        self.counter = val
        return prev
    
    def get_switch(self) -> bool:
        '''Gets the current state of the button (sw pin).\n
        Returns True if the button is in the down or pressed position.\n
        Returns False if the button is in the up or unpressed position.\n
        Does not update encoder state.'''
        return self.button_down
    
    def switch_was_pressed(self) -> bool:
        '''Returns True only on the moment the switch was pressed (rising edge).\n
        This detects the transition from not-pressed to pressed.\n
        Call poll() before this to get current state.'''
        return self.button_down and not self._prev_button_down
    
    def clear_pressed(self) -> None:
        '''Clears the pressed state.'''
        self.button_pressed = False

    def get_press_state(self) -> bool:
        '''Returns True if the button has been pressed since last cleared.\n
        Call clear_pressed() to reset this state.'''
        return self.button_pressed
    
    def switch_was_released(self) -> bool:
        '''Returns True only on the moment the switch was released (falling edge).\n
        This detects the transition from pressed to not-pressed.\n
        Call poll() before this to get current state.'''
        return not self.button_down and self._prev_button_down
    
    def get_name(self) -> str:
        '''Returns the name of the knob.'''
        return self.name
    
    def set_name(self, name : str) -> None:
        '''Sets the name of the knob.'''
        self.name = name