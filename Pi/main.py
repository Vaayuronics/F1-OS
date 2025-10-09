from devices.testerial import JSONSerialReader
import engine.soundsys as sound
import time
import threading
import multiprocessing
import sys
import signal
import queue
import os
import platform
import ui.dashboard as dash
from devices.light_manager import LightManager
from devices.button import Button

# GPU configuration is done via environment variables in start.sh
# This avoids polluting the system environment and breaking rpi-connect
# Just print what we detected from the environment
if os.environ.get('QT_QPA_PLATFORM'):
    print(f"[Main] Qt Platform: {os.environ.get('QT_QPA_PLATFORM')}")
if os.environ.get('QT_OPENGL'):
    print(f"[Main] Qt OpenGL Mode: {os.environ.get('QT_OPENGL')}")
if os.environ.get('QSG_RENDER_LOOP'):
    print(f"[Main] Qt Scene Graph: {os.environ.get('QSG_RENDER_LOOP')} render loop")
    
# Verify GPU device exists (informational only)
if os.path.exists('/dev/dri/card0'):
    print("[Main] GPU device detected at /dev/dri/card0")
else:
    print("[Main] WARNING: No GPU device found - see Pi/GPU_SETUP.md")

pico = None
arduino = None
lights = LightManager([16, 6, 5, 7, 24, 23, 22, 27, 17], 
["Green 1", "Green 2", "Green 3", "Green 4", "Blue 1", "Blue 2", "Yellow", "Orange", "Red"])
gear_up = Button(13, "Gear Up")
gear_down = Button(19, "Gear Down")
cur_gear = 0 # Supposedly int operations are atomic in python so this should be fine without a lock
dashboard = None

MAX_THROTTLE_DEG = 135

# Use multiprocessing Manager dict for inter-process communication (avoids GIL)
# This allows UI to run on its own CPU core without being blocked by other threads
# Using dict instead of queue ensures we ALWAYS get latest data, never old queued data
ui_data_dict = None  # Will be initialized in main as Manager().dict()
hardware_data_dict = None
sound_data_dict = None

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
    'Porche': False,
    'Pause': False,
    'Lights': 'Off',
    'Prev Speed': 0,  # Needed to calculate acceleration
    'Prev Time': 0,   # Needed to calculate rate of change
}
persistent_state_lock = None  # Will be initialized as multiprocessing.Lock()

interrupted = None  # Will be initialized as multiprocessing.Event()

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
    lights_count = len(lights)
    rpm_per_light = (dash.MAX_RPM - 100) / lights_count
    
    for i in range(lights_count):
        if rpm >= i * rpm_per_light:
            lights.turn_on(i)
        else:
            lights.turn_off(i)
            
    if rpm > dash.MAX_RPM:
        lights.toggle(lights_count - 1)  # Flash the last light if over

def get_ui_data():
    """Get latest UI data as a regular dict (copy from shared dict)."""
    if ui_data_dict:
        return dict(ui_data_dict)  # Return copy to avoid issues
    return None

def hardware_update_loop(interrupted_event):
    """Continuously poll hardware devices - runs in separate thread within hardware process"""
    global pico, arduino
    while not interrupted_event.is_set():
        try:
            pico_data = pico.poll()
            arduino_data = arduino.poll()
            
            process_data(pico_data, arduino_data)
            time.sleep(0.05)  # 20Hz polling - now won't block UI thanks to separate process
        except Exception as e:
            print(f"[hardware_update_loop] Error: {e}")
            if interrupted_event.is_set():
                break
    
    print("[hardware_update_loop] Thread exiting")

