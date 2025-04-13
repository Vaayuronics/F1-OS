import sys
from machine import Pin, reset
import include.gyro as gyro_module
import include.button as button
import include.knob as knob
import json
import os
import select  # Import the select module

#Defining objects
LED: Pin = Pin("LED", Pin.OUT)
gyro = gyro_module.Gyro(16, 17)
b1 = button.Button(26)
k = knob.Knob(20, 19, 18)
serial_in = sys.stdin  # Use sys.stdin for reading from USB serial
serial_out = sys.stdout # Using sys.stdout for writing back to serial

# Create a poll object for checking stdin
poll_obj = select.poll()
poll_obj.register(serial_in, select.POLLIN)

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

def read() -> dict | None:
    """Reads JSON data from serial input if available, non-blocking."""
    # Check if data is available with a timeout of 0 (non-blocking)
    poll_results = poll_obj.poll(0) 
    if poll_results:
        # Check if the event is for stdin and is a read event
        if poll_results[0][1] & select.POLLIN:
            print("Found something")
            incoming_data = serial_in.readline()
            if incoming_data:
                try:
                    # Strip whitespace and attempt to decode JSON
                    message = json.loads(incoming_data.strip())
                    return message
                except json.JSONDecodeError:
                    print("Decode error")
                except Exception as e:
                    print(f"Error reading/decoding: {e}")
    # No data available or error occurred
    return None

def process_command(command : dict | None, state : dict) -> None:
    """Processes a command dictionary."""
    if command is None: # Handle case where no command was read
        return 
        
    if command.get("command") == "poll":
        # Use sys.stdout.write for MicroPython serial output
        serial_out.write(json.dumps(state) + '\n') 
    elif command.get("command") == "save":
        save_angles()
    else:
        print("Unknown or no command")

def loop() -> None:
    gyro.poll()
    b1.poll()
    k.poll()

    state = {}
    state['steer'] = gyro.get_angles()[0]
    state['button'] = b1.get_state()
    state['knob'] = {"count" : k.get_count(), "switch" : k.get_switch()}
    
    command = read() # Read potential command
    process_command(command, state) # Process command if received

if __name__ == "__main__":
    print("Starting")
    angles = load_saved_angles()
    gyro.tare_gyro(angles)
    while True:
        loop()