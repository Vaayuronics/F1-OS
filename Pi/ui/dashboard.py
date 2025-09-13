from PySide6.QtWidgets import (QMainWindow, QFrame, QSplitter, 
                              QSizePolicy, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QSettings, QSize
from ui.gauge import GaugeWidget
from ui.car3d import Car3DWidget
import os
import sys

class F1Dashboard(QMainWindow):
    """Main dashboard window that displays gauges and car visualization."""
    
    def __init__(self, settings_file_path: str = None, model_path: str = None, title="F1 Dash"):
        """Initialize the dashboard with all widgets and layouts.""" 
        # Create QApplication if it doesn't exist
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
            self.app.setStyle('Fusion')  # Use Fusion style for a more modern look
            self.app.setApplicationName("F1-OS")
            self.app.setOrganizationName("F1-OS")
        else:
            self.app = QApplication.instance()
            
        super().__init__()
        
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #121212;")
        
        # Set up settings from file path
        if settings_file_path:
            self.settings = QSettings(settings_file_path, QSettings.IniFormat)
        else:
            self.settings = QSettings("ui/dashboard_settings.ini", QSettings.IniFormat)
        
        self.telemetry_resize_callbacks = []
        
        # Verify model exists and handle accordingly
        self.model_path = None
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
                self.model_path = None
            else:
                self.model_path = model_path
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top section for title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # Create middle section with splitters for resizing
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)  # Prevent collapsing widgets completely
        
        # RPM gauge
        self.rpm_gauge = GaugeWidget("RPM × 1000", 14, "TH")
        self.rpm_gauge.setMinimumWidth(150)
        self.rpm_gauge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # MPH gauge
        self.mph_gauge = GaugeWidget("MPH", 60, "ENG_TN")
        self.mph_gauge.setMinimumWidth(150)
        self.mph_gauge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # 3D Car visualization
        self.car_widget = Car3DWidget(self.model_path)
        self.car_widget.setMinimumWidth(300)
        self.car_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Add widgets to splitter
        self.main_splitter.addWidget(self.rpm_gauge)
        self.main_splitter.addWidget(self.car_widget)
        self.main_splitter.addWidget(self.mph_gauge)
        
        # Load saved splitter sizes if available
        self.load_splitter_settings()
        
        # Create a container for the upper part of the UI (title + gauges)
        upper_container = QWidget()
        upper_layout = QVBoxLayout(upper_container)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addWidget(title_label)
        upper_layout.addWidget(self.main_splitter, 5)  # Give more vertical space
        
        # Create the telemetry frame
        self.telemetry_frame = QFrame()
        self.telemetry_frame.setStyleSheet("background-color: #1E1E1E; border-radius: 10px;")
        self.telemetry_frame.setMinimumHeight(100)
        
        telemetry_layout = QVBoxLayout(self.telemetry_frame)
        telemetry_label = QLabel("TELEMETRY DATA")
        telemetry_label.setStyleSheet("color: #555; font-size: 14px;")
        telemetry_label.setAlignment(Qt.AlignCenter)
        telemetry_layout.addWidget(telemetry_label)
        
        # Create a new vertical splitter to separate main content from telemetry
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.vertical_splitter.setHandleWidth(8)
        self.vertical_splitter.setChildrenCollapsible(False)
        self.vertical_splitter.addWidget(upper_container)       # Upper content first
        self.vertical_splitter.addWidget(self.telemetry_frame)  # Telemetry frame at bottom
        
        # Set initial sizes for the vertical splitter (70% upper, 30% telemetry)
        self.vertical_splitter.setSizes([700, 300])
        
        # Add the vertical splitter to the main layout
        main_layout.addWidget(self.vertical_splitter)
        
        # Style the splitter handle to make it more visible
        self.setStyleSheet("""
            QSplitter::handle {
                background-color: #555555;
                border: 1px solid #777777;
            }
            QSplitter::handle:hover {
                background-color: #666666;
            }
            QSplitter::handle:pressed {
                background-color: #777777;
            }
        """)
        
        # Connect splitter's splitterMoved signal
        self.vertical_splitter.splitterMoved.connect(self._on_telemetry_resize)
        
        # Initialize window geometry and settings
        self._setup_window_geometry()
        self._connect_geometry_events()
    
    def run(self):
        """Show the dashboard and run the application."""
        self.show()
        return self.app.exec()
    
    def _setup_window_geometry(self):
        """Set up window size and position from settings."""
        # Set size from settings if available, otherwise use default
        if self.settings.contains("window/size"):
            size_str = self.settings.value("window/size")
            try:
                width, height = map(int, size_str.split(","))
                self.resize(width, height)
            except:
                self.setMinimumSize(QSize(1000, 700))
        else:
            self.setMinimumSize(QSize(1000, 700))
        
        # Set position from settings if available
        if self.settings.contains("window/position"):
            pos_str = self.settings.value("window/position")
            try:
                x, y = map(int, pos_str.split(","))
                self.move(x, y)
            except:
                # Use default position
                pass
        
        # Load telemetry box size if available
        if self.settings.contains("telemetry/size"):
            telemetry_size_str = self.settings.value("telemetry/size")
            try:
                width, height = map(int, telemetry_size_str.split(","))
                self.set_telemetry_box_size(width, height)
            except:
                # Use default telemetry box size
                pass
        
        # Important: Force load splitter settings here to make sure they're applied
        # after all other layout operations
        self.load_splitter_settings()
        
        # Load camera settings if available
        self.load_camera_settings()
    
    def _connect_geometry_events(self):
        """Connect window resize and move events to save settings."""
        def on_window_geometry_changed():
            size = self.size()
            pos = self.pos()
            self.settings.setValue("window/size", f"{size.width()},{size.height()}")
            self.settings.setValue("window/position", f"{pos.x()},{pos.y()}")
            
            # Also save telemetry box size
            telemetry_size = self.get_telemetry_box_size()
            if telemetry_size:
                self.settings.setValue("telemetry/size", f"{telemetry_size[0]},{telemetry_size[1]}")
            
            # Save camera settings when window changes (user might have moved camera)
            self.save_camera_settings()
        
        self.resizeEvent = lambda event: (super(F1Dashboard, self).resizeEvent(event), on_window_geometry_changed())
        self.moveEvent = lambda event: (super(F1Dashboard, self).moveEvent(event), on_window_geometry_changed())
        
        # Connect telemetry box resize event
        self.connect_telemetry_resize_event(on_window_geometry_changed)
    
    def setRPM(self, rpm):
        """Set the RPM gauge value."""
        self.rpm_gauge.setValue(rpm)
    
    def setSpeed(self, speed):
        """Set the speed gauge value."""
        self.mph_gauge.setValue(speed)
    
    def getRPM(self):
        """Get current RPM value."""
        return self.rpm_gauge.getValue()
    
    def getSpeed(self):
        """Get current speed value."""
        return self.mph_gauge.getValue()
    
    def setThrottle(self, throttle):
        """Set the throttle value (0-1 range)."""
        self.rpm_gauge.setThrottle(throttle)
    
    def getThrottle(self):
        """Get current throttle value."""
        return self.rpm_gauge.getThrottle()
    
    def setTune(self, tune):
        """Set the throttle value (0-1 range)."""
        self.mph_gauge.setThrottle(tune)
    
    def getTune(self):
        """Get current throttle value."""
        return self.mph_gauge.getThrottle()
    
    def resetValues(self):
        """Reset all dashboard values to zero/default."""
        self.rpm_gauge.setValue(0)
        self.rpm_gauge.setThrottle(0)
        self.mph_gauge.setValue(0)
    
    def updateTelemetryDisplay(self, data_dict):
        """Update the telemetry data space with custom information.""" 
        # Remove old widgets
        for i in reversed(range(self.telemetry_frame.layout().count())): 
            widget = self.telemetry_frame.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Create a horizontal layout for each data pair
        if data_dict:
            for label, value in data_dict.items():
                row_layout = QHBoxLayout()
                
                label_widget = QLabel(f"{label}:")
                label_widget.setStyleSheet("color: #AAA; font-size: 14px;")
                
                value_widget = QLabel(f"{value}")
                value_widget.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
                
                row_layout.addWidget(label_widget)
                row_layout.addWidget(value_widget)
                row_layout.addStretch()
                
                self.telemetry_frame.layout().addLayout(row_layout)
        else:
            # Add placeholder if no data
            placeholder = QLabel("TELEMETRY DATA")
            placeholder.setStyleSheet("color: #555; font-size: 14px;")
            placeholder.setAlignment(Qt.AlignCenter)
            self.telemetry_frame.layout().addWidget(placeholder)
    
    def load_splitter_settings(self):
        """Load saved splitter sizes from settings.""" 
        if self.settings.contains("splitter/sizes"):
            # Convert the saved string back to a list of integers
            sizes_str = self.settings.value("splitter/sizes")
            try:
                if isinstance(sizes_str, str):
                    # Handle string representation
                    sizes = [int(x) for x in sizes_str.split(",")]
                else:
                    # Handle list representation
                    sizes = [int(x) for x in sizes_str]
                
                # Apply the sizes only if we have the right number of elements
                if len(sizes) == self.main_splitter.count():
                    self.main_splitter.setSizes(sizes)
                    # Force the layout to update immediately
                    self.main_splitter.refresh()
                    print(f"Loaded splitter sizes: {sizes}")
                    return True  # Successfully loaded
            except (ValueError, TypeError) as e:
                print(f"Error loading splitter sizes: {e}")
        
        return False  # Failed to load
    
    def save_splitter_settings(self):
        """Save current splitter sizes to settings.""" 
        sizes = self.main_splitter.sizes()
        # Store as comma-separated string to avoid type issues
        self.settings.setValue("splitter/sizes", ",".join(str(x) for x in sizes))
        print(f"Saved splitter sizes: {sizes}")
    
    def load_camera_settings(self):
        """Load saved camera settings from configuration."""
        if self.settings.contains("camera/position"):
            try:
                pos_str = self.settings.value("camera/position")
                center_str = self.settings.value("camera/viewCenter", "0,0,0")
                up_str = self.settings.value("camera/upVector", "0,1,0")
                
                pos = [float(x) for x in pos_str.split(",")]
                center = [float(x) for x in center_str.split(",")]
                up = [float(x) for x in up_str.split(",")]
                
                camera_settings = {
                    'position': pos,
                    'viewCenter': center,
                    'upVector': up
                }
                
                self.car_widget.set_camera_settings(camera_settings)
                print(f"Loaded camera settings: {camera_settings}")
                return True
            except Exception as e:
                print(f"Error loading camera settings: {e}")
        return False
    
    def save_camera_settings(self):
        """Save current camera settings to configuration."""
        camera_settings = self.car_widget.get_camera_settings()
        if camera_settings:
            try:
                pos = camera_settings['position']
                center = camera_settings['viewCenter']
                up = camera_settings['upVector']
                
                self.settings.setValue("camera/position", ",".join(str(x) for x in pos))
                self.settings.setValue("camera/viewCenter", ",".join(str(x) for x in center))
                self.settings.setValue("camera/upVector", ",".join(str(x) for x in up))
                print(f"Saved camera settings: {camera_settings}")
            except Exception as e:
                print(f"Error saving camera settings: {e}")
    
    def closeEvent(self, event):
        """Override close event to save settings before closing.""" 
        self.save_splitter_settings()
        self.save_camera_settings()
        super().closeEvent(event)
    
    def set_telemetry_box_size(self, width, height):
        """
        Set the dimensions of the telemetry data box.
        
        Args:
            width (int): The width of the telemetry box
            height (int): The height of the telemetry box
        """
        if hasattr(self, 'vertical_splitter'):
            sizes = self.vertical_splitter.sizes()
            if len(sizes) >= 2:
                total_height = sum(sizes)
                # Set telemetry height (bottom widget)
                self.vertical_splitter.setSizes([total_height - height, height])
    
    def get_telemetry_box_size(self):
        """
        Get the current dimensions of the telemetry data box.
        
        Returns:
            tuple: A tuple containing (width, height) of the telemetry box
        """
        if hasattr(self, 'telemetry_frame') and hasattr(self, 'vertical_splitter'):
            sizes = self.vertical_splitter.sizes()
            if len(sizes) >= 2:
                return (self.telemetry_frame.width(), sizes[1])  # Second widget is telemetry
        return None
    
    def connect_telemetry_resize_event(self, callback):
        """
        Connect a callback function to be called when the telemetry box is resized.
        
        Args:
            callback (function): The function to call when the telemetry box is resized
        """
        if callback not in self.telemetry_resize_callbacks:
            self.telemetry_resize_callbacks.append(callback)
    
    def _on_telemetry_resize(self, pos, index):
        """
        Internal method called when the splitter is moved, triggering telemetry box resize.
        
        Args:
            pos (int): The position of the splitter
            index (int): The index of the splitter handle that was moved
        """
        # Execute all registered callbacks
        for callback in self.telemetry_resize_callbacks:
            callback()
    
    def reset_view(self):
        """Reset the dashboard view to default state and make gauges symmetrical."""
        # Reset any existing view settings
        
        # Make RPM and MPH gauges equal size
        if hasattr(self, 'main_splitter'):
            sizes = self.main_splitter.sizes()
            if len(sizes) == 3:  # RPM, car, MPH layout
                # Calculate total width
                total_width = sum(sizes)
                
                # Calculate gauge width (equal for both)
                gauge_width = int((total_width - sizes[1]) / 2)
                
                # Set sizes: [RPM gauge, car widget, MPH gauge]
                self.main_splitter.setSizes([gauge_width, sizes[1], gauge_width])
                
                # Save the new splitter sizes
                self.save_splitter_settings()
        
        # Reset other view elements as needed