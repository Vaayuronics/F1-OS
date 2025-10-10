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
ui_data_dict = None  # Will be initialized in main as Manager().dict()
hardware_data_dict = None
sound_data_dict = None

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
        data = dict(ui_data_dict)
        # Clear alert messages after reading
        ui_data_dict["Alert Title"] = ""
        ui_data_dict["Alert Message"] = ""
        return data  # Return copy to avoid issues
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
                
                # Update RPM lights on every data update (continuous)
                rpm = data.get('RPM', 0)
                update_rpm_lights(rpm) #Update rpm even if it is 0 !!
                
                # Process hardware commands
                #TODO: Process hardware data
                # Check persistent flags in data for operations (level-triggered)
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

                # Edge-triggered events (reset after consuming)
                if data.get('START', False):
                    # Start throttle
                    arduino.send({"command": "tare"})
                    hardware_data_dict['START'] = False  # Reset after consuming

                if data.get('STOP', False):
                    # Emergency stop throttle
                    pass  # STOP is level-triggered (stays on while held)
            
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
                
                # Handle edge-triggered events (reset after consuming)
                if data.get('Start', False):
                    sound.play_f1_start()
                    sound.reset_curtime()  # Reset engine sound time
                    sound_data_dict['Start'] = False  # Reset after consuming
                    continue
                if data.get('Horn', False):
                    sound.play_horn()
                    continue  # Horn is level-triggered (stays on while held)
                if 'Porche' in data:
                    sound.set_porche_mode(data['Porche'])
                if data.get('Change Track', False):
                    sound.change_track(sound.current_track() + 1)
                    sound_data_dict['Change Track'] = False  # Reset after consuming
                #TODO: Implement Launch sound
                if data.get('Launch', False):
                    pass  # Launch control sound
                if not data.get('Pause', False):
                    #sound.play_music(data.get('Music Volume', 0))
                    pass
                
                # Pass accel state (True/False/None), play speed, idle flag, and volume
                sound.play_engine(
                    data.get('Accel', False), 
                    data.get('Play Speed', 1.0),
                    data.get('Engine Volume', 0),
                    data.get('Idle', False)
                )
            
            time.sleep(0.03)
            
        except Exception as e:
            print(f"[audio_loop] Error: {e}")
            if interrupted_event.is_set():
                break
    
    print("[audio_loop] Thread exiting")

def calc_speed_rpm(throttle: float, speed: float, gear: int, prev_rpm: float = 0, prev_time: float = 0, motor_rpm: int = 0) -> tuple[bool, bool, float, float]:
    '''Simple RPM calculation based on throttle (in degrees 0-135) and speed.
    Acceleration is detected when RPM increases by at least 300 RPM.
    Idle is True when RPM <= 2000 (forces idle sound regardless of accel state).
    '''
    accel = False
    play_speed = 1.0
    rpm = 0.0
    idle = False

    #TODO: Finish calculations when real speed sensor is available

    # For now, RPM is proportional to throttle for testing
    if gear == 0:
        rpm = throttle * 103.7
    else:
        # Add proper gear-based RPM calculation here
        rpm = (speed * 60 * gear * 10) + (throttle * 50)

    # Check if we're at idle RPM (force idle sound)
    if rpm <= 2000:
        idle = True
    
    # Detect acceleration: RPM must change by at least 300 to be significant
    rpm_change = rpm - prev_rpm
    if rpm_change >= 300:
        accel = True  # Accelerating
    elif rpm_change <= -300:
        accel = False  # Decelerating
    else:
        # No significant change - loop the current/previous chunks
        accel = None  # None indicates no significant change (loop current position)

    return accel, idle, play_speed, rpm

