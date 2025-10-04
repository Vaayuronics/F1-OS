import sys
from machine import Pin, reset
import include.gyro as gyro_module
from include.button import Button
from include.knob import Knob
import json
import os
import time  # For delays
import select

# Debug LED to show we're running
LED = Pin("LED", Pin.OUT)
LED.on()  # Turn on immediately to show we're starting

# Defining objects
gyro = gyro_module.Gyro(16, 17)
#NOTE: Headlights should also turn on a rear lights like car do at night. 
# Only two of the three lights though in upside down equalatral triangle, the side ones. 
# Top one is brake light. Hazards flash all lights.
buttons = [Button(0, "Shift Emulation Toggle"), Button(1, "Headlights"), Button(2, "Hazards"),  Button(3, "Change Engine"), 
           Button(4, "Change Music"), Button( 5,"DRS"), Button(6, "Start"), Button(7, "Stop"), 
           Button(8, "Play/Pause"), Button(9, "Horn"), Button(10, "Auto Turn Signal Toggle")]
knobs = [Knob(15, 16, 17, "Engine Vol"), Knob(19, 20, 21, "Engine Tune"), Knob(22, 24, 25, "Music Vol")]  # dt, clk, sw
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
        save_angles()
        print(json.dumps({'status': 'resetting'}))
        reset()
    elif command.get("command") == "poll":
        # Create state object
        state = {
            'status': 'polled',
            'gyro': gyro.get_angles(),
            'buttons': {b.get_name(): b.get_state() for b in buttons},
            'knobs': {k.get_name(): {"count": k.get_count(), "switch": k.get_switch()} for k in knobs}
        }
        # Send response as JSON
        print(json.dumps(state))   
    elif command.get("command") == "stop":
        save_angles()
        print(json.dumps({"status": "stopping"}))
        exit(0)
    elif command.get("command") == "tare":
        gyro.tare_gyro((0,0,0))
        print(json.dumps({"status": "tared"}))
    else:
        print(json.dumps({"status": "unknown command"}))

def heartbeat():
    global last_led_toggle
    # Update LED at 1Hz for visual heartbeat
    current_time = time.time_ns()/1000000  # Convert to milliseconds
    if current_time-last_led_toggle > 1000:
        LED.toggle()
        last_led_toggle = current_time

def poll_all():
    '''Poll all input devices.'''
    gyro.poll()
    for b in buttons:
        b.poll()
    for k in knobs:
        k.poll()
 
def loop():
    heartbeat()
    poll_all()
    
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