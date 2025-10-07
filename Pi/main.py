from devices.testerial import JSONSerialReader
import engine.soundsys as sound
import time
import threading
import sys
import signal
import queue
import ui.dashboard as dash
from devices.light_manager import LightManager
from devices.button import Button

pico = None
arduino = None
lights = LightManager([16, 6, 5, 7, 24, 23, 22, 27, 17], 
                      ["Green 1", "Green 2", "Green 3", "Green 4", "Blue 1", "Blue 2", "Yellow", "Orange", "Red"])
gear_up = Button(13, "Gear Up")
gear_down = Button(19, "Gear Down")
cur_gear = 0 # Supposedly int operations are atomic in python so this should be fine without a lock
dashboard = None

MAX_THROTTLE_DEG = 135

# Use queues for thread-safe data passing
# maxsize=5 allows for small bursts without dropping data
ui_data_queue = queue.Queue(maxsize=5)
hardware_data_queue = queue.Queue(maxsize=5)
sound_data_queue = queue.Queue(maxsize=5)

# Persistent state dictionary with lock
persistent_state = {
    'Shift Emulation': False,
    'Headlights': False,
    'Hazards': False,
    'Auto Turn Signal': False,
    'DRS': False,
    'Started': False,
    'Engine Mute': False,
    'Music Mute': False,
    'Tune': 0,
    'Porche': False,
    'Pause': False,
    'Lights': 'Off',
    'Prev Speed': 0,
    'Prev Time': 0,
}
persistent_state_lock = threading.Lock()

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
    
    # Calculate how many lights should be on based on current RPM
    lights_to_activate = int(rpm / rpm_per_light)
    
    for i in range(lights_count):
        if i < lights_to_activate:
            lights.turn_on(i)
        else:
            lights.turn_off(i)
            
    # Flash the last light if over max RPM
    if rpm > dash.MAX_RPM:
        lights.toggle(lights_count - 1)

def get_ui_data():
    """Get latest UI data without blocking."""
    try:
        return ui_data_queue.get_nowait()
    except queue.Empty:
        return None

def hardware_update_loop():
    """Continuously poll hardware devices"""
    global interrupted, pico, arduino
    while not interrupted.is_set():
        try:
            pico_data = pico.poll()
            arduino_data = arduino.poll()
            process_data(pico_data, arduino_data)
            time.sleep(0.05)  # 20Hz polling - responsive but not wasteful
        except Exception as e:
            print(f"[hardware_update_loop] Error: {e}")
            if interrupted.is_set():
                break
    
    print("[hardware_update_loop] Thread exiting")

def hardware_loop():
    '''Complete operations on hardware data and update RPM lights'''
    global interrupted, arduino

    lights_boot_anim()
    
    while not interrupted.is_set():
        try:
            # Wait for new data with timeout
            try:
                data = hardware_data_queue.get(timeout=0.1)
                
                # Update RPM lights on every data update
                rpm = data.get('RPM', 0)
                update_rpm_lights(rpm)
                
                # Process hardware commands
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

                if data.get('Launch', False):
                    # Activate Launch Control
                    pass

                if data.get('START', False):
                    # Start throttle
                    arduino.send({"command": "tare"})

                if data.get('STOP', False):
                    # Emergency stop throttle
                    pass
                    
            except queue.Empty:
                continue  # No new data, keep waiting
            
        except Exception as e:
            print(f"[hardware_loop] Error: {e}")
            if interrupted.is_set():
                break
    
    print("[hardware_loop] Thread exiting")

def audio_loop():
    '''Play the sounds chunks and return '''
    global interrupted
    sound.load_tracks()
    sound.play_startup_sound()
    
    while not interrupted.is_set():
        try:
            # Wait for new data with timeout
            try:
                data = sound_data_queue.get(timeout=0.1)
                
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
                
            except queue.Empty:
                continue  # No new data, keep waiting
            
        except Exception as e:
            print(f"[audio_loop] Error: {e}")
            if interrupted.is_set():
                break
    
    print("[audio_loop] Thread exiting")

def calc_speed_rpm(throttle_degrees: float, speed: float, gear: int, prev_speed: float = 0, prev_time: float = 0, engine_speed : float = 0, motor_rpm: int = 0) -> tuple[bool, float, float]:
    '''Simple RPM calculation based on throttle (in degrees 0-135) and speed.'''
    accel = False
    play_speed = 1.0
    rpm = 0.0

    # Convert throttle from degrees to percentage (0-100)
    throttle_percent = (throttle_degrees / MAX_THROTTLE_DEG) * 100

    rate = 0
    if prev_time > 0 and (time.time() - prev_time) > 0:
        rate = (speed - prev_speed) / (time.time() - prev_time)

    #TODO: Finish calculations

    if gear == 0:
        rpm = throttle_percent * 103.7
    else:
        # Add proper gear-based RPM calculation here
        rpm = (speed * 60 * gear * 10) + (throttle_percent * 50)

    if speed >= prev_speed:
        accel = True

    return accel, play_speed, rpm

