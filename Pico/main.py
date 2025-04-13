import sys
from machine import Pin, reset
import include.gyro as gyro_module
import include.button as button
import include.knob as knob
import json
import os

#Defining objects
LED: Pin = Pin("LED", Pin.OUT)
gyro = gyro_module.Gyro(16, 17)
b1 = button.Button(26)
k = knob.Knob(20, 19, 18)
serial_in = sys.stdin  # Use sys.stdin for reading from USB serial
serial_out = sys.stdout # Using sys.stdout for writing back to serial
#Setting attributes
gyro.set_function_mode(gyro_module.NDOF_MODE)
gyro.set_power_mode(gyro_module.POWER_NORMAL)

def file_exists(filepath) -> bool:
        """Returns if a file exists or not"""
        try:
            os.stat(filepath)
            return True
        except OSError:
            return False

def load_saved_angles() -> tuple:
    """Load the previously saved steering angle"""
    try:
        if file_exists("steering_angle.txt"):
            with open("steering_angle.txt", "r") as f:
                values : dict = json.loads(f.read().strip())
                return (values.get("yaw"), values.get("pitch"), values.get("roll"))
    except Exception as e:
        print(f"Error loading angle: {e}")
    return (0,0,0)  # Default angle if no saved value

def save_angles() -> None:
    """Save the current steering angle to persistent storage"""
    try:
        with open("steering_angle.txt", "w") as f:
            values = {}
            values["yaw"] = gyro.get_angles()[0]
            values["pitch"] = gyro.get_angles()[1]
            values["roll"] = gyro.get_angles()[2]
            f.write(json.dumps(values))
    except Exception as e:
        print(f"Error saving angle: {e}")

def setLED(boolOn) -> None:
    """Turns the LED on or off"""
    if(boolOn):
        LED.on()
    else:
        LED.off()

def read() -> dict:
    print("Looking")
    if serial_in in sys.stdin:  # Check if there is any data available in stdin (USB serial)
        print("Found something")
        incoming_data = serial_in.readline()  # Read the incoming data
        if incoming_data:
            try:
                message = json.loads(incoming_data.decode().strip())
                return message
            except json.JSONDecodeError:
                print("Decode error")
    else:
        print("Nothing")

def process_command(command : dict, state : dict) -> None:
    if command.get("command") == "poll":
        serial_out.write(json.dumps(state))
    else:
        print("No Command")

def loop() -> None:
    gyro.poll()
    b1.poll()
    k.poll()

    state = {}
    state['steer'] = gyro.get_angles()[0]
    state['button'] = b1.get_state()
    state['knob'] = {"count" : k.get_count(), "switch" : k.get_switch()}
    
    process_command(read(), state)
    save_angles()

if __name__ == "__main__":
    print("Starting")
    angles = load_saved_angles()
    gyro.tare_gyro(angles)
    loop()