from devices.jerial import JSONSerialReader
import engine.soundsys
import time
import threading
import sys
import signal 
from ui.dashboard import F1Dashboard, REFRESH_RATE
from devices.light_manager import LightManager

'''
TODO: Check to see if the usb ports on the Raspberry Pi are still not working with tty.
'''

pico = None
arduino = None
lights = LightManager([17, 27, 22, 23, 24, 25, 5, 6, 16], ["Green 1", "Green 2", "Green 3", "Green 4", "Blue 1", "Blue 2", "Yellow", "Orange", "Red"])
dashboard = None
interrupt_lock = threading.Lock()
ui_data_lock = threading.Lock()
ui_data = None
interrupted = False

def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) gracefully"""
    global interrupted, dashboard, lights
    print("\nReceived interrupt signal. Shutting down gracefully...")
    with interrupt_lock:
        interrupted = True
    if dashboard:
        dashboard.close()  # Close the dashboard window
    if lights:
        lights.turn_off_all()  # Turn off all lights
        lights.cleanup()  # Clean up GPIO
    if pico:
        pico.send({"command": "stop"})
        pico.ser.close()
    if arduino:
        arduino.send({"command": "stop"})
        arduino.ser.close()
    time.sleep(1) # Give some time for devices to process stop command
    sys.exit(0)  # Exit cleanly

# Set up signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)

def telemetry_update_loop():
    """Continuously update telemetry data"""
    global interrupted
    while True:
        interrupt_lock.acquire()
        if interrupted:
            interrupt_lock.release()
            break
        ui_data_lock.acquire()
        if ui_data:
            dashboard.set_data_thread_safe(ui_data)
        ui_data_lock.release()
        time.sleep(REFRESH_RATE)  # Update at ~58Hz to match display refresh rate

def hardware_loop():
    """Continuously poll hardware devices"""
    global interrupted, ui_data
    while True:
        interrupt_lock.acquire()
        if interrupted:
            interrupt_lock.release()
            break
        pico_data = pico.poll()
        arduino_data = arduino.poll()
        ui_processed_data = process_data(pico_data, arduino_data)
        if ui_processed_data:
            ui_data_lock.acquire()
            ui_data = ui_processed_data
            ui_data_lock.release()
        interrupt_lock.release()
        time.sleep(0.01)  # Polling interval

def process_data(pico_data, arduino_data) -> dict:
    """Combine and process data from pico and arduino.\n
    Operate on any hardware instructions.\n
    Return combined data for UI."""
    combined = {}
    if pico_data:
        '''User button inputs'''
        if 'buttons' in pico_data:
            buttons = pico_data['buttons']
            if 'engine_knob' in buttons:
                combined['engine_volume'] = buttons['engine_knob'].get('count', 0)
                combined['engine_mute'] = buttons['engine_knob'].get('switch', 0) == 0
            if 'music_knob' in buttons:
                combined['music_volume'] = buttons['music_knob'].get('count', 0)
                combined['music_mute'] = buttons['music_knob'].get('switch', 0) == 0
        if 'knobs' in pico_data:
            knobs = pico_data['knobs']
            for k in knobs:
                combined[f"{k.get_name()}_count"] = k.get_count()
                combined[f"{k.get_name()}_switch"] = k.get_switch()
    if arduino_data:
        '''Throttle and Speed data'''
        if 'throttle' in arduino_data:
            combined['throttle'] = arduino_data['throttle']
        if 'speed' in arduino_data:
            combined['speed'] = arduino_data['speed']
    return combined

def boot():
    print("Booting up system.")

    global pico, arduino, dashboard

    pico = JSONSerialReader("/dev/pico")
    arduino = JSONSerialReader("/dev/arduino")
    dashboard = F1Dashboard("ui/dashboard_settings.ini", "ui/model.fbx")

    telemetry_thread = threading.Thread(target=telemetry_update_loop, daemon=True)
    telemetry_thread.start()

    hardware_thread = threading.Thread(target=hardware_loop, daemon=True)
    hardware_thread.start()

    dashboard.enable_fullscreen()
    exit_code = dashboard.run()
    while exit_code != 0:
        print("Application exited with code:", exit_code, "restarting...")
        exit_code = dashboard.run()
    print("Application finished with exit code:", exit_code)
    sys.exit(exit_code)

if __name__ == "__main__":
    try:
        #boot()
        lights.turn_on("Green 1")
        time.sleep(1)
        lights.turn_on("Green 2")
        time.sleep(1)
        lights.turn_on("Green 3")
        time.sleep(1)
        lights.turn_on("Green 4")
        time.sleep(1)
        lights.turn_on("Blue 1")
        time.sleep(1)
        lights.turn_on("Blue 2")
        time.sleep(1)
        lights.turn_on("Yellow")
        time.sleep(1)
        lights.turn_on("Orange")
        time.sleep(1)
        lights.turn_on("Red")
        time.sleep(5)
        lights.turn_off_all()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        print("Cleaning up GPIO...")
        lights.cleanup()