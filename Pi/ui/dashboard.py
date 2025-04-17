from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Qt
from gauge import GaugeWidget
from car3d import Car3DWidget

class F1Dashboard(QMainWindow):
    """Main dashboard window that displays gauges, car visualization, and controls."""
    
    def __init__(self, title="F1 Dash", stl_path=None):
        """Initialize the dashboard with all widgets and layouts."""
        super().__init__()
        
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #121212;")
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top section for title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Create middle section with gauges and car
        middle_layout = QHBoxLayout()
        
        # RPM gauge
        self.rpm_gauge = GaugeWidget("RPM × 1000", 14)
        self.rpm_gauge.setMinimumWidth(200)
        middle_layout.addWidget(self.rpm_gauge)
        
        # 3D Car visualization
        self.car_widget = Car3DWidget(stl_path)
        self.car_widget.setMinimumWidth(400)
        middle_layout.addWidget(self.car_widget)
        
        # MPH gauge
        self.mph_gauge = GaugeWidget("MPH", 60)
        self.mph_gauge.setMinimumWidth(200)
        middle_layout.addWidget(self.mph_gauge)
        
        main_layout.addLayout(middle_layout)
        
        # Create bottom section for controls
        bottom_layout = QHBoxLayout()
        
        # Add animation controls
        self.animation_active = False
        self.animation_button = QPushButton("Start Animation")
        self.animation_button.clicked.connect(self.toggle_animation)
        bottom_layout.addWidget(self.animation_button)
        
        main_layout.addLayout(bottom_layout)
        
        # Add telemetry data space
        self.future_frame = QFrame()
        self.future_frame.setStyleSheet("background-color: #1E1E1E; border-radius: 10px;")
        self.future_frame.setMinimumHeight(100)
        
        future_layout = QVBoxLayout(self.future_frame)
        future_label = QLabel("ADDITIONAL TELEMETRY DATA SPACE")
        future_label.setStyleSheet("color: #555; font-size: 14px;")
        future_label.setAlignment(Qt.AlignCenter)
        future_layout.addWidget(future_label)
        
        main_layout.addWidget(self.future_frame)
    
    def toggle_animation(self):
        """Toggle the car animation on/off."""
        if self.animation_active:
            self.car_widget.stop_animation()
            self.animation_button.setText("Start Animation")
        else:
            self.car_widget.start_animation()
            self.animation_button.setText("Stop Animation")
        
        self.animation_active = not self.animation_active
    
    def updateWheelAngle(self, angle):
        """Update the wheel angle based on slider input."""
        self.car_widget.setWheelAngle(angle)
    
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
    
    def getWheelAngle(self):
        """Get current steering wheel angle."""
        return self.car_widget.getWheelAngle()
    
    def resetValues(self):
        """Reset all dashboard values to zero/default."""
        self.rpm_gauge.setValue(0)
        self.mph_gauge.setValue(0)
        self.car_widget.setWheelAngle(0)
        if hasattr(self, 'wheel_slider'):
            self.wheel_slider.setValue(0)
    
    def updateTelemetryDisplay(self, data_dict):
        """Update the telemetry data space with custom information."""
        # Remove old widgets
        for i in reversed(range(self.future_frame.layout().count())): 
            widget = self.future_frame.layout().itemAt(i).widget()
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
                
                self.future_frame.layout().addLayout(row_layout)
        else:
            # Add placeholder if no data
            placeholder = QLabel("ADDITIONAL TELEMETRY DATA SPACE")
            placeholder.setStyleSheet("color: #555; font-size: 14px;")
            placeholder.setAlignment(Qt.AlignCenter)
            self.future_frame.layout().addWidget(placeholder)