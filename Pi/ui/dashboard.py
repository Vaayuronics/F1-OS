from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QFrame, QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, QSettings, QSize
from ui.gauge import GaugeWidget
from ui.car3d import Car3DWidget
import os

class F1Dashboard(QMainWindow):
    """Main dashboard window that displays gauges and car visualization."""
    
    def __init__(self, settings_file : QSettings, title="F1 Dash", model_path=None):
        """Initialize the dashboard with all widgets and layouts."""
        super().__init__()
        
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #121212;")
        
        # Set up settings with relative path
        self.settings = settings_file
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top section for title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Create middle section with splitters for resizing
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)  # Prevent collapsing widgets completely
        
        # RPM gauge
        self.rpm_gauge = GaugeWidget("RPM × 1000", 14)
        self.rpm_gauge.setMinimumWidth(150)
        self.rpm_gauge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # MPH gauge
        self.mph_gauge = GaugeWidget("MPH", 60)
        self.mph_gauge.setMinimumWidth(150)
        self.mph_gauge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # 3D Car visualization
        self.car_widget = Car3DWidget(model_path)
        self.car_widget.setMinimumWidth(300)
        self.car_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Add widgets to splitter
        self.main_splitter.addWidget(self.rpm_gauge)
        self.main_splitter.addWidget(self.car_widget)
        self.main_splitter.addWidget(self.mph_gauge)
        
        # Load saved splitter sizes if available
        self.load_splitter_settings()
        
        main_layout.addWidget(self.main_splitter, 5)  # Give the middle section more vertical space
        
        # Add telemetry data space
        self.telemetry_frame = QFrame()
        self.telemetry_frame.setStyleSheet("background-color: #1E1E1E; border-radius: 10px;")
        self.telemetry_frame.setMinimumHeight(100)
        
        telemetry_layout = QVBoxLayout(self.telemetry_frame)
        telemetry_label = QLabel("TELEMETRY DATA")
        telemetry_label.setStyleSheet("color: #555; font-size: 14px;")
        telemetry_label.setAlignment(Qt.AlignCenter)
        telemetry_layout.addWidget(telemetry_label)
        
        main_layout.addWidget(self.telemetry_frame)
    
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
    
    def resetValues(self):
        """Reset all dashboard values to zero/default."""
        self.rpm_gauge.setValue(0)
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
                    print(f"Loaded splitter sizes: {sizes}")
            except (ValueError, TypeError) as e:
                print(f"Error loading splitter sizes: {e}")
    
    def save_splitter_settings(self):
        """Save current splitter sizes to settings."""
        sizes = self.main_splitter.sizes()
        # Store as comma-separated string to avoid type issues
        self.settings.setValue("splitter/sizes", ",".join(str(x) for x in sizes))
        print(f"Saved splitter sizes: {sizes}")
    
    def closeEvent(self, event):
        """Override close event to save settings before closing."""
        self.save_splitter_settings()
        super().closeEvent(event)