from machine import Pin

class Knob:
    def __init__(self, sw : int, dt : int, clk : int):
        '''Creates a Rotary Encoder (Knob) object.\n
        Requires the sw pin : knob button.\n
        Requires the dt pin : direction.\n
        Requires the clk pin : change pin.'''
        self.clk = Pin(18, Pin.IN, Pin.PULL_UP)
        self.dt = Pin(19, Pin.IN, Pin.PULL_UP)
        self.sw = Pin(20, Pin.IN, Pin.PULL_UP)
        self.counter = 0
        self.last_clk = self.clk.value()
        self.button_down = False

    def check_encoder(self) -> int:
        '''Checks the clk and dt pins to increment the encoder.\n
        This function is wrapped by self.poll().\n
        Returns the current encoder count.'''
        current_clk = self.clk.value()
        current_dt = self.dt.value()

        if current_clk != self.last_clk:
            if current_dt != current_clk:
                counter += 1
            else:
                counter -= 1

        self.last_clk = current_clk

        return self.counter

    def check_switch(self) -> bool:
        '''Checks the sw pin to determine button position.\n
        This function is wrapped by self.poll().\n
        Returns if the button is pressed.'''
        if self.sw.value() == 0 and not self.button_down:
            self.button_down = True
        elif self.sw.value() == 1 and self.button_down:
            self.button_down = False

        return self.button_down

    def poll(self) -> None:
        '''Wrapper for the check functions.\n
        This function should be included in the main while loop.'''
        self.check_encoder()
        self.check_switch()

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
        Does not check encoder state.'''
        return self.button_down