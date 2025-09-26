from devices.light import Light

class LightManager:

    def __init__(self, pins: list[int] = None, names: list[str] = None):
        self.lights = [Light(pin, name) for pin, name in zip(pins, names)] if pins and names else []

    def get_lights(self):
        return self.lights
    
    def get_names(self):
        return [light.get_name() for light in self.lights]
    
    def add_light(self, pin: int, name: str):
        self.lights.append(Light(pin, name))

    def add_at(self, pin: int, name: str, index: int):
        if 0 <= index <= len(self.lights):
            self.lights.insert(index, Light(pin, name))
        elif index == len(self.lights):
            self.lights.append(Light(pin, name))

    def turn_on_all(self):
        for light in self.lights:
            light.turn_on()

    def turn_off_all(self):
        for light in self.lights:
            light.turn_off()

    def toggle_all(self):
        for light in self.lights:
            light.toggle()

    def turn_on(self, name: str = None, index: int = None):
        if name:
            for light in self.lights:
                if light.get_name() == name:
                    light.turn_on()
                    return
        if index is not None:
            if 0 <= index < len(self.lights):
                self.lights[index].turn_on()
                return

    def turn_off(self, name: str):
        for light in self.lights:
            if light.get_name() == name:
                light.turn_off()
                return

    def cleanup(self):
        for light in self.lights:
            light.cleanup()
        # Also clean up all GPIO at once
        Light.cleanup_all()