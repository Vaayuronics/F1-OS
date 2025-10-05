from devices.jerial import JSONSerialReader
import engine.soundsys as sound
import time
import threading
import sys
import signal 
import math
import ui.dashboard as dash
from devices.light_manager import LightManager
from devices.button import Button

'''
TODO: Check to see if the usb ports on the Raspberry Pi are still not working with tty.
NOTE: Possible issue with polling rate being so high button inputs are counted multiple times.
        If this is the case, implement a debounce system in the button class.
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
persist_lock = threading.Lock()
ui_data = None
sound_data = None
hardware_data = None
persist_data = {'Headlights': False, 'Hazards': False, 'Auto Turn Signal': False, 'DRS': False,
                 'Shift Emulation': False, 'Started': False, 'Porche': False, 'Prev Speed': 0, 
                 'Prev Time': 0, 'Music Mute': False, 'Engine Mute': False, 'Tune': 0, 'Pause': False}
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
    global interrupted, ui_data, ui_data_cond
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
        start = time.time()
        pico_data = pico.poll()
        arduino_data = arduino.poll()
        # would be better if done seperatly but its more efficient if done together
        process_data(pico_data, arduino_data)
        # Should occur ever 100 ms, if processing took less time, sleep the remainder
        time.sleep(min(0, 0.1 - (time.time() - start)))

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
    global interrupted, sound_data, sound_data_cond, persist_data, persist_lock
    sound.load_tracks()
    sound.play_startup_sound()
    while not interrupted.is_set():
        data = None
        persistent = None
        with sound_data_cond:
            while not sound_data:
                sound_data_cond.wait()
            data = sound_data
            sound_data_cond.notify(1)
        with persist_lock:
            persistent = persist_data
            persist_lock.notify(1)
        if data.get('Start', False):
            sound.play_f1_start()
        if data.get('Horn', False):
            sound.play_horn()
        if 'Porche' in data:
            sound.set_porche_mode(data['Porche'])
        if data.get('Change Track', False):
            sound.change_track(sound.current_track() + 1)
        #TODO: Implement Lauch sound
        if 'Pause' in persistent and not persistent['Pause']:
            sound.play_music(data.get('Music Volume', 0))
        sound.play_engine(data.get('Accel'), data.get('Speed', 0), data.get('Engine Volume', 0))
        time.sleep(0.1)  # Polling interval

def calc_speed_rpm(throttle: float, speed: float, gear: int, engine_speed : float, motor_rpm: int) -> tuple[bool, float, float]:
    '''Simple RPM calculation based on throttle and speed.'''
    global persist_data
    accel = False
    play_speed = 1.0
    rpm = 0.0

    rate = 0
    if (time.time() - persist_data['Prev Time']) > 0:
        rate = speed - persist_data['Prev Speed']/(time.time() - persist_data['Prev Time'])

    #TODO: Finish claculations

    if gear == 0:
        rpm = throttle * 103.7

        # Throttle goes from 0-135, 25% throttle is 1x speed, make
        # equation that does this up to 3x speed at 100% throttle
        # Map throttle (0-135) to playback speed multiplier for engine sounds.
        # New behavior (logarithmic feel):
        # - Below 25% throttle playback slows down logarithmically (gives a
        #   'heavy' low-throttle feel).
        # - At 25% throttle we return to baseline 1.0 playback.
        # - From 25% to 100% we smoothly increase up to 3.0 using a small log-based
        #   curve to keep responsiveness but with diminishing returns.
        # Implementation approach:
        # - Compute throttle_pct in [0,1].
        # - For throttle_pct <= 0.25 use a logarithmic decay below 1.0:
        #     play_speed = 1.0 - A * log10(1 + B * (0.25 - throttle_pct))
        #   so speed falls as throttle decreases.
        # - For throttle_pct > 0.25, map to [1.0, 3.0] using a gentle log curve:
        #     play_speed = 1.0 + (3.0 - 1.0) * (log(1 + C * (throttle_pct - 0.25)) / log(1 + C * 0.75))
        #   which normalizes the log output so throttle_pct=1.0 => play_speed=3.0.
        max_throttle = 135.0
        throttle_pct = max(0.0, min(throttle / max_throttle, 1.0))

        if throttle_pct <= 0.25:
            # Parameters tuned for a pleasant slow-down feel under 25%.
            A = 0.22
            B = 18.0
            # use log10 because it's shallower near zero; add 1 to keep argument >0
            play_speed = 1.0 - A * math.log10(1.0 + B * (0.25 - throttle_pct))
            # clamp lower bound so playback doesn't become negative
            play_speed = max(play_speed, 0.5)
        else:
            # For the upper region (25%..100%) use a normalized natural-log curve
            C = 6.0
            numerator = math.log(1.0 + C * (throttle_pct - 0.25))
            denominator = math.log(1.0 + C * 0.75)
            frac = numerator / denominator if denominator != 0 else 1.0
            play_speed = 1.0 + (3.0 - 1.0) * frac
            play_speed = min(max(play_speed, 1.0), 3.0)

    if speed >= persist_data['Prev Speed']:
        accel = True

    return accel, play_speed, rpm

def process_data(pico_data, arduino_data):
    """Combine and process data from pico and arduino.\n
    Operate on any hardware instructions.\n
    Return combined data for UI."""
    global ui_data, ui_data_cond, hardware_data, hardware_data_cond, sound_data, sound_data_cond, persist_data, persist_lock
    #Clear ui_data and let all consumers start waiting for new data instead of operating on old data. Old data bad, duh.
    #idk if this even works. time to test in prod type shi
    with ui_data_cond:
        ui_data = None
        ui_data_cond.notify_all()
    with hardware_data_cond:
        hardware_data = None
        hardware_data_cond.notify_all()
    with sound_data_cond:
        sound_data = None
        sound_data_cond.notify_all()

    ui_data = {} # Reset ui_data
    hardware_data = {} # Reset hardware_data
    sound_data = {} # Reset sound_data

    with ui_data_cond:
        with hardware_data_cond: 
            with sound_data_cond:
                with persist_lock:
                    #Always replace ui data, dont wait for consumption!!
                    if pico_data:
                        '''User button inputs'''
                        if 'buttons' in pico_data:
                            buttons = pico_data['buttons']
                            if 'Shift Emulation Toggle' in buttons and buttons['Shift Emulation Toggle'].get('pressed', True):
                                ui_data['Alert Title'] = f"Shift Emulation {'ON' if not persist_data['Shift Emulation'] else 'OFF'}"
                                ui_data['Alert Message'] = "Shift emulation mode has been toggled."
                                ui_data['Shift Emulation'] = not persist_data['Shift Emulation']
                                persist_data['Shift Emulation'] = ui_data['Shift Emulation']
                            if 'Headlights' in buttons and buttons['Headlights'].get('pressed', True):
                                ui_data['Alert Title'] = f"Headlights {'ON' if not persist_data['Headlights'] else 'OFF'}"
                                ui_data['Alert Message'] = "Headlights and backlights are toggled."
                                if ui_data['Headlights']:
                                    hardware_data['Lights'] = "Headlights"
                                else:
                                    hardware_data['Lights'] = "Off"
                                persist_data['Headlights'] = not persist_data['Headlights']
                            if 'Hazards' in buttons and buttons['Hazards'].get('pressed', True):
                                ui_data['Alert Title'] = f"Hazards {'ON' if not persist_data['Hazards'] else 'OFF'}"
                                ui_data['Alert Message'] = "All lights are flashing is toggled."
                                if ui_data['Hazards']:
                                    hardware_data['Lights'] = "Hazards"
                                elif not hardware_data.get('Lights', "Off") == "Headlights":
                                    hardware_data['Lights'] = "Off"
                                persist_data['Hazards'] = not persist_data['Hazards']
                            if 'Change Engine' in buttons and buttons['Change Engine'].get('pressed', True):
                                sound_data['Porche'] = not persist_data['Porche'] # Toggle between two modes
                                ui_data['Alert Title'] = "Engine Changed"
                                ui_data['Alert Message'] = f"Engine mode changed to {'Porche' if sound_data['Porche'] else 'F1 v10'}."
                                persist_data['Porche'] = sound_data['Porche']
                            if 'Change Music' in buttons and buttons['Change Music'].get('pressed', True):
                                sound_data["Change Track"] = True
                            if 'DRS' in buttons and buttons['DRS'].get('pressed', True):
                                ui_data['Alert Title'] = f"DRS {'ON' if not persist_data['drs'] else 'OFF'}"
                                ui_data['Alert Message'] = "Drag Reduction System has been toggled."
                                hardware_data['DRS'] = not persist_data['DRS']
                                persist_data['DRS'] = not persist_data['DRS']
                            if 'Start' in buttons and buttons['Start'].get('pressed', True):
                                if persist_data['Started'] == False:
                                    sound_data['Start'] = True  # Momentary start sound
                                    ui_data['Alert Title'] = "Car Started"
                                    ui_data['Alert Message'] = "Car has been started."
                                    persist_data['Started'] = True
                                else:
                                    #TODO: Implement launch control
                                    sound_data['Launch'] = True #Lauch control sound while pressed
                            if 'Stop' in buttons and buttons['Stop'].get('pressed', True):
                                #TODO: Still need to implement hardware stop on throttle wire with switch
                                ui_data['Alert Title'] = "Car Stopped"
                                ui_data['Alert Message'] = "Car has been turned off."
                                persist_data['Started'] = False
                                hardware_data['STOP'] = True 
                            if 'Play/Pause' in buttons and buttons['Play/Pause'].get('pressed', True):
                                persist_data['Pause'] = not persist_data['Pause']
                            if 'Auto Turn Signal Toggle' in buttons and buttons['Auto Turn Signal Toggle'].get('pressed', True):
                                ui_data['Alert Title'] = f"Auto Turn Signal {'ON' if not persist_data['Auto Turn Signal'] else 'OFF'}"
                                ui_data['Alert Message'] = "Auto turn signal has been toggled."
                                persist_data['Auto Turn Signal'] = not persist_data['Auto Turn Signal']
                            if 'Horn' in buttons and buttons['Horn'].get('pressed', True):
                                sound_data['Horn'] = True  # Momentary horn sound
                        if 'knobs' in pico_data:
                            knobs = pico_data['knobs']
                            if 'Engine Vol' in knobs:
                                if knobs['Engine Vol'].get('switch', False):
                                    persist_data['Engine Mute'] = not persist_data['Engine Mute']
                                if persist_data['Engine Mute']:
                                    sound_data['Engine Volume'] = 0
                                else:
                                    sound_data['Engine Volume'] = max(min(knobs['Engine Vol'].get('count', 0), 100), 0)  #clamped 0-100
                            if 'Music Vol' in knobs:
                                if knobs['Music Vol'].get('switch', False):
                                    persist_data['Music Mute'] = not persist_data['Music Mute']
                                if persist_data['Music Mute']:
                                    sound_data['Music Volume'] = 0
                                else:
                                    sound_data['Music Volume'] = max(min(knobs['Music Vol'].get('count', 0), 100), 0)  #clamped 0-100
                            if 'Engine Tune' in knobs:
                                if knobs['Engine Tune'].get('switch', False):
                                    ui_data['Mode Switch'] = True
                                else:
                                    ui_data['Engine Tune'] = max(min(knobs['Engine Tune'].get('count', 0), 100), 0)  # 0-100
                                    persist_data['Tune'] = ui_data['Engine Tune']

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
                            persist_data['Prev Speed'] = speed
                            persist_data['Prev Time'] = time.time()
 
                sound_data_cond.notify_all()
            hardware_data_cond.notify_all()
        ui_data_cond.notify_all()

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