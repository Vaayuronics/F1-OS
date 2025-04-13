import sys
from machine import Pin, reset, UART
import include.gyro as gyro_module
import include.button as button
import include.knob as knob
import json
import os
import time  # For delays
import select

# Debug LED to show we're running
LED = Pin("LED", Pin.OUT)
LED.on()  # Turn on immediately to show we're starting

# Defining objects
gyro = gyro_module.Gyro(16, 17)
b1 = button.Button(26)
k = knob.Knob(19, 18, 20)  # dt, clk, sw
poller = select.poll()
last_led_toggle = 0

# Setting attributes
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
    if file_exists("steering_angle.txt"):
        with open("steering_angle.txt", "r") as f:
            values = json.loads(f.read().strip())
            return (values.get("yaw"), values.get("pitch"), values.get("roll"))
    return (0,0,0)  # Default angle if no saved value

def save_angles() -> dict:
    """Save the current steering angle to persistent storage"""
    values = {
        "yaw": gyro.get_angles()[0],
        "pitch": gyro.get_angles()[1],
        "roll": gyro.get_angles()[2]
    }
    with open("steering_angle.txt", "w") as f:
        f.write(json.dumps(values))
    return values

def read() -> dict:
    # Non-blocking check for commands
    if poller.poll(0):  # 0 timeout = non-blocking
        try:
            line = sys.stdin.readline().strip()
            if line:
                command = json.loads(line)
                return command
        except Exception as e:
            pass
    return {}

def process_command(command: dict) -> None:
    """Process the command received from stdin"""
    if command.get("command") == "reset":
        print(json.dumps({'status': 'resetting'}))
        reset()
    elif command.get("command") == "poll":
        # Create state object
        state = {
            'steer': gyro.get_angles()[0],
            'button': b1.get_state(),
            'knob': {
                "count": k.get_count(),
                "switch": k.get_switch()
            }
        }   
        # Send response as JSON
        print(json.dumps(state))   
    elif command.get("command") == "save":
        save_angles()
        print(json.dumps({"status": "saved"}))
    elif command.get("command") == "tare":
        gyro.tare_gyro((0,0,0))
        print(json.dumps({"status": "tared"}))
    else:
        print(json.dumps({"status": "unknown command"}))

def loop():
    global last_led_toggle
    # Update LED at 2Hz for visual heartbeat
    current_time = time.time_ns()/1000000  # Convert to milliseconds
    if current_time-last_led_toggle > 500:
        LED.toggle()
        last_led_toggle = current_time
        
    # Poll sensors
    gyro.poll()
    b1.poll()
    k.poll()
    
    data = read()
    if not data == None and not data.get("command") == None:
        process_command(data)

if __name__ == "__main__":
    # Initial setup - load saved angles
    angles = load_saved_angles()
    gyro.tare_gyro(angles)
    
    print("Ready to receive commands")
    
    # Setup polling for stdin
    poller.register(sys.stdin, select.POLLIN)
    
    while True:
        loop()