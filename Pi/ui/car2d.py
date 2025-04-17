from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath
)
from PySide6.QtCore import Qt

class CarWidget(QWidget):
    """Widget that displays a top-down view of an F1 car with steerable front wheels."""
    
    def __init__(self, start_angle=0, parent=None):
        """Initialize the car widget."""
        super().__init__(parent)
        self.wheel_angle = start_angle  # 0 degrees is straight
        self.setMinimumSize(300, 400)
    
    def setWheelAngle(self, angle):
        """Set the steering angle of the front wheels."""
        self.wheel_angle = max(-30, min(30, angle))
        self.update()
    
    def getWheelAngle(self):
        """Get the current steering angle of the front wheels."""
        return self.wheel_angle
        
    def paintEvent(self, event):
        """Render the car on screen."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(20, 20, 20)))
        painter.drawRect(0, 0, self.width(), self.height())
        
        # Set pen for car wireframe
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(Qt.NoBrush)
        
        # Calculate dimensions based on widget size
        width = self.width()
        height = self.height()
        car_width = width * 0.6
        car_length = height * 0.7
        
        # Main body of car (simplified F1 shape)
        center_x = width / 2
        bottom_y = height * 0.8
        top_y = bottom_y - car_length
        
        # Draw car body - create a path for the outline
        path = QPainterPath()
        
        # Start at the nose of the car
        path.moveTo(center_x, top_y)
        
        # Draw the left side
        path.lineTo(center_x - car_width * 0.15, top_y + car_length * 0.15)  # Nose to cockpit
        path.lineTo(center_x - car_width * 0.3, top_y + car_length * 0.3)    # Cockpit
        path.lineTo(center_x - car_width / 2, top_y + car_length * 0.5)      # Sidepod
        path.lineTo(center_x - car_width / 2, bottom_y - car_length * 0.1)   # Rear
        
        # Draw the rear
        path.lineTo(center_x + car_width / 2, bottom_y - car_length * 0.1)
        
        # Draw the right side (mirror of left)
        path.lineTo(center_x + car_width / 2, top_y + car_length * 0.5)
        path.lineTo(center_x + car_width * 0.3, top_y + car_length * 0.3)
        path.lineTo(center_x + car_width * 0.15, top_y + car_length * 0.15)
        
        # Close the path
        path.lineTo(center_x, top_y)
        
        # Draw the car body
        painter.drawPath(path)
        
        # Draw cockpit
        cockpit_width = car_width * 0.2
        cockpit_length = car_length * 0.2
        cockpit_x = center_x - cockpit_width / 2
        cockpit_y = top_y + car_length * 0.25
        painter.drawEllipse(int(cockpit_x), int(cockpit_y), 
                           int(cockpit_width), int(cockpit_length))
        
        # Draw front wing
        wing_width = car_width * 0.8
        wing_x = center_x - wing_width / 2
        wing_y = top_y + car_length * 0.1
        wing_height = car_length * 0.05
        painter.drawRect(int(wing_x), int(wing_y), 
                         int(wing_width), int(wing_height))
        
        # Draw rear wing
        rear_wing_width = car_width * 0.7
        rear_wing_x = center_x - rear_wing_width / 2
        rear_wing_y = bottom_y - car_length * 0.15
        rear_wing_height = car_length * 0.05
        painter.drawRect(int(rear_wing_x), int(rear_wing_y), 
                         int(rear_wing_width), int(rear_wing_height))
        
        # Draw wheels
        wheel_width = car_width * 0.15
        wheel_length = car_length * 0.12
        
        # Wheel positions
        fl_wheel_x = center_x - car_width * 0.4
        fl_wheel_y = top_y + car_length * 0.3
        
        fr_wheel_x = center_x + car_width * 0.25
        fr_wheel_y = top_y + car_length * 0.3
        
        rl_wheel_x = center_x - car_width * 0.4
        rl_wheel_y = bottom_y - car_length * 0.25
        
        rr_wheel_x = center_x + car_width * 0.25
        rr_wheel_y = bottom_y - car_length * 0.25
        
        # Draw rear wheels (static)
        painter.drawRect(int(rl_wheel_x), int(rl_wheel_y), 
                         int(wheel_width), int(wheel_length))
        painter.drawRect(int(rr_wheel_x), int(rr_wheel_y), 
                         int(wheel_width), int(wheel_length))
        
        # Draw front wheels with rotation
        painter.save()
        painter.translate(fl_wheel_x + wheel_width / 2, fl_wheel_y + wheel_length / 2)
        painter.rotate(self.wheel_angle)
        painter.drawRect(int(-wheel_width / 2), int(-wheel_length / 2), 
                         int(wheel_width), int(wheel_length))
        painter.restore()
        
        painter.save()
        painter.translate(fr_wheel_x + wheel_width / 2, fr_wheel_y + wheel_length / 2)
        painter.rotate(self.wheel_angle)
        painter.drawRect(int(-wheel_width / 2), int(-wheel_length / 2), 
                         int(wheel_width), int(wheel_length))
        painter.restore()