def hardware_loop(interrupted_event):
    '''Complete operations on hardware data and update RPM lights - runs in separate thread within hardware process'''
    global arduino, hardware_data_dict

    lights_boot_anim()
    
    while not interrupted_event.is_set():
        try:
            # Get latest data from shared dict
            if hardware_data_dict:
                data = dict(hardware_data_dict)  # Copy to regular dict
                
                # Update RPM lights on every data update
                rpm = data.get('RPM', 0)
                update_rpm_lights(rpm) #Update rpm even if it is 0 !!
                
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
            
            time.sleep(0.05)  # 20Hz update rate
            
        except Exception as e:
            print(f"[hardware_loop] Error: {e}")
            if interrupted_event.is_set():
                break
    
    print("[hardware_loop] Thread exiting")

def audio_loop(interrupted_event):
    '''Play the sounds chunks and return - runs in separate thread within audio process'''
    global sound_data_dict
    
    sound.load_tracks()
    sound.play_startup_sound()
    
    while not interrupted_event.is_set():
        try:
            # Get latest data from shared dict
            if sound_data_dict:
                data = dict(sound_data_dict)  # Copy to regular dict
                
                if data.get('Start', False):
                    sound.play_f1_start()
                    sound.reset_curtime()  # Reset engine sound time
                    continue
                if data.get('Horn', False):
                    sound.play_horn()
                    continue
                if 'Porche' in data:
                    sound.set_porche_mode(data['Porche'])
                if data.get('Change Track', False):
                    sound.change_track(sound.current_track() + 1)
                #TODO: Implement Launch sound
                if data.get('Launch', False):
                    pass  # Launch control sound
                
                if not data.get('Pause', False):
                    #sound.play_music(data.get('Music Volume', 0))
                    pass
                
                sound.play_engine(data.get('Accel', False), data.get('Play Speed', 0), data.get('Engine Volume', 0))
            
            time.sleep(0.05)  # 20Hz update rate
            
        except Exception as e:
            print(f"[audio_loop] Error: {e}")
            if interrupted_event.is_set():
                break
    
    print("[audio_loop] Thread exiting")

def calc_speed_rpm(throttle: float, speed: float, gear: int, prev_speed: float = 0, prev_time: float = 0, engine_speed : float = 0, motor_rpm: int = 0) -> tuple[bool, float, float]:
    '''Simple RPM calculation based on throttle (in degrees 0-135) and speed.'''
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

    #TODO: change back to speed
    if rpm >= (prev_speed - 500) :
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
                
                # Knob returns absolute position (0-100), no need to store in persistent_state
                tune = max(min(knobs['Engine Tune'].get('Count', 0), 100), 0)
                # Convert to 0-1 range for UI (dashboard expects 0-1, not 0-100)
                new_ui_data['Engine Tune'] = tune / 100.0
    
    # Process arduino data
    if arduino_data:
        if 'Throttle' in arduino_data and 'Speed' in arduino_data and 'Brake' in arduino_data:
            #TODO: Change back to speed from rpm for debug
            accel, play_speed, rpm = calc_speed_rpm(
                arduino_data.get('Throttle', 0),  # Pass raw degrees
                arduino_data.get('Speed', 0),
                cur_gear,
                prev_speed,
                prev_time
            )
            new_sound_data['Accel'] = accel
            new_sound_data['Play Speed'] = play_speed
            new_ui_data['RPM'] = rpm
            new_ui_data['Speed'] = arduino_data['Speed']
            new_ui_data['Throttle'] = arduino_data['Throttle'] / MAX_THROTTLE_DEG  # Convert to 0-1 for UI
            new_hardware_data['Brake'] = arduino_data['Brake']
            new_hardware_data['Throttle'] = arduino_data['Throttle']
            new_hardware_data['RPM'] = rpm
            
            # Update persistent state
            with persistent_state_lock:
                persistent_state['Prev Speed'] = rpm #arduino_data.get('Speed', 0)
                persistent_state['Prev Time'] = time.time()
    
    # Update shared dicts atomically (always latest data, no queueing)
    if new_ui_data:
        ui_data_dict.update(new_ui_data)
    
    if new_hardware_data:
        hardware_data_dict.update(new_hardware_data)
    
    if new_sound_data:
        sound_data_dict.update(new_sound_data)