def process_data(pico_data, arduino_data):
    """Combine and process data from pico and arduino.
    Operate on any hardware instructions.
    Update shared dicts directly - consumers will reset what they've handled."""
    global cur_gear, ui_data_dict, hardware_data_dict, sound_data_dict

    # Get current persistent values from shared dicts (they persist until explicitly reset)
    prev_time = sound_data_dict.get('Prev Time', 0)
    prev_rpm = sound_data_dict.get('Prev RPM', 0)
    shift_emulation = ui_data_dict.get('Shift Emulation', False)
    headlights = ui_data_dict.get('Headlights', False)
    hazards = ui_data_dict.get('Hazards', False)
    auto_turn_signal = ui_data_dict.get('Auto Turn Signal', False)
    drs = ui_data_dict.get('DRS', False)
    started = ui_data_dict.get('Started', False)
    engine_mute = sound_data_dict.get('Engine Mute', False)
    music_mute = sound_data_dict.get('Music Mute', False)
    porche = sound_data_dict.get('Porche', False)
    pause = sound_data_dict.get('Pause', False)
    lights_state = hardware_data_dict.get('Lights', 'Off')

    # Process pico data
    if pico_data:
        '''User button inputs'''
        if 'Buttons' in pico_data:
            buttons = pico_data['Buttons']
            
            # Shift Emulation Toggle
            if buttons.get('Shift Emulation Toggle', {}).get('Pressed', False):
                shift_emulation = not shift_emulation
                ui_data_dict['Shift Emulation'] = shift_emulation
                ui_data_dict['Alert Title'] = f"Shift Emulation {'ON' if shift_emulation else 'OFF'}"
                ui_data_dict['Alert Message'] = "Shift emulation mode has been toggled."
            
            # Headlights
            if buttons.get('Headlights', {}).get('Pressed', False):
                headlights = not headlights
                lights_state = "Headlights" if headlights else "Off"
                ui_data_dict['Headlights'] = headlights
                ui_data_dict['Alert Title'] = f"Headlights {'ON' if headlights else 'OFF'}"
                ui_data_dict['Alert Message'] = "Headlights and backlights are toggled."
                hardware_data_dict['Lights'] = lights_state
            
            # Hazards
            if buttons.get('Hazards', {}).get('Pressed', False):
                hazards = not hazards
                if hazards:
                    lights_state = "Hazards"
                elif not headlights:
                    lights_state = "Off"
                ui_data_dict['Hazards'] = hazards
                ui_data_dict['Alert Title'] = f"Hazards {'ON' if hazards else 'OFF'}"
                ui_data_dict['Alert Message'] = "All lights are flashing."
                hardware_data_dict['Lights'] = lights_state
            
            # Change Engine
            if buttons.get('Change Engine', {}).get('Pressed', False):
                porche = not porche
                sound_data_dict['Porche'] = porche
                ui_data_dict['Alert Title'] = "Engine Changed"
                ui_data_dict['Alert Message'] = f"Engine mode changed to {'Porche' if porche else 'F1 v10'}."
                print("[Remove Me] Giving engine change alert")
            
            # Change Music
            if buttons.get('Change Music', {}).get('Pressed', False):
                sound_data_dict["Change Track"] = True
            
            # DRS
            if buttons.get('DRS', {}).get('Pressed', False):
                drs = not drs
                ui_data_dict['DRS'] = drs
                ui_data_dict['Alert Title'] = f"DRS Changed"
                ui_data_dict['Alert Message'] = f"Drag Reduction System is now {'ACTIVE' if drs else 'INACTIVE'}."
                hardware_data_dict['DRS'] = drs
            
            # Start
            start_btn = buttons.get('Start', {})
            if start_btn.get('Pressed', False):
                if not started:
                    started = True
                    sound_data_dict['Start'] = True
                    ui_data_dict['Alert Title'] = "Car Started"
                    ui_data_dict['Alert Message'] = "Car has been started."
                    ui_data_dict['Started'] = started
                    hardware_data_dict['START'] = True
            
            # Launch control when held down after started
            if start_btn.get('Down', False) and started:
                sound_data_dict['Launch'] = True
            else:
                sound_data_dict['Launch'] = False
                sound_data_dict['Start'] = False
            
            # Stop (use Pressed for alert, Down for continuous stop signal)
            stop_btn = buttons.get('Stop', {})
            if stop_btn.get('Pressed', False):
                started = False
                ui_data_dict['Alert Title'] = "Car Stopped"
                ui_data_dict['Alert Message'] = "Car has been turned off."
                ui_data_dict['Started'] = started

            if stop_btn.get('Down', False):
                hardware_data_dict['STOP'] = stop_btn.get('Down', False)

            # Play/Pause
            if buttons.get('Play/Pause', {}).get('Pressed', False):
                pause = not pause
                sound_data_dict['Pause'] = pause
            
            # Auto Turn Signal Toggle
            if buttons.get('Auto Turn Signal Toggle', {}).get('Pressed', False):
                auto_turn_signal = not auto_turn_signal
                ui_data_dict['Auto Turn Signal'] = auto_turn_signal
                ui_data_dict['Alert Title'] = f"Auto Turn Signal Changed"
                ui_data_dict['Alert Message'] = f"Auto turn signal is now {'ACTIVE' if auto_turn_signal else 'INACTIVE'}."

            # Horn (momentary - use Down for continuous sound while held)
            sound_data_dict['Horn'] = buttons.get('Horn', {}).get('Down', False)
        
        # Process knobs
        if 'Knobs' in pico_data:
            knobs = pico_data['Knobs']
            
            # Engine Volume
            if 'Engine Vol' in knobs:
                if knobs['Engine Vol'].get('Pressed', False):
                    engine_mute = not engine_mute
                    ui_data_dict['Engine Mute'] = engine_mute
                
                if engine_mute:
                    sound_data_dict['Engine Volume'] = 0
                    ui_data_dict['Engine Volume'] = 0
                else:
                    volume = max(min(knobs['Engine Vol'].get('Count', 0), 100), 0)
                    sound_data_dict['Engine Volume'] = volume
                    ui_data_dict['Engine Volume'] = volume
            
            # Music Volume
            if 'Music Vol' in knobs:
                if knobs['Music Vol'].get('Pressed', False):
                    music_mute = not music_mute
                    ui_data_dict['Music Mute'] = music_mute
                
                if music_mute:
                    sound_data_dict['Music Volume'] = 0
                    ui_data_dict['Music Volume'] = 0
                else:
                    volume = max(min(knobs['Music Vol'].get('Count', 0), 100), 0)
                    sound_data_dict['Music Volume'] = volume
                    ui_data_dict['Music Volume'] = volume
            
            # Engine Tune
            if 'Engine Tune' in knobs:
                if knobs['Engine Tune'].get('Pressed', False):
                    ui_data_dict['Mode Switch'] = True
                
                # Knob returns absolute position (0-100)
                tune = max(min(knobs['Engine Tune'].get('Count', 0), 100), 0)
                # Convert to 0-1 range for UI (dashboard expects 0-1, not 0-100)
                ui_data_dict['Engine Tune'] = tune / 100.0
    
    # Process arduino data
    if arduino_data:
        if 'Throttle' in arduino_data and 'Speed' in arduino_data and 'Brake' in arduino_data:
            accel, idle, play_speed, rpm = calc_speed_rpm(
                arduino_data.get('Throttle', 0),  # Pass raw degrees
                arduino_data.get('Speed', 0),
                cur_gear,
                prev_rpm,
                prev_time
            )
            # accel can be True (accelerating), False (decelerating), or None (no significant change/loop)
            sound_data_dict['Accel'] = accel
            sound_data_dict['Play Speed'] = play_speed
            sound_data_dict['Idle'] = idle  # Force idle sound when RPM <= 2000
            ui_data_dict['RPM'] = rpm
            ui_data_dict['Speed'] = arduino_data['Speed']
            ui_data_dict['Throttle'] = arduino_data['Throttle'] / MAX_THROTTLE_DEG  # Convert to 0-1 for UI
            hardware_data_dict['Brake'] = arduino_data['Brake']
            hardware_data_dict['Throttle'] = arduino_data['Throttle']
            hardware_data_dict['RPM'] = rpm
            
            # Update persistent values for next calculation
            sound_data_dict['Prev RPM'] = rpm
            sound_data_dict['Prev Time'] = time.time()

