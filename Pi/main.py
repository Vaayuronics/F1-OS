from devices.testerial import JSONSerialReader
import engine.soundsys as sound
import time
import threading
import sys
import signal 
import ui.dashboard as dash
from devices.light_manager import LightManager
from devices.button import Button
import copy

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

# Better synchronization with locks and ready flags
ui_data_lock = threading.Lock()
hardware_data_lock = threading.Lock()
sound_data_lock = threading.Lock()

ui_data = {}
ui_data_ready = False

sound_data = {}
sound_data_ready = False

hardware_data = {}
hardware_data_ready = False

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

def update_rpm_lights(rpm):
    """Update lights based on RPM value."""
    global lights
    lights_count = len(lights.lights)
    rpm_per_light = dash.MAX_RPM / lights_count
    
    for i in range(lights_count):
        if rpm >= i * rpm_per_light:
            lights.turn_on(i)
        else:
            lights.turn_off(i)
            
    if rpm > dash.MAX_RPM:
        lights.toggle(lights_count - 1)  # Flash the last light if over max RPM

def get_ui_data():
    """Get a copy of the current UI data (called by dashboard timer)."""
    global ui_data, ui_data_ready, ui_data_lock
    with ui_data_lock:
        if ui_data_ready and ui_data:
            return copy.deepcopy(ui_data)
    return None

def hardware_update_loop():
    """Continuously poll hardware devices"""
    global interrupted, pico, arduino
    while not interrupted.is_set():
        try:
            pico_data = pico.poll()
            arduino_data = arduino.poll()
            process_data(pico_data, arduino_data)
            time.sleep(0.05)  # Polling interval
        except Exception as e:
            print(f"[hardware_update_loop] Error: {e}")
            if interrupted.is_set():
                break
    
    print("[hardware_update_loop] Thread exiting")

def hardware_loop():
    '''Complete operations on hardware data and update RPM lights'''
    global interrupted, hardware_data, hardware_data_ready, hardware_data_lock
    global ui_data, ui_data_ready, ui_data_lock

    lights_boot_anim()
    
    while not interrupted.is_set():
        try:
            data = None
            rpm = 0
            
            # Get hardware data
            with hardware_data_lock:
                if hardware_data_ready and hardware_data:
                    data = copy.deepcopy(hardware_data)
            
            # Get RPM from ui_data for lights
            with ui_data_lock:
                if ui_data_ready and ui_data:
                    rpm = ui_data.get('RPM', 0)
            
            # Update RPM lights
            if rpm > 0:
                update_rpm_lights(rpm)
            
            if data:
                #TODO: Process hardware data
                # Check persistent flags in data for operations
                if data.get('Lights') == 'Headlights':
                    # Turn on headlights
                    pass
                elif data.get('Lights') == 'Hazards':
                    # Flash all lights
                    pass
                elif data.get('Lights') == 'Off':
                    # Turn off lights
                    pass
                
                if data.get('DRS', False):
                    # Activate DRS
                    pass
                
                if data.get('STOP', False):
                    # Emergency stop throttle
                    pass
            
            time.sleep(0.05)
        except Exception as e:
            print(f"[hardware_loop] Error: {e}")
            if interrupted.is_set():
                break
    
    print("[hardware_loop] Thread exiting")

def audio_loop():
    '''Play the sounds chunks and return '''
    global interrupted, sound_data, sound_data_ready, sound_data_lock
    sound.load_tracks()
    sound.play_startup_sound()
    while not interrupted.is_set():
        try:
            data = None
            with sound_data_lock:
                if sound_data_ready and sound_data:
                    data = copy.deepcopy(sound_data)
            
            if data:
                if data.get('Start', False):
                    sound.play_f1_start()
                if data.get('Horn', False):
                    sound.play_horn()
                if 'Porche' in data:
                    sound.set_porche_mode(data['Porche'])
                if data.get('Change Track', False):
                    sound.change_track(sound.current_track() + 1)
                #TODO: Implement Launch sound
                if data.get('Launch', False):
                    pass  # Launch control sound
                
                if not data.get('Pause', False):
                    sound.play_music(data.get('Music Volume', 0))
                
                sound.play_engine(data.get('Accel', False), data.get('Speed', 0), data.get('Engine Volume', 0))
            
            time.sleep(0.1)  # Polling interval
        except Exception as e:
            print(f"[audio_loop] Error: {e}")
            if interrupted.is_set():
                break
    
    print("[audio_loop] Thread exiting")

