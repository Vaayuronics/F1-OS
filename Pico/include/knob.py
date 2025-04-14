from machine import Pin

class Knob:
    def __init__(self, dt : int, clk : int, sw : int = -1):
        '''Creates a Rotary Encoder (Knob) object.\n
        Requires the dt pin : direction.\n
        Requires the clk pin : change pin.\n
        Optional sw pin : knob button.'''
        self.clk = Pin(clk, Pin.IN, Pin.PULL_UP)
        self.dt = Pin(dt, Pin.IN, Pin.PULL_UP)
        if(sw == -1):
            self.sw = None
        else:
            self.sw = Pin(sw, Pin.IN, Pin.PULL_UP)
        self.counter = 0
        self.last_clk = self.clk.value()
        self.button_down = False

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
        elif self.sw.value() == 0 and not self.button_down:
            self.button_down = True
        elif self.sw.value() == 1 and self.button_down:
            self.button_down = False

        return self.button_down

    def poll(self) -> None:
        '''Wrapper for the update functions.\n
        This function should be included in the main while loop.\n
        Use get functions to access the values during compute.'''
        self.update_encoder()
        self.update_switch()

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