def process_data(pico_data, arduino_data):
    """Combine and process data from pico and arduino.\n
    Operate on any hardware instructions.\n
    Return combined data for UI."""
    global cur_gear, persistent_state, persistent_state_lock

    # Create new data dicts to populate
    new_ui_data = {}
    new_hardware_data = {}
    new_sound_data = {}
    
    # Get persistent state once with lock
    with persistent_state_lock:
        prev_speed = persistent_state['Prev Speed']
        prev_time = persistent_state['Prev Time']
        shift_emulation = persistent_state['Shift Emulation']
        headlights = persistent_state['Headlights']
        hazards = persistent_state['Hazards']
        auto_turn_signal = persistent_state['Auto Turn Signal']
        drs = persistent_state['DRS']
        started = persistent_state['Started']
        engine_mute = persistent_state['Engine Mute']
        music_mute = persistent_state['Music Mute']
        tune = persistent_state['Tune']
        porche = persistent_state['Porche']
        pause = persistent_state['Pause']
        lights_state = persistent_state['Lights']

    # Process pico data
    if pico_data:
        '''User button inputs'''
        if 'Buttons' in pico_data:
            buttons = pico_data['Buttons']
            
            # Shift Emulation Toggle
            if buttons.get('Shift Emulation Toggle', {}).get('Pressed', False):
                shift_emulation = not shift_emulation
                with persistent_state_lock:
                    persistent_state['Shift Emulation'] = shift_emulation
                new_ui_data['Shift Emulation'] = shift_emulation
                new_ui_data['Alert Title'] = f"Shift Emulation {'ON' if shift_emulation else 'OFF'}"
                new_ui_data['Alert Message'] = "Shift emulation mode has been toggled."
            
            # Headlights
            if buttons.get('Headlights', {}).get('Pressed', False):
                headlights = not headlights
                lights_state = "Headlights" if headlights else "Off"
                with persistent_state_lock:
                    persistent_state['Headlights'] = headlights
                    persistent_state['Lights'] = lights_state
                new_ui_data['Headlights'] = headlights
                new_ui_data['Alert Title'] = f"Headlights {'ON' if headlights else 'OFF'}"
                new_ui_data['Alert Message'] = "Headlights and backlights are toggled."
                new_hardware_data['Lights'] = lights_state
            
            # Hazards
            if buttons.get('Hazards', {}).get('Pressed', False):
                hazards = not hazards
                if hazards:
                    lights_state = "Hazards"
                elif not headlights:
                    lights_state = "Off"
                with persistent_state_lock:
                    persistent_state['Hazards'] = hazards
                    persistent_state['Lights'] = lights_state
                new_ui_data['Hazards'] = hazards
                new_ui_data['Alert Title'] = f"Hazards {'ON' if hazards else 'OFF'}"
                new_ui_data['Alert Message'] = "All lights are flashing."
                new_hardware_data['Lights'] = lights_state
            
            # Change Engine
            if buttons.get('Change Engine', {}).get('Pressed', False):
                porche = not porche
                with persistent_state_lock:
                    persistent_state['Porche'] = porche
                new_sound_data['Porche'] = porche
                new_ui_data['Alert Title'] = "Engine Changed"
                new_ui_data['Alert Message'] = f"Engine mode changed to {'Porche' if porche else 'F1 v10'}."
            
            # Change Music
            if buttons.get('Change Music', {}).get('Pressed', False):
                new_sound_data["Change Track"] = True
            else:
                new_sound_data["Change Track"] = False
            
            # DRS
            if buttons.get('DRS', {}).get('Pressed', False):
                drs = not drs
                with persistent_state_lock:
                    persistent_state['DRS'] = drs
                new_ui_data['DRS'] = drs
                new_ui_data['Alert Title'] = f"DRS {'ON' if drs else 'OFF'}"
                new_ui_data['Alert Message'] = "Drag Reduction System has been toggled."
                new_hardware_data['DRS'] = drs
            
            # Start
            start_btn = buttons.get('Start', {})
            if start_btn.get('Pressed', False):
                if not started:
                    started = True
                    with persistent_state_lock:
                        persistent_state['Started'] = started
                    new_sound_data['Start'] = True
                    new_ui_data['Alert Title'] = "Car Started"
                    new_ui_data['Alert Message'] = "Car has been started."
                    new_ui_data['Started'] = started
                    new_hardware_data['START'] = True
            
            # Launch control when held down after started
            if start_btn.get('Down', False) and started:
                new_sound_data['Launch'] = True
            else:
                new_sound_data['Launch'] = False
                new_sound_data['Start'] = False
            
            # Stop (use Pressed for alert, Down for continuous stop signal)
            stop_btn = buttons.get('Stop', {})
            if stop_btn.get('Pressed', False):
                started = False
                with persistent_state_lock:
                    persistent_state['Started'] = started
                new_ui_data['Alert Title'] = "Car Stopped"
                new_ui_data['Alert Message'] = "Car has been turned off."
                new_ui_data['Started'] = started

            if stop_btn.get('Down', False):
                new_hardware_data['STOP'] = stop_btn.get('Down', False)

            # Play/Pause
            if buttons.get('Play/Pause', {}).get('Pressed', False):
                pause = not pause
                with persistent_state_lock:
                    persistent_state['Pause'] = pause
                new_sound_data['Pause'] = pause
            
            # Auto Turn Signal Toggle
            if buttons.get('Auto Turn Signal Toggle', {}).get('Pressed', False):
                auto_turn_signal = not auto_turn_signal
                with persistent_state_lock:
                    persistent_state['Auto Turn Signal'] = auto_turn_signal
                new_ui_data['Auto Turn Signal'] = auto_turn_signal
                new_ui_data['Alert Title'] = f"Auto Turn Signal {'ON' if auto_turn_signal else 'OFF'}"
                new_ui_data['Alert Message'] = "Auto turn signal has been toggled."
            
            # Horn (momentary - use Down for continuous sound while held)
            new_sound_data['Horn'] = buttons.get('Horn', {}).get('Down', False)
        
        # Process knobs
        if 'Knobs' in pico_data:
            knobs = pico_data['Knobs']
            
            # Engine Volume
            if 'Engine Vol' in knobs:
                if knobs['Engine Vol'].get('Pressed', False):
                    engine_mute = not engine_mute
                    with persistent_state_lock:
                        persistent_state['Engine Mute'] = engine_mute
                    new_ui_data['Engine Mute'] = engine_mute
                
                if engine_mute:
                    new_sound_data['Engine Volume'] = 0
                    new_ui_data['Engine Volume'] = 0
                else:
                    volume = max(min(knobs['Engine Vol'].get('Count', 0), 100), 0)
                    new_sound_data['Engine Volume'] = volume
                    new_ui_data['Engine Volume'] = volume
            
            # Music Volume
            if 'Music Vol' in knobs:
                if knobs['Music Vol'].get('Pressed', False):
                    music_mute = not music_mute
                    with persistent_state_lock:
                        persistent_state['Music Mute'] = music_mute
                    new_ui_data['Music Mute'] = music_mute
                
                if music_mute:
                    new_sound_data['Music Volume'] = 0
                    new_ui_data['Music Volume'] = 0
                else:
                    volume = max(min(knobs['Music Vol'].get('Count', 0), 100), 0)
                    new_sound_data['Music Volume'] = volume
                    new_ui_data['Music Volume'] = volume
            
            # Engine Tune
            if 'Engine Tune' in knobs:
                if knobs['Engine Tune'].get('Pressed', False):
                    new_ui_data['Mode Switch'] = True
                
                tune = max(min(knobs['Engine Tune'].get('Count', 0), 100), 0)
                with persistent_state_lock:
                    persistent_state['Tune'] = tune
                new_ui_data['Engine Tune'] = tune
                new_ui_data['Tune'] = tune
    
    # Process arduino data
    if arduino_data:
        if 'Throttle' in arduino_data and 'Speed' in arduino_data and 'Brake' in arduino_data:
            accel, speed, rpm = calc_speed_rpm(
                arduino_data.get('Throttle', 0),  # Pass raw degrees
                arduino_data.get('Speed', 0),
                cur_gear,
                prev_speed,
                prev_time
            )
            
            new_sound_data['Accel'] = accel
            new_sound_data['Speed'] = speed
            new_ui_data['RPM'] = rpm
            new_ui_data['Speed'] = arduino_data['Speed']
            new_ui_data['Throttle'] = arduino_data['Throttle'] / MAX_THROTTLE_DEG  # Convert to 0-1 for UI
            new_hardware_data['Brake'] = arduino_data['Brake']
            new_hardware_data['Throttle'] = arduino_data['Throttle']
            new_hardware_data['RPM'] = rpm
            
            # Update persistent state
            with persistent_state_lock:
                persistent_state['Prev Speed'] = speed
                persistent_state['Prev Time'] = time.time()
    
    # Push to queues (replaces old data if queue is full)
    # Always prioritize latest data by removing old first
    if new_ui_data:
        if ui_data_queue.full():
            try:
                ui_data_queue.get_nowait()  # Remove old data first
            except queue.Empty:
                pass
        try:
            ui_data_queue.put_nowait(new_ui_data)
        except queue.Full:
            pass  # Should never happen after get_nowait
    
    if new_hardware_data:
        if hardware_data_queue.full():
            try:
                hardware_data_queue.get_nowait()  # Remove old data first
            except queue.Empty:
                pass
        try:
            hardware_data_queue.put_nowait(new_hardware_data)
        except queue.Full:
            pass
    
    if new_sound_data:
        if sound_data_queue.full():
            try:
                sound_data_queue.get_nowait()  # Remove old data first
            except queue.Empty:
                pass
        try:
            sound_data_queue.put_nowait(new_sound_data)
        except queue.Full:
            pass

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

    global pico, arduino, dashboard, lights

    pico = JSONSerialReader("/dev/pico")
    arduino = JSONSerialReader("/dev/arduino")

    # Create dashboard first (no 3D model needed - using 2D vector graphics)
    dashboard = dash.F1Dashboard("ui/dashboard_settings.ini")
    
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
    lights.turn_off_all()
    sys.exit(exit_code)

if __name__ == "__main__":
    boot()