from jerial import JSONSerialReader
import time
import threading
import sys
import signal
from ui.dashboard import F1Dashboard, REFRESH_RATE

'''
TODO: Check to see if the usb ports on the Raspberry Pi are still not working with tty.
'''

pico = JSONSerialReader("/dev/pico")
arduino = JSONSerialReader("/dev/arduino")
dashboard = F1Dashboard("ui/dashboard_settings.ini", "ui/model.fbx")
interrupted = False

def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) gracefully"""
    global interrupted, dashboard
    print("\nReceived interrupt signal. Shutting down gracefully...")
    interrupted = True
    pico.ser.close()
    arduino.ser.close()
    if dashboard:
        dashboard.close()  # Close the dashboard window
    sys.exit(0)  # Exit cleanly

# Set up signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)

def telemetry_update_loop():
    """Continuously update telemetry data"""
    global interrupted
    while not interrupted:
        pico_data = pico.poll()
        arduino_data = arduino.poll()
        if pico_data and arduino_data:
            combined_data = {**pico_data, **arduino_data}
            dashboard.set_data_thread_safe(combined_data)
        time.sleep(REFRESH_RATE)  # Update at ~58Hz to match display refresh rate

if __name__ == "__main__":
    print("Booting up system.")

    telemetry_thread = threading.Thread(target=telemetry_update_loop, daemon=True)
    telemetry_thread.start()

    dashboard.enable_fullscreen()
    exit_code = dashboard.run()
    while exit_code != 0:
        print("Application exited with code:", exit_code, "restarting...")
        exit_code = dashboard.run()
    print("Application finished with exit code:", exit_code)
    sys.exit(exit_code)