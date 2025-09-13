#!/usr/bin/env python3
"""
F1 Dashboard Application with 3D Visualization
Provides telemetry gauges and 3D car visualization.
"""
import sys
from ui.dashboard import F1Dashboard

def main():
    """Main function to initialize and run the application."""
    # Set the path to the model
    model_path = "C:\\Users\\Kp101\\OneDrive\\Engineering\\GoKart\\Modeling\\Assets\\kartModel_uitest.fbx"
    
    # Create and run dashboard
    dashboard = F1Dashboard(
        settings_file_path="ui/dashboard_settings.ini",
        model_path=model_path
    )
    
    exit_code = dashboard.run()
    while exit_code != 0:
        print("Application exited with code:", exit_code, "restarting...")
        exit_code = dashboard.run()
    print("Application finished with exit code:", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
