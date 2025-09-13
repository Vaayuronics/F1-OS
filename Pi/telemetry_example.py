#!/usr/bin/env python3
"""
Example of how to update dashboard data from external processes/threads
"""
import time
import threading
import random
from ui.dashboard import F1Dashboard
import sys

dashboard = None

def update_dashboard_via_function():
    """Example: Update dashboard using the direct dashboard instance"""
    global dashboard
    if dashboard:
        # Thread-safe data update
        data = {
            'rpm': random.randint(1000, 14000),
            'speed': random.randint(0, 120),
            'throttle': random.random(),
            'tune': random.random(),
            'gear': random.randint(-1, 6),  # -1=Reverse, 0=Neutral, 1-6=Gears
            'battery': random.randint(20, 100),
            'wheel_rotation': random.randint(0, 360)  # Add wheel rotation
        }
        dashboard.set_data_thread_safe(data)
        dashboard.set_data_thread_safe(data)
        print(f"Updated dashboard: RPM={data['rpm']}, Speed={data['speed']}, Gear={data['gear']}")

def telemetry_update_loop():
    """Continuously update telemetry data"""
    while True:
        update_dashboard_via_function()
        time.sleep(1/58)  # Update at ~58Hz to match display refresh rate

def start_dashboard():
    """Start the dashboard in the main thread"""
    global dashboard
    model_path = "C:\\Users\\Kp101\\OneDrive\\Engineering\\GoKart\\Modeling\\Assets\\kartModel_uitest.fbx"
    
    # Create dashboard
    dashboard = F1Dashboard(
        settings_file_path="ui/dashboard_settings.ini",
        model_path=model_path
    )
    
    # Start telemetry updates in background thread
    telemetry_thread = threading.Thread(target=telemetry_update_loop, daemon=True)
    telemetry_thread.start()
    
    # Run dashboard (blocks until closed)
    exit_code = dashboard.run()
    while exit_code != 0:
        print("Application exited with code:", exit_code, "restarting...")
        exit_code = dashboard.run()
    print("Application finished with exit code:", exit_code)
    sys.exit(exit_code)

if __name__ == "__main__":
    print("Starting F1 Dashboard with simulated telemetry...")
    start_dashboard()