def lights_boot_anim():
    time.sleep(3)
    for i in range(len(lights)):
        lights.turn_on(i)
        time.sleep(0.5)
    for i in range(5):
        lights.toggle_all()
        time.sleep(0.3)
    lights.turn_off_all()

def hardware_process(interrupted_event, ui_dict, hw_dict, sound_dict, state_lock):
    """Main hardware process - runs on separate CPU core, avoiding GIL with UI"""
    global pico, arduino, lights, ui_data_dict, hardware_data_dict, sound_data_dict, persistent_state_lock
    
    # Set up process-local variables
    ui_data_dict = ui_dict
    hardware_data_dict = hw_dict
    sound_data_dict = sound_dict
    persistent_state_lock = state_lock
    
    print("[Hardware Process] Starting...")
    
    # Initialize hardware devices in this process
    try:
        pico = JSONSerialReader("/dev/pico")
        arduino = JSONSerialReader("/dev/arduino")
        lights = LightManager([16, 6, 5, 7, 24, 23, 22, 27, 17], 
                             ["Green 1", "Green 2", "Green 3", "Green 4", "Blue 1", "Blue 2", "Yellow", "Orange", "Red"])
    except Exception as e:
        print(f"[Hardware Process] Error initializing devices: {e}")
        return
    
    # Create local threading event for threads within this process
    local_interrupted = threading.Event()
    
    # Start hardware threads within this process (NOT daemon - we need to join them)
    hardware_update_thread = threading.Thread(target=hardware_update_loop, args=(local_interrupted,), daemon=False)
    hardware_update_thread.start()
    
    hardware_thread = threading.Thread(target=hardware_loop, args=(local_interrupted,), daemon=False)
    hardware_thread.start()
    
    # Wait for shutdown signal from main process
    try:
        interrupted_event.wait()
    except KeyboardInterrupt:
        pass
    
    print("[Hardware Process] Shutting down...")
    local_interrupted.set()
    
    # Wait for threads to exit (give them 3 seconds)
    print("[Hardware Process] Waiting for threads to exit...")
    hardware_update_thread.join(timeout=3)
    hardware_thread.join(timeout=3)
    
    if hardware_update_thread.is_alive():
        print("[Hardware Process] WARNING: hardware_update_thread still alive")
    if hardware_thread.is_alive():
        print("[Hardware Process] WARNING: hardware_thread still alive")
    
    # Cleanup hardware
    print("[Hardware Process] Cleaning up hardware...")
    try:
        if lights:
            lights.turn_off_all()
            lights.cleanup()
    except Exception as e:
        print(f"[Hardware Process] Error cleaning up lights: {e}")
    
    try:
        if pico:
            pico.send({"command": "stop"})
            pico.ser.close()
    except Exception as e:
        print(f"[Hardware Process] Error closing pico: {e}")
    
    try:
        if arduino:
            arduino.send({"command": "stop"})
            arduino.ser.close()
    except Exception as e:
        print(f"[Hardware Process] Error closing arduino: {e}")
    
    print("[Hardware Process] Exited cleanly")

def audio_process(interrupted_event, sound_dict):
    """Main audio process - runs on separate CPU core"""
    global sound_data_dict
    
    sound_data_dict = sound_dict
    
    print("[Audio Process] Starting...")
    
    # Create local threading event
    local_interrupted = threading.Event()
    
    # Start audio thread within this process (NOT daemon - we need to join it)
    audio_thread = threading.Thread(target=audio_loop, args=(local_interrupted,), daemon=False)
    audio_thread.start()
    
    # Wait for shutdown signal
    try:
        interrupted_event.wait()
    except KeyboardInterrupt:
        pass
    
    print("[Audio Process] Shutting down...")
    local_interrupted.set()
    
    # Wait for thread to exit (give it 3 seconds)
    print("[Audio Process] Waiting for audio thread to exit...")
    audio_thread.join(timeout=3)
    
    if audio_thread.is_alive():
        print("[Audio Process] WARNING: audio_thread still alive")
    
    print("[Audio Process] Exited cleanly")

