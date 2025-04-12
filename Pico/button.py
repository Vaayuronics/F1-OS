from mahcine import Pin

class Button:
    def __init__(self, gpio : int):
        '''Creates a button object.\n
        Requires a gpio pin for the pull down.'''
        self.gpio = Pin(16, Pin.IN, Pin.PULL_UP)
        self.button_down = False

    def poll(self) -> bool:
        '''Checks the gpio pin to determine button position.\n
        Returns if the button is pressed.'''
        if self.gpio.value() == 0 and not self.button_down:
            self.button_down = True
        elif self.gpio.value() == 1 and self.button_down:
            self.button_down = False

        return self.button_down
