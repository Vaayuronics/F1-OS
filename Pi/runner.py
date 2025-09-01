#!/usr/bin/env python3
"""
F1 Dashboard Application with 3D Visualization
Provides telemetry gauges and 3D car visualization.
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QSize, QSettings
from ui.dashboard import F1Dashboard

def main():
    """Main function to initialize and run the application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a more modern look
    app.setApplicationName("F1-OS")
    app.setOrganizationName("F1-OS")
    
    # Set the path to the model
    model_path = "C:\\Users\\Kp101\\OneDrive\\Engineering\\GoKart\\test.fbx"
    
    # Verify model exists and print info
    model_exists = False
    if model_path:
        model_exists = os.path.exists(model_path)
        print(f"3D Model path: {model_path}")
        print(f"Model exists: {model_exists}")
        
        if not model_exists:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f"Model file not found: {model_path}")
            msg.setWindowTitle("Model Not Found")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setInformativeText("Using default fallback model instead.")
            msg.exec()
            model_path = None
    
    # Load window settings with relative path
    settings = QSettings("ui/dashboard_settings.ini", QSettings.IniFormat)
    
    dashboard = F1Dashboard(settings_file=settings, model_path=model_path)
    
    # Order matters: first set window size, then load splitter settings
    # Set size from settings if available, otherwise use default
    if settings.contains("window/size"):
        size_str = settings.value("window/size")
        try:
            width, height = map(int, size_str.split(","))
            dashboard.resize(width, height)
        except:
            dashboard.setMinimumSize(QSize(1000, 700))
    else:
        dashboard.setMinimumSize(QSize(1000, 700))
    
    # Set position from settings if available
    if settings.contains("window/position"):
        pos_str = settings.value("window/position")
        try:
            x, y = map(int, pos_str.split(","))
            dashboard.move(x, y)
        except:
            # Use default position
            pass
    
    # Load telemetry box size if available
    if settings.contains("telemetry/size"):
        telemetry_size_str = settings.value("telemetry/size")
        try:
            width, height = map(int, telemetry_size_str.split(","))
            dashboard.set_telemetry_box_size(width, height)
        except:
            # Use default telemetry box size
            pass
    
    # Important: Force load splitter settings here to make sure they're applied
    # after all other layout operations
    dashboard.load_splitter_settings()
    
    # Connect window resize and move events to save settings
    def on_window_geometry_changed():
        size = dashboard.size()
        pos = dashboard.pos()
        settings.setValue("window/size", f"{size.width()},{size.height()}")
        settings.setValue("window/position", f"{pos.x()},{pos.y()}")
        
        # Also save telemetry box size
        telemetry_size = dashboard.get_telemetry_box_size()
        if telemetry_size:
            settings.setValue("telemetry/size", f"{telemetry_size[0]},{telemetry_size[1]}")
    
    dashboard.resizeEvent = lambda event: (super(F1Dashboard, dashboard).resizeEvent(event), on_window_geometry_changed())
    dashboard.moveEvent = lambda event: (super(F1Dashboard, dashboard).moveEvent(event), on_window_geometry_changed())
    
    # Connect telemetry box resize event
    dashboard.connect_telemetry_resize_event(on_window_geometry_changed)
    
    # Set test values AFTER all layout operations
    dashboard.setThrottle(0.75)
    dashboard.setTune(0.5)

    dashboard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
