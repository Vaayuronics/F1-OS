import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor
)
from PySide6.QtCore import (
    Qt, QRect, QPoint
)

class GaugeWidget(QWidget):
    """Widget that displays an analog-style gauge with a title, current value, and tick marks."""
    
    def __init__(self, title, max_value, parent=None):
        """Initialize the gauge widget."""
        super().__init__(parent)
        self.title = title
        self.max_value = max_value
        self.current_value = 0
        self.setMinimumSize(150, 150)
    
    def setValue(self, value):
        """Set the current value of the gauge."""
        self.current_value = max(0, min(self.max_value, value))
        self.update()
    
    def getValue(self):
        """Get the current value of the gauge."""
        return self.current_value
    
    def setTitle(self, title):
        """Change the title of the gauge."""
        self.title = title
        self.update()
    
    def setMaxValue(self, max_value):
        """Change the maximum value of the gauge."""
        self.max_value = max_value
        self.current_value = min(self.current_value, self.max_value)
        self.update()
    
    def paintEvent(self, event):
        """Render the gauge on screen."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(0, 0, self.width(), self.height())
        
        # Calculate gauge dimensions
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - 10
        
        # Draw outer ring
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(radius), int(radius))
        
        # Draw gauge title
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(QRect(0, int(center_y + radius/2), self.width(), 30), 
                        Qt.AlignCenter, self.title)
        
        # Draw value
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRect(0, int(center_y - 15), self.width(), 30), 
                        Qt.AlignCenter, f"{int(self.current_value)}")
        
        # Draw gauge arc
        start_angle = 225 * 16  # 225 degrees in QPainter's 1/16th degree system
        span_angle = -270 * 16  # -270 degrees in QPainter's system (clockwise)
        
        progress = self.current_value / self.max_value if self.max_value > 0 else 0
        current_span = span_angle * progress
        
        # Background arc
        painter.setPen(QPen(QColor(60, 60, 60), 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawArc(int(center_x - radius + 15), int(center_y - radius + 15), 
                      int(radius * 2 - 30), int(radius * 2 - 30), start_angle, span_angle)
        
        # Foreground arc with color based on value
        if progress < 0.7:
            gradient_color = QColor(0, 255, 0)  # Green
        elif progress < 0.9:
            gradient_color = QColor(255, 165, 0)  # Orange
        else:
            gradient_color = QColor(255, 0, 0)  # Red
            
        painter.setPen(QPen(gradient_color, 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawArc(int(center_x - radius + 15), int(center_y - radius + 15), 
                      int(radius * 2 - 30), int(radius * 2 - 30), start_angle, int(current_span))
        
        # Draw tick marks
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for i in range(11):
            angle = math.radians(225 - i * 27)  # 270 degrees / 10 = 27 degrees per tick
            inner_x = center_x + (radius - 20) * math.cos(angle)
            inner_y = center_y - (radius - 20) * math.sin(angle)
            outer_x = center_x + (radius - 10) * math.cos(angle)
            outer_y = center_y - (radius - 10) * math.sin(angle)
            
            painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))
            
            # Draw tick labels every other tick
            if i % 2 == 0:
                text_x = center_x + (radius - 35) * math.cos(angle)
                text_y = center_y - (radius - 35) * math.sin(angle)
                
                tick_value = int(i * self.max_value / 10)
                if self.max_value >= 1000:
                    tick_label = f"{tick_value/1000:.1f}k" if tick_value >= 1000 else f"{tick_value}"
                else:
                    tick_label = f"{tick_value}"
                
                rect = QRect(int(text_x) - 20, int(text_y) - 10, 40, 20)
                painter.drawText(rect, Qt.AlignCenter, tick_label)