def boot():
    print("Booting up system with multiprocessing (UI on separate CPU core)...")

    global dashboard, interrupted, ui_data_dict, hardware_data_dict, sound_data_dict, persistent_state_lock
    
    # Initialize multiprocessing primitives
    interrupted = multiprocessing.Event()
    manager = multiprocessing.Manager()
    ui_data_dict = manager.dict()
    hardware_data_dict = manager.dict()
    sound_data_dict = manager.dict()
    persistent_state_lock = multiprocessing.Lock()
    
    hw_process = None
    audio_proc = None
    
    try:
        # Start hardware process (runs on separate CPU core - no GIL conflict!)
        hw_process = multiprocessing.Process(
            target=hardware_process,
            args=(interrupted, ui_data_dict, hardware_data_dict, sound_data_dict, persistent_state_lock),
            daemon=False
        )
        hw_process.start()
        print(f"[Main] Hardware process started (PID: {hw_process.pid})")
        
        # Start audio process (runs on separate CPU core)
        audio_proc = multiprocessing.Process(
            target=audio_process,
            args=(interrupted, sound_data_dict),
            daemon=False
        )
        audio_proc.start()
        print(f"[Main] Audio process started (PID: {audio_proc.pid})")
        
        # Create dashboard in main process (gets its own CPU core!)
        dashboard = dash.F1Dashboard("ui/dashboard_settings.ini")
        
        # Give dashboard access to data and shutdown event
        dashboard.set_data_source(get_ui_data)
        dashboard.set_interrupted_event(interrupted)

        # Start dashboard (blocks until window closes) - runs smoothly on its own core
        dashboard.enable_fullscreen()
        print("[Main] Starting UI (runs on main process with dedicated CPU core)")
        exit_code = dashboard.run()
        
    except KeyboardInterrupt:
        print("\n[Main] Keyboard interrupt received")
        exit_code = 0
    except Exception as e:
        print(f"[Main] Error during execution: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        # CRITICAL: Ensure cleanup happens no matter what
        print("[Main] Shutting down all processes...")
        
        # Signal all processes to stop
        interrupted.set()
        
        # Give processes time to exit gracefully
        print("[Main] Waiting for processes to exit gracefully (5 seconds)...")
        
        if hw_process and hw_process.is_alive():
            hw_process.join(timeout=5)
            if hw_process.is_alive():
                print("[Main] Hardware process didn't exit, terminating...")
                hw_process.terminate()
                hw_process.join(timeout=2)
                if hw_process.is_alive():
                    print("[Main] Hardware process still alive, killing...")
                    hw_process.kill()
                    hw_process.join()
        
        if audio_proc and audio_proc.is_alive():
            audio_proc.join(timeout=5)
            if audio_proc.is_alive():
                print("[Main] Audio process didn't exit, terminating...")
                audio_proc.terminate()
                audio_proc.join(timeout=2)
                if audio_proc.is_alive():
                    print("[Main] Audio process still alive, killing...")
                    audio_proc.kill()
                    audio_proc.join()
        
        # Shut down the manager to release resources
        print("[Main] Shutting down multiprocessing manager...")
        manager.shutdown()
        
        print(f"[Main] All processes terminated. Exit code: {exit_code}")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    # Required for multiprocessing on Windows/macOS (safe to have on Linux too)
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Already set, ignore
        pass
    
    # Set up proper signal handling
    def emergency_shutdown(signum, frame):
        print("\n[Main] Emergency shutdown requested!")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, emergency_shutdown)
    signal.signal(signal.SIGTERM, emergency_shutdown)
    
    boot()