def lights_boot_anim():
    time.sleep(3)
    for i in range(len(lights)):
        lights.turn_on(i)
        time.sleep(0.5)
    for i in range(5):
        lights.toggle_all()
        time.sleep(0.3)
    lights.turn_off_all()

def hardware_process(interrupted_event, ui_dict, hw_dict, sound_dict):
    """Main hardware process - runs on separate CPU core, avoiding GIL with UI"""
    global pico, arduino, lights, ui_data_dict, hardware_data_dict, sound_data_dict
    
    # Set up process-local variables
    ui_data_dict = ui_dict
    hardware_data_dict = hw_dict
    sound_data_dict = sound_dict
    
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

    global dashboard, interrupted, ui_data_dict, hardware_data_dict, sound_data_dict
    
    # Initialize multiprocessing primitives
    interrupted = multiprocessing.Event()
    manager = multiprocessing.Manager()
    ui_data_dict = manager.dict()
    hardware_data_dict = manager.dict()
    sound_data_dict = manager.dict()
    
    hw_process = None
    audio_proc = None
    
    try:
        # Start hardware process (runs on separate CPU core - no GIL conflict!)
        hw_process = multiprocessing.Process(
            target=hardware_process,
            args=(interrupted, ui_data_dict, hardware_data_dict, sound_data_dict),
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
        #dashboard.enable_fullscreen()
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