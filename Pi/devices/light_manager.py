from devices.light import Light

class LightManager:

    def __init__(self, pins: list[int], names: list[str]):
        self.lights = [Light(pin, name) for pin, name in zip(pins, names)]

    def turn_on_all(self):
        for light in self.lights:
            light.turn_on()

    def turn_off_all(self):
        for light in self.lights:
            light.turn_off()

    def toggle_all(self):
        for light in self.lights:
            light.toggle()

    def turn_on(self, name: str):
        for light in self.lights:
            if light.get_name() == name:
                light.turn_on()
                return

    def turn_off(self, name: str):
        for light in self.lights:
            if light.get_name() == name:
                light.turn_off()
                return

    def cleanup(self):
        for light in self.lights:
            light.cleanup()