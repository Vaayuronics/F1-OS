from devices.jerial import JSONSerialReader
import engine.soundsys as sound
import time
import threading
import sys
import signal 
import ui.dashboard as dash
from devices.light_manager import LightManager

'''
TODO: Check to see if the usb ports on the Raspberry Pi are still not working with tty.
'''

pico = None
arduino = None
lights = LightManager([16, 6, 5, 25, 24, 23, 22, 27, 17], ["Green 1", "Green 2", "Green 3", "Green 4", "Blue 1", "Blue 2", "Yellow", "Orange", "Red"])
dashboard = None
ui_data_cond = threading.Condition()
hardware_data_cond = threading.Condition()
sound_data_cond = threading.Condition()
started = False
ui_data = None
sound_data = None
hardware_data = None
interrupted = threading.Event()

def signal_handler(signum, frame):
    """Handle SIGINT gracefully"""
    global interrupted, dashboard, lights, arduino, pico
    print("\nReceived interrupt signal. Shutting down gracefully...")
    interrupted.set()
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
    time.sleep(3) # Give some time for devices to process stop command
    sys.exit(0)  # Exit cleanly

# Set up signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)

def light_loop():
    """Continuously update lights based on UI data"""
    global interrupted, interrupt_cond, ui_data, ui_data_cond
    # First time light bootup animation
    lights_boot_anim()
    # Should be off now
    while True:
        with interrupt_cond:
            if interrupted:
                break
        data : dict = None
        with ui_data_cond:
            data = ui_data
        rpm = data.get('rpm', 0)
        lights_count = len(lights.lights)
        rpm_per_light = dash.MAX_RPM / lights_count
        
        for i in range(lights_count):
            if rpm >= i * rpm_per_light:
                lights.turn_on(i)
            if rpm > dash.MAX_RPM:
                lights.toggle(lights_count - 1)  # Flash the last light if over max RPM
            else:
                lights.turn_off(i)
        time.sleep(0.5)  # Adjust light update frequency as needed

def telemetry_update_loop():
    """Continuously update telemetry data"""
    global interrupted
    while True:
        with interrupt_cond:
            if interrupted:
                break
        data = None
        with ui_data_cond:
            data = ui_data
        if data:
            dashboard.set_data_thread_safe(data)
        time.sleep(dash.REFRESH_RATE)  # Update at ~58Hz to match display refresh rate

def hardware_loop():
    """Continuously poll hardware devices"""
    global interrupted, ui_data, interrupt_cond, hardware_data, hardware_data_cond, sound_data, sound_data_cond, ui_data_cond
    while not interrupted.is_set():
        pico_data = pico.poll()
        arduino_data = arduino.poll()
        #TODO: Process hardware data and update ui_data and sound_data accordingly
        process_ui_data(pico_data, arduino_data)
        time.sleep(0.01)  # Polling interval

def process_ui_data(pico_data, arduino_data):
    """Combine and process data from pico and arduino.\n
    Operate on any hardware instructions.\n
    Return combined data for UI."""
    global ui_data, ui_data_cond
    with ui_data_cond:
        if pico_data:
            '''User button inputs'''
            if 'buttons' in pico_data:
                buttons = pico_data['buttons']
                if 'Headlights' in buttons:
                    #TODO: Implement Headlights
                    pass
                if 'Hazards' in buttons:
                    #TODO: Implement Hazards
                    pass
                if 'Horn' in buttons:
                    #TODO: Implement Horn
                    pass
                if 'Auto Turn Signal Toggle' in buttons:
                    #TODO: Implement Auto Turn Signal Toggle
                    pass
                if 'Start' in buttons and buttons['Start'].get('pressed', False) and not started:
                    #TODO: Implement Start
                    pass
                if 'Stop' in buttons and buttons['Stop'].get('pressed', False) and started:
                    #TODO: Implement Stop
                    pass
                if 'Play/Pause' in buttons and buttons['Play/Pause'].get('pressed', False):
                    #TODO: Implement Play/Pause
                    pass
            if 'knobs' in pico_data:
                knobs = pico_data['knobs']
                if 'Engine Vol' in knobs:
                    ui_data['Engine Volume'] = max(min(knobs['Engine Vol'].get('count', 0) if not knobs['Engine Vol'].get('switch', 0) else 0, 100), 0)  # Mute if switch is on, clamped 0-100
                if 'Music Vol' in knobs:
                    ui_data['Music Volume'] = max(min(knobs['Music Vol'].get('count', 0) if not knobs['Music Vol'].get('switch', 0) else 0, 100), 0)  # Mute if switch is on, clamped 0-100
                if 'Engine Tune' in knobs:
                    ui_data['Engine Tune'] = max(min(knobs['Engine Tune'].get('count', 0), 100), 0) # Clamped 0-100
                    ui_data['Engine Mode'] = knobs['Engine Tune'].get('switch', 0)  # 0 or 1 for two modes

        if arduino_data:
            '''Throttle and Speed data'''
            if 'throttle' in arduino_data:
                ui_data['throttle'] = arduino_data['throttle']
            if 'brake' in arduino_data:
                ui_data['brake'] = arduino_data['brake']
            if 'speed' in arduino_data:
                ui_data['speed'] = arduino_data['speed']
        if 'throttle' in ui_data and 'speed' in ui_data:
            ui_data['rpm'] = calc_rpm(ui_data['throttle'], ui_data['speed'])

def audio_loop():
    '''Play the sounds chunks and return '''
    global interrupted, sound_data, sound_data_cond
    while not interrupted.is_set():
        data = None
        with sound_data_cond:
            while not sound_data:
                sound_data_cond.wait()
            data = sound_data
            sound_data = None  # Clear after reading
        #TODO use rpm, throttle, speed, engine rpm to determine audio chunk to play
        time.sleep(0.5)  # Polling interval

def calc_rpm(throttle: float, speed: float, gear: int, motor_rpm: int) -> float:
    '''Simple RPM calculation based on throttle and speed.'''
    #TODO Implement RPM calculation based on karts state and relation to audio.
    pass

def start_dashboard():
    """Start the dashboard UI in the main thread."""
    global dashboard

    dashboard = dash.F1Dashboard("ui/dashboard_settings.ini", "ui/model.fbx")
    
    dashboard.enable_fullscreen()
    exit_code = dashboard.run()
    while exit_code != 0:
        print("Application exited with code:", exit_code, "restarting...")
        exit_code = dashboard.run()
    print("Application finished with exit code:", exit_code)
    sys.exit(exit_code)

def lights_boot_anim():
    time.sleep(3)
    for i in range(len(lights)):
        lights.turn_on(i)
        time.sleep(0.5)
    for i in range(5):
        lights.toggle_all()
        time.sleep(0.3)
    lights.turn_off_all()

def boot():
    print("Booting up system.")

    global pico, arduino

    pico = JSONSerialReader("/dev/pico")
    arduino = JSONSerialReader("/dev/arduino")

    lighting_thread = threading.Thread(target=light_loop, daemon=True)
    lighting_thread.start()

    telemetry_thread = threading.Thread(target=telemetry_update_loop, daemon=True)
    telemetry_thread.start()

    hardware_thread = threading.Thread(target=hardware_loop, daemon=True)
    hardware_thread.start()

    audio_thread = threading.Thread(target=audio_loop, daemon=True)
    audio_thread.start()

    start_dashboard()

if __name__ == "__main__":
    #boot()
    threading.Thread(target=lights_boot_anim, daemon=True).start()
    start_dashboard()