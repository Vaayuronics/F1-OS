from machine import Pin

class Button:
    def __init__(self, gpio : int):
        '''Creates a button object.\n
        Requires a gpio pin for the pull down.'''
        self.gpio = Pin(gpio, Pin.IN, Pin.PULL_UP)
        self.button_down = False

    def poll(self) -> bool:
        '''Wrapper for the update functions.\n
        This function should be included in the main while loop.\n
        Use get functions to access the values during compute.'''
        if self.gpio.value() == 0 and not self.button_down:
            self.button_down = True
        elif self.gpio.value() == 1 and self.button_down:
            self.button_down = False

        return self.button_down

    def get_state(self) -> bool:
        '''Returns true if the button is down.\n
        Returns false otherwise.'''
        return self.button_down