def calc_speed_rpm(throttle: float, speed: float, gear: int, prev_speed: float = 0, prev_time: float = 0, engine_speed : float = 0, motor_rpm: int = 0) -> tuple[bool, float, float]:
    '''Simple RPM calculation based on throttle and speed.'''
    accel = False
    play_speed = 1.0
    rpm = 0.0

    rate = 0
    if prev_time > 0 and (time.time() - prev_time) > 0:
        rate = (speed - prev_speed) / (time.time() - prev_time)

    #TODO: Finish calculations

    if gear == 0:
        rpm = throttle * 103.7
    else:
        # Add proper gear-based RPM calculation here
        rpm = (speed * 60 * gear * 10) + (throttle * 50)

    if speed >= prev_speed:
        accel = True

    return accel, play_speed, rpm

def process_data(pico_data, arduino_data):
    """Combine and process data from pico and arduino.\n
    Operate on any hardware instructions.\n
    Return combined data for UI."""
    global ui_data, ui_data_ready, ui_data_lock
    global hardware_data, hardware_data_ready, hardware_data_lock
    global sound_data, sound_data_ready, sound_data_lock
    global cur_gear

    # Create new data dicts to populate (work outside locks)
    new_ui_data = {}
    new_hardware_data = {}
    new_sound_data = {}
    
    # Get current state from existing data for persistent values
    prev_speed = 0
    prev_time = 0
    with ui_data_lock:
        if ui_data:
            prev_speed = ui_data.get('Prev Speed', 0)
            prev_time = ui_data.get('Prev Time', 0)
            # Copy persistent flags to new data
            new_ui_data['Shift Emulation'] = ui_data.get('Shift Emulation', False)
            new_ui_data['Headlights'] = ui_data.get('Headlights', False)
            new_ui_data['Hazards'] = ui_data.get('Hazards', False)
            new_ui_data['Auto Turn Signal'] = ui_data.get('Auto Turn Signal', False)
            new_ui_data['DRS'] = ui_data.get('DRS', False)
            new_ui_data['Started'] = ui_data.get('Started', False)
            new_ui_data['Engine Mute'] = ui_data.get('Engine Mute', False)
            new_ui_data['Music Mute'] = ui_data.get('Music Mute', False)
            new_ui_data['Tune'] = ui_data.get('Tune', 0)
    
    with sound_data_lock:
        if sound_data:
            new_sound_data['Porche'] = sound_data.get('Porche', False)
            new_sound_data['Pause'] = sound_data.get('Pause', False)
    
    with hardware_data_lock:
        if hardware_data:
            new_hardware_data['Lights'] = hardware_data.get('Lights', 'Off')
    
    # Process pico data
    if pico_data:
        '''User button inputs'''
        if 'Buttons' in pico_data:
            buttons = pico_data['Buttons']
            
            # Shift Emulation Toggle
            if buttons.get('Shift Emulation Toggle', False):
                new_ui_data['Shift Emulation'] = not new_ui_data.get('Shift Emulation', False)
                new_ui_data['Alert Title'] = f"Shift Emulation {'ON' if new_ui_data['Shift Emulation'] else 'OFF'}"
                new_ui_data['Alert Message'] = "Shift emulation mode has been toggled."
            
            # Headlights
            if buttons.get('Headlights', False):
                new_ui_data['Headlights'] = not new_ui_data.get('Headlights', False)
                new_ui_data['Alert Title'] = f"Headlights {'ON' if new_ui_data['Headlights'] else 'OFF'}"
                new_ui_data['Alert Message'] = "Headlights and backlights are toggled."
                new_hardware_data['Lights'] = "Headlights" if new_ui_data['Headlights'] else "Off"
            
            # Hazards
            if buttons.get('Hazards', False):
                new_ui_data['Hazards'] = not new_ui_data.get('Hazards', False)
                new_ui_data['Alert Title'] = f"Hazards {'ON' if new_ui_data['Hazards'] else 'OFF'}"
                new_ui_data['Alert Message'] = "All lights are flashing."
                if new_ui_data['Hazards']:
                    new_hardware_data['Lights'] = "Hazards"
                elif not new_ui_data.get('Headlights', False):
                    new_hardware_data['Lights'] = "Off"
            
            # Change Engine
            if buttons.get('Change Engine', False):
                new_sound_data['Porche'] = not new_sound_data.get('Porche', False)
                new_ui_data['Alert Title'] = "Engine Changed"
                new_ui_data['Alert Message'] = f"Engine mode changed to {'Porche' if new_sound_data['Porche'] else 'F1 v10'}."
            
            # Change Music
            if buttons.get('Change Music', False):
                new_sound_data["Change Track"] = True
            else:
                new_sound_data["Change Track"] = False
            
            # DRS
            if buttons.get('DRS', False):
                new_ui_data['DRS'] = not new_ui_data.get('DRS', False)
                new_ui_data['Alert Title'] = f"DRS {'ON' if new_ui_data['DRS'] else 'OFF'}"
                new_ui_data['Alert Message'] = "Drag Reduction System has been toggled."
                new_hardware_data['DRS'] = new_ui_data['DRS']
            
            # Start
            if buttons.get('Start', False):
                if not new_ui_data.get('Started', False):
                    new_sound_data['Start'] = True
                    new_ui_data['Alert Title'] = "Car Started"
                    new_ui_data['Alert Message'] = "Car has been started."
                    new_ui_data['Started'] = True
                else:
                    # Launch control while held
                    new_sound_data['Launch'] = True
            else:
                # Button released
                new_sound_data['Start'] = False
                new_sound_data['Launch'] = False
            
            # Stop
            if buttons.get('Stop', False):
                new_ui_data['Alert Title'] = "Car Stopped"
                new_ui_data['Alert Message'] = "Car has been turned off."
                new_ui_data['Started'] = False
                new_hardware_data['STOP'] = True
            else:
                new_hardware_data['STOP'] = False
            
            # Play/Pause
            if buttons.get('Play/Pause', False):
                new_sound_data['Pause'] = not new_sound_data.get('Pause', False)
            
            # Auto Turn Signal Toggle
            if buttons.get('Auto Turn Signal Toggle', False):
                new_ui_data['Auto Turn Signal'] = not new_ui_data.get('Auto Turn Signal', False)
                new_ui_data['Alert Title'] = f"Auto Turn Signal {'ON' if new_ui_data['Auto Turn Signal'] else 'OFF'}"
                new_ui_data['Alert Message'] = "Auto turn signal has been toggled."
            
            # Horn (momentary)
            if buttons.get('Horn', False):
                new_sound_data['Horn'] = True
            else:
                new_sound_data['Horn'] = False
        
        # Process knobs
        if 'Knobs' in pico_data:
            knobs = pico_data['Knobs']
            
            # Engine Volume
            if 'Engine Vol' in knobs:
                if knobs['Engine Vol'].get('Switch', False):
                    new_ui_data['Engine Mute'] = not new_ui_data.get('Engine Mute', False)
                
                if new_ui_data.get('Engine Mute', False):
                    new_sound_data['Engine Volume'] = 0
                    new_ui_data['Engine Volume'] = 0
                else:
                    volume = max(min(knobs['Engine Vol'].get('Count', 0), 100), 0)
                    new_sound_data['Engine Volume'] = volume
                    new_ui_data['Engine Volume'] = volume
            
            # Music Volume
            if 'Music Vol' in knobs:
                if knobs['Music Vol'].get('Switch', False):
                    new_ui_data['Music Mute'] = not new_ui_data.get('Music Mute', False)
                
                if new_ui_data.get('Music Mute', False):
                    new_sound_data['Music Volume'] = 0
                    new_ui_data['Music Volume'] = 0
                else:
                    volume = max(min(knobs['Music Vol'].get('Count', 0), 100), 0)
                    new_sound_data['Music Volume'] = volume
                    new_ui_data['Music Volume'] = volume
            
            # Engine Tune
            if 'Engine Tune' in knobs:
                if knobs['Engine Tune'].get('Switch', False):
                    new_ui_data['Mode Switch'] = True
                else:
                    tune = max(min(knobs['Engine Tune'].get('Count', 0), 100), 0)
                    new_ui_data['Engine Tune'] = tune
                    new_ui_data['Tune'] = tune
    
    # Process arduino data
    if arduino_data:
        print(f"Arduino Cond: {'Throttle' in arduino_data and 'Speed' in arduino_data and 'Brake' in arduino_data}")
        if 'Throttle' in arduino_data and 'Speed' in arduino_data and 'Brake' in arduino_data:
            accel, speed, rpm = calc_speed_rpm(
                arduino_data.get('Throttle', 0),
                arduino_data.get('Speed', 0),
                cur_gear,
                prev_speed,
                prev_time
            )
            
            new_sound_data['Accel'] = accel
            new_sound_data['Speed'] = speed
            new_ui_data['RPM'] = rpm
            new_ui_data['Speed'] = arduino_data['Speed']
            new_ui_data['Throttle'] = arduino_data['Throttle']
            new_hardware_data['Brake'] = arduino_data['Brake']
            new_hardware_data['Throttle'] = arduino_data['Throttle']
            new_ui_data['Prev Speed'] = speed
            new_ui_data['Prev Time'] = time.time()
            
            print(f"[process_data] Set RPM in ui_data: {rpm}")
    
    # Update shared data with minimal lock time
    if new_ui_data:
        with ui_data_lock:
            ui_data.update(new_ui_data)
            ui_data_ready = True
    
    if new_hardware_data:
        with hardware_data_lock:
            hardware_data.update(new_hardware_data)
            hardware_data_ready = True
    
    if new_sound_data:
        with sound_data_lock:
            sound_data.update(new_sound_data)
            sound_data_ready = True

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

    global pico, arduino, dashboard

    pico = JSONSerialReader("/dev/pico")
    arduino = JSONSerialReader("/dev/arduino")

    # Create dashboard first
    dashboard = dash.F1Dashboard("ui/dashboard_settings.ini", "ui/model.fbx")
    
    # Give dashboard access to data and shutdown event
    dashboard.set_data_source(get_ui_data)
    dashboard.set_interrupted_event(interrupted)

    # Start hardware threads (no lighting or telemetry threads needed)
    hardware_update_thread = threading.Thread(target=hardware_update_loop, daemon=True)
    hardware_update_thread.start()

    hardware_thread = threading.Thread(target=hardware_loop, daemon=True)
    hardware_thread.start()

    audio_thread = threading.Thread(target=audio_loop, daemon=True)
    audio_thread.start()

    # Start dashboard (blocks until window closes)
    dashboard.enable_fullscreen()
    exit_code = dashboard.run()
    
    # After dashboard closes, ensure threads stop
    print("[Main] Dashboard closed, setting interrupted flag...")
    interrupted.set()
    
    # Wait for threads to finish
    time.sleep(0.5)
    
    print(f"Application finished with exit code: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    boot()