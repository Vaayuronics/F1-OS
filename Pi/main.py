from devices.jerial import JSONSerialReader
import engine.soundsys as sound
import time
import threading
import sys
import signal 
import ui.dashboard as dash
from devices.light_manager import LightManager
from devices.button import Button

'''
TODO: Check to see if the usb ports on the Raspberry Pi are still not working with tty.
'''

pico = None
arduino = None
lights = LightManager([16, 6, 5, 7, 24, 23, 22, 27, 17], 
                      ["Green 1", "Green 2", "Green 3", "Green 4", "Blue 1", "Blue 2", "Yellow", "Orange", "Red"])
gear_up = Button(13, "Gear Up")
gear_down = Button(19, "Gear Down")
cur_gear = 0 # Supposedly int operations are atomic in python so this should be fine without a lock
dashboard = None
ui_data_cond = threading.Condition()
hardware_data_cond = threading.Condition()
sound_data_cond = threading.Condition()
previous_cond = threading.Condition()
ui_data = None
sound_data = None
hardware_data = None
previous_data = {'Headlights': False, 'Hazards': False, 'Auto Turn Signal': False, 'DRS': False,
                 'Shift Emulation': False, 'Started': False, 'Porche': False, 'Track' : 0, 
                 'Prev Speed': 0, 'Prev Time': 0, 'Music Mute': False, 'Engine Mute': False, 'Tune': 0}
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
    global interrupted, ui_data, ui_data_cond
    # First time light bootup animation
    lights_boot_anim()
    # Should be off now
    while not interrupted.is_set():
        data : dict = None
        with ui_data_cond:
            while not ui_data:
                ui_data_cond.wait()
            data = ui_data
            ui_data_cond.notify(1)
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
    while not interrupted.is_set():
        data = None
        with ui_data_cond:
            while not ui_data:
                ui_data_cond.wait()
            data = ui_data
            ui_data_cond.notify(1)
        if data:
            dashboard.set_data_thread_safe(data)
        time.sleep(dash.REFRESH_RATE)  # Update at ~58Hz to match display refresh rate

def hardware_update_loop():
    """Continuously poll hardware devices"""
    global interrupted, pico, arduino
    while not interrupted.is_set():
        pico_data = pico.poll()
        arduino_data = arduino.poll()
        # would be better if done seperatly but its more efficient if done together
        process_data(pico_data, arduino_data)
        time.sleep(0.01)  # Polling interval

def hardware_loop():
    '''Complete operations on hardware data'''
    global interrupted, hardware_data, hardware_data_cond
    while not interrupted.is_set():
        data = None
        with hardware_data_cond:
            while not hardware_data:
                hardware_data_cond.wait()
            data = hardware_data
            hardware_data_cond.notify(1)
        if data:
            #TODO: Process hardware data
            #INFO: For some things look in prev data as it is persistent
            pass

def audio_loop():
    '''Play the sounds chunks and return '''
    global interrupted, sound_data, sound_data_cond
    sound.load_tracks()
    sound.play_startup_sound()
    while not interrupted.is_set():
        data = None
        with sound_data_cond:
            while not sound_data:
                sound_data_cond.wait()
            data = sound_data
            sound_data_cond.notify(1)
        if data.get('Start', False):
            sound.play_f1_start()
        if data.get('Horn', False):
            sound.play_horn()
        if 'Porche' in data:
            sound.set_porche_mode(data['Porche'])
        sound.play_audio(data.get('Accel'), data.get('Speed', 0), data.get('Engine Vol', 0), data.get('Music Vol', 0))
        #TODO: Process other sound data like Music Track, Volume
        time.sleep(0.1)  # Polling interval

def calc_speed_rpm(throttle: float, speed: float, gear: int, engine_speed : float, motor_rpm: int) -> tuple[bool, float, float]:
    '''Simple RPM calculation based on throttle and speed.'''
    global previous_data
    accel = False
    play_speed = 1.0
    rpm = 0.0

    rate = 0
    if (time.time() - previous_data['Prev Time']) > 0:
        rate = speed - previous_data['Prev Speed']/(time.time() - previous_data['Prev Time'])

    #TODO: Finish claculations

    if speed >= previous_data['Prev Speed']:
        accel = True

    return accel, play_speed, rpm

def process_data(pico_data, arduino_data):
    """Combine and process data from pico and arduino.\n
    Operate on any hardware instructions.\n
    Return combined data for UI."""

    #Clear ui_data and let all consumers start waiting for new data instead of operating on old data. Old data bad, duh.
    #idk if this even works. time to test in prod type shi
    global ui_data, ui_data_cond, hardware_data, hardware_data_cond, sound_data, sound_data_cond, previous_data, previous_cond
    with ui_data_cond:
        ui_data = None
        ui_data_cond.notify_all()
    ui_data = {} # Reset ui_data
    with hardware_data_cond:
        hardware_data = None
        hardware_data_cond.notify_all()
    hardware_data = {} # Reset hardware_data
    with sound_data_cond:
        sound_data = None
        sound_data_cond.notify_all()
    sound_data = {} # Reset sound_data

    with ui_data_cond and hardware_data_cond and sound_data_cond and previous_cond:
        #Always replace ui data, dont wait for consumption!!
        if pico_data:
            '''User button inputs'''
            if 'buttons' in pico_data:
                buttons = pico_data['buttons']
                if 'Shift Emulation Toggle' in buttons and buttons['Shift Emulation Toggle'].get('pressed', True):
                    ui_data['Alert Title'] = f"Shift Emulation {'ON' if not previous_data['Shift Emulation'] else 'OFF'}"
                    ui_data['Alert Message'] = "Shift emulation mode has been toggled."
                    ui_data['Shift Emulation'] = not previous_data['Shift Emulation']
                    previous_data['Shift Emulation'] = ui_data['Shift Emulation']
                if 'Headlights' in buttons and buttons['Headlights'].get('pressed', True):
                    ui_data['Alert Title'] = f"Headlights {'ON' if not previous_data['Headlights'] else 'OFF'}"
                    ui_data['Alert Message'] = "Headlights and backlights are toggled."
                    if ui_data['Headlights']:
                        hardware_data['Lights'] = "Headlights"
                    else:
                        hardware_data['Lights'] = "Off"
                    previous_data['Headlights'] = not previous_data['Headlights']
                if 'Hazards' in buttons and buttons['Hazards'].get('pressed', True):
                    ui_data['Alert Title'] = f"Hazards {'ON' if not previous_data['Hazards'] else 'OFF'}"
                    ui_data['Alert Message'] = "All lights are flashing is toggled."
                    if ui_data['Hazards']:
                        hardware_data['Lights'] = "Hazards"
                    elif not hardware_data.get('Lights', "Off") == "Headlights":
                        hardware_data['Lights'] = "Off"
                    previous_data['Hazards'] = not previous_data['Hazards']
                if 'Change Engine' in buttons and buttons['Change Engine'].get('pressed', True):
                    sound_data['Porche'] = not previous_data['Porche'] # Toggle between two modes
                    ui_data['Alert Title'] = "Engine Changed"
                    ui_data['Alert Message'] = f"Engine mode changed to {'Porche' if sound_data['Porche'] else 'F1 v10'}."
                    previous_data['Porche'] = sound_data['Porche']
                if 'Change Music' in buttons and buttons['Change Music'].get('pressed', True):
                    sound_data["Track"] = (previous_data['Track'] + 1) % sound.TRACKS  # Cycle through 10 tracks
                    ui_data['Alert Title'] = "Music Changed"
                    ui_data['Alert Message'] = f"Music track changed to Track {sound_data['Track'] + 1}."
                    previous_data['Track'] = sound_data['Track']
                if 'DRS' in buttons and buttons['DRS'].get('pressed', True):
                    ui_data['Alert Title'] = f"DRS {'ON' if not previous_data['drs'] else 'OFF'}"
                    ui_data['Alert Message'] = "Drag Reduction System has been toggled."
                    hardware_data['DRS'] = not previous_data['DRS']
                    previous_data['DRS'] = not previous_data['DRS']
                if 'Start' in buttons and buttons['Start'].get('pressed', True):
                    if previous_data['Started'] == False:
                        sound_data['Start'] = True  # Momentary start sound
                        ui_data['Alert Title'] = "Car Started"
                        ui_data['Alert Message'] = "Car has been started."
                        previous_data['Started'] = True
                    else:
                        #TODO: Implement launch control
                        pass
                if 'Stop' in buttons and buttons['Stop'].get('pressed', True):
                    #TODO: Still need to implement hardware stop on throttle wire with switch
                    ui_data['Alert Title'] = "Car Stopped"
                    ui_data['Alert Message'] = "Car has been turned off."
                    previous_data['Started'] = False
                    hardware_data['STOP'] = True 
                if 'Play/Pause' in buttons and buttons['Play/Pause'].get('pressed', True):
                    #TODO: Implement Play/Pause
                    pass
                if 'Auto Turn Signal Toggle' in buttons and buttons['Auto Turn Signal Toggle'].get('pressed', True):
                    ui_data['Alert Title'] = f"Auto Turn Signal {'ON' if not previous_data['Auto Turn Signal'] else 'OFF'}"
                    ui_data['Alert Message'] = "Auto turn signal has been toggled."
                    previous_data['Auto Turn Signal'] = not previous_data['Auto Turn Signal']
                if 'Horn' in buttons and buttons['Horn'].get('pressed', True):
                    sound_data['Horn'] = True  # Momentary horn sound
            if 'knobs' in pico_data:
                knobs = pico_data['knobs']
                if 'Engine Vol' in knobs:
                    if knobs['Engine Vol'].get('switch', False):
                        previous_data['Engine Mute'] = not previous_data['Engine Mute']
                    if previous_data['Engine Mute']:
                        sound_data['Engine Volume'] = 0
                    else:
                        sound_data['Engine Volume'] = max(min(knobs['Engine Vol'].get('count', 0), 100), 0)  #clamped 0-100
                if 'Music Vol' in knobs:
                    if knobs['Music Vol'].get('switch', False):
                        previous_data['Music Mute'] = not previous_data['Music Mute']
                    if previous_data['Music Mute']:
                        sound_data['Music Volume'] = 0
                    else:
                        sound_data['Music Volume'] = max(min(knobs['Music Vol'].get('count', 0), 100), 0)  #clamped 0-100
                if 'Engine Tune' in knobs:
                    if knobs['Engine Tune'].get('switch', False):
                        ui_data['Mode Switch'] = True
                    else:
                        ui_data['Engine Tune'] = max(min(knobs['Engine Tune'].get('count', 0), 100), 0)  # 0-100
                        previous_data['Tune'] = ui_data['Engine Tune']

        if arduino_data:
            if 'Throttle' in arduino_data and 'Speed' in arduino_data and 'Engine Speed' in arduino_data and 'Engine RPM' in arduino_data and 'Brake' in arduino_data:
                accel, speed, rpm = calc_speed_rpm(arduino_data.get('Throttle', 0), arduino_data.get('Speed', 0), cur_gear, arduino_data.get('Engine Speed', 0), arduino_data.get('Engine RPM', 0))
                sound_data['Accel'] = accel
                ui_data['RPM'] = rpm
                ui_data['Engine RPM'] = arduino_data['Engine RPM']
                ui_data['Engine Speed'] = arduino_data['Engine Speed']
                ui_data['Speed'] = arduino_data['Speed']
                ui_data['Throttle'] = arduino_data['Throttle']
                hardware_data['Brake'] = arduino_data['Brake']
                hardware_data['Throttle'] = arduino_data['Throttle']
                previous_data['Prev Speed'] = speed
                previous_data['Prev Time'] = time.time()

        ui_data_cond.notify_all()
        hardware_data_cond.notify_all()
        sound_data_cond.notify_all()

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

    hardware_update_thread = threading.Thread(target=hardware_update_loop, daemon=True)
    hardware_update_thread.start()

    hardware_thread = threading.Thread(target=hardware_loop, daemon=True)
    hardware_thread.start()

    audio_thread = threading.Thread(target=audio_loop, daemon=True)
    audio_thread.start()

    start_dashboard()

if __name__ == "__main__":
    boot()