import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor
)
from PySide6.QtCore import (
    Qt, QRect, QPoint, QRectF
)

class GaugeWidget(QWidget):
    """Widget that displays an analog-style gauge with a title, current value, and tick marks."""
    
    def __init__(self, title="", max_value=100, throttle_label = "TH", parent=None):
        """Initialize the gauge widget."""
        super().__init__(parent)
        self.throttle_label = throttle_label
        self.title = title
        self.max_value = max_value
        self.current_value = 0
        self.throttle = 0  # Add throttle property with default value 0
        self.custom_center_value = None  # Custom value to display in center (e.g., gear)
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
    
    def setThrottle(self, throttle):
        """Set the throttle value (0-1 range)"""
        self.throttle = min(max(0, throttle), 1.0)
        self.update()
    
    def getThrottle(self):
        """Get the current throttle value"""
        return self.throttle
    
    def setCenterValue(self, value):
        """Set a custom value to display in the center (e.g., gear number)"""
        self.custom_center_value = value
        self.update()
    
    def getCenterValue(self):
        """Get the custom center value"""
        return self.custom_center_value
    
    def clearCenterValue(self):
        """Clear the custom center value to show the normal gauge value"""
        self.custom_center_value = None
        self.update()
    
    def paintEvent(self, event):
        """Render the gauge on screen."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate the gauge dimensions
        rect = self.rect()
        center = rect.center()
        
        # Draw the gauge background
        self._drawGaugeBackground(painter)
        
        # Draw the throttle arc before the main value arc (so it appears underneath)
        self._drawThrottleArc(painter)
        
        # Draw the value arc (RPM)
        self._drawValueArc(painter)
        
        # Draw the gauge details (ticks, numbers, needle)
        self._drawGaugeDetails(painter)
    
    def _drawThrottleArc(self, painter):
        """Draw a throttle arc beneath the RPM arc as a curved bar with gradient colors"""
        painter.save()
        
        # Calculate dimensions
        rect = self.rect()
        center = rect.center()
        size = min(rect.width(), rect.height()) * 0.9  # 90% of gauge size
        
        # Define the inner arc for throttle (smaller than the RPM arc)
        inner_radius = size * 0.32  # Make throttle arc closer to center than RPM arc
        arc_thickness = size * 0.04  # Thickness of the arc line
        
        # Set angles to match RPM gauge
        start_angle = 225   # Start at left side (225 degrees)
        span_angle = -270   # -270 degrees total arc (clockwise direction)

        # The throttle value determines how much of the arc to draw
        throttle_span = span_angle * self.throttle
        
        # Create a pen for drawing the arc lines
        background_pen = QPen(QColor(40, 40, 40), arc_thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(background_pen)
        
        # Draw the background arc
        painter.drawArc(
            center.x() - inner_radius, 
            center.y() - inner_radius,
            inner_radius * 2, 
            inner_radius * 2,
            start_angle * 16,  # QPainter uses 16th of a degree
            span_angle * 16
        )
        
        # Draw the colored throttle arc if throttle is greater than 0
        if self.throttle > 0:
            # Calculate how many degrees to fill based on throttle
            filled_angle = 270 * self.throttle  # How many degrees to fill
            
            # Draw each segment with appropriate color
            for i in range(int(filled_angle)):
                # Calculate position in gradient (0.0 to 1.0)
                position = i / 270.0  # Position in the full range
                
                # Fixed: Calculate angle for this segment - starting at exactly the same point
                # as the background arc, and moving clockwise
                segment_angle = start_angle * 16  # Start at the same point as background
                segment_offset = i * 16           # Offset by i degrees (in 1/16ths)
                
                # Create gradient color (green -> orange -> red)
                if position < 0.5:
                    # Green to orange (0.0 to 0.5)
                    ratio = position * 2  # 0.0 to 1.0
                    r = int(0 + (255 * ratio))      # 0 to 255
                    g = int(255)                    # Stay at 255
                    b = int(0)                      # Stay at 0
                else:
                    # Orange to red (0.5 to 1.0)
                    ratio = (position - 0.5) * 2    # 0.0 to 1.0
                    r = int(255)                    # Stay at 255
                    g = int(255 - (255 * ratio))    # 255 to 0
                    b = int(0)                      # Stay at 0
                
                color = QColor(r, g, b)
                gradient_pen = QPen(color, arc_thickness, Qt.SolidLine, Qt.RoundCap)
                painter.setPen(gradient_pen)
                
                # Draw a 1-degree segment with this color
                painter.drawArc(
                    center.x() - inner_radius, 
                    center.y() - inner_radius,
                    inner_radius * 2, 
                    inner_radius * 2,
                    segment_angle - segment_offset,  # Move clockwise from start angle
                    -1 * 16  # Draw 1 degree clockwise
                )
        
        # Add small "TH" label at a position that won't overlap with RPM
        painter.setPen(Qt.white)
        font = painter.font()
        
        # Calculate font size dynamically based on gauge dimensions
        # Use a scaling factor of 3% of the gauge size for the font
        dynamic_font_size = max(12, int(size * 0.05))
        font.setPointSize(dynamic_font_size)
        painter.setFont(font)
        
        # Position below the main display, closer to the bottom of the gauge
        throttle_text = f"{self.throttle_label}: {int(self.throttle * 100)}%"
        
        # Also adjust the text rectangle size based on the gauge size
        text_rect = QRectF(
            center.x() - inner_radius,
            center.y() + size * 0.05,  # Position lower in the gauge
            inner_radius * 2,
            inner_radius * 0.4
        )
        painter.drawText(text_rect, Qt.AlignCenter, throttle_text)
        
        painter.restore()
    
    def _drawGaugeBackground(self, painter):
        """Draw the background of the gauge."""
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(0, 0, self.width(), self.height())
    
    def _drawValueArc(self, painter):
        """Draw the value arc (RPM) on the gauge."""
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - 10
        
        # Draw outer ring
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(radius), int(radius))
        
        # Draw gauge title (reduced by half)
        painter.setPen(QColor(200, 200, 200))
        title_font = painter.font()
        title_font.setPointSize(8)  # Reduced from 16 to 8 (half)
        painter.setFont(title_font)
        painter.drawText(QRect(0, int(center_y + radius/2), self.width(), 30), 
                        Qt.AlignCenter, self.title)
        
        # Draw value (main number) - MUCH BIGGER
        painter.setPen(QColor(255, 255, 255))
        value_font = painter.font()
        value_font.setPointSize(48)  # Even larger for main value
        value_font.setBold(True)     # Make it bold for better visibility
        painter.setFont(value_font)
        
        # Show custom center value if set, otherwise show the gauge value
        if self.custom_center_value is not None:
            center_text = str(self.custom_center_value)
        else:
            center_text = f"{int(self.current_value)}"
            
        # Move center number up to avoid overlap with TH/ENG TUN labels
        painter.drawText(QRect(0, int(center_y - 50), self.width(), 70), 
                        Qt.AlignCenter, center_text)
        
        # Reset font for tick marks (reduced by half)
        tick_font = painter.font()
        tick_font.setPointSize(12)  # Reduced from 24 to 12 (half)
        tick_font.setBold(True)     # Keep bold for visibility
        painter.setFont(tick_font)
        
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
    
    def _drawGaugeDetails(self, painter):
        """Draw the details of the gauge (ticks, numbers, needle)."""
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - 10
        
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
                # Adjust text position for smaller font - move closer to tick marks
                text_x = center_x + (radius - 35) * math.cos(angle)  # Reduced from 50 to 35
                text_y = center_y - (radius - 35) * math.sin(angle)
                
                tick_value = int(i * self.max_value / 10)
                
                # Special handling for RPM gauge (14000 max) to show clean numbers
                if self.max_value == 14000:
                    # For 14k RPM: show 0, 2, 4, 6, 8, 10, 12, 14 (representing thousands)
                    tick_label = f"{tick_value // 1000}"
                elif self.max_value >= 1000:
                    # For other large values, use the original logic but with cleaner formatting
                    if tick_value >= 1000 and tick_value % 1000 == 0:
                        tick_label = f"{tick_value // 1000}k"
                    else:
                        tick_label = f"{tick_value}"
                else:
                    tick_label = f"{tick_value}"
                
                # Smaller rectangle for smaller font
                rect = QRect(int(text_x) - 30, int(text_y) - 15, 60, 30)  # Reduced from 100x50 to 60x30
                painter.drawText(rect, Qt.AlignCenter, tick_label)