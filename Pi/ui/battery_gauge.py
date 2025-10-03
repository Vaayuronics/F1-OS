import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath
)
from PySide6.QtCore import (
    Qt, QRect, QRectF
)

class BatteryGaugeWidget(QWidget):
    """Widget that displays a vertical battery gauge with percentage."""
    
    def __init__(self, parent=None):
        """Initialize the battery gauge widget."""
        super().__init__(parent)
        self.battery_level = 100  # Battery level 0-100
        self.setMinimumSize(60, 120)  # Reduced from 80x200 to 60x120
        self.setMaximumWidth(100)     # Reduced from 120 to 100
    
    def setBatteryLevel(self, level):
        """Set the battery level (0-100)."""
        self.battery_level = max(0, min(100, level))
        self.update()
    
    def getBatteryLevel(self):
        """Get the current battery level."""
        return self.battery_level
    
    def mousePressEvent(self, event):
        """Handle mouse clicks on the battery gauge to close the application."""
        if event.button() == Qt.LeftButton:
            # Find the top-level window and close it
            window = self.window()
            if window:
                window.close()
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Render the battery gauge on screen."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions
        rect = self.rect()
        center_x = rect.width() / 2
        
        # Draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(rect)
        
        # Draw battery icon
        self._drawBatteryIcon(painter)
        self._drawBatteryPercentage(painter)
    
    def _drawBatteryIcon(self, painter):
        """Draw an enlarged battery icon that fills the available space."""
        painter.save()
        
        rect = self.rect()
        # Make the battery much larger to fill the space previously used by both icon and bar
        icon_width = rect.width() * 0.6  # Use 60% of widget width
        icon_height = rect.height() * 0.5  # Use 50% of widget height
        
        # Center the battery icon
        icon_x = (rect.width() - icon_width) / 2
        icon_y = rect.height() * 0.15  # Position it in upper portion, leaving space for percentage
        
        # Draw battery outline
        painter.setPen(QPen(QColor(200, 200, 200), 3))  # Thicker outline for larger battery
        painter.setBrush(Qt.NoBrush)
        
        # Main battery body
        battery_rect = QRectF(icon_x, icon_y, icon_width, icon_height)
        painter.drawRoundedRect(battery_rect, 6, 6)  # Larger corner radius
        
        # Battery terminal (top nub) - make it proportional
        terminal_width = icon_width * 0.3
        terminal_height = icon_height * 0.12
        terminal_x = icon_x + (icon_width - terminal_width) / 2
        terminal_y = icon_y - terminal_height
        terminal_rect = QRectF(terminal_x, terminal_y, terminal_width, terminal_height)
        painter.drawRoundedRect(terminal_rect, 2, 2)
        
        # Fill battery based on level
        if self.battery_level > 0:
            fill_height = battery_rect.height() * (self.battery_level / 100)
            fill_y = battery_rect.bottom() - fill_height
            
            # Color based on battery level
            if self.battery_level > 60:
                fill_color = QColor(0, 255, 0)  # Green
            elif self.battery_level > 30:
                fill_color = QColor(255, 165, 0)  # Orange
            else:
                fill_color = QColor(255, 0, 0)  # Red
            
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.NoPen)
            
            # Add some padding inside the battery outline
            padding = 4
            fill_rect = QRectF(
                battery_rect.left() + padding, 
                fill_y + padding,
                battery_rect.width() - (padding * 2), 
                fill_height - padding
            )
            painter.drawRoundedRect(fill_rect, 4, 4)
        
        painter.restore()
    
    def _drawBatteryPercentage(self, painter):
        """Draw the percentage text below the battery icon."""
        painter.save()
        
        rect = self.rect()
        
        # Set font (same size as gauge tick marks - 24pt)
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        
        # Draw percentage text below the enlarged battery icon
        percentage_text = f"{int(self.battery_level)}%"
        text_rect = QRect(0, int(rect.height() * 0.7), rect.width(), int(rect.height() * 0.3))
        painter.drawText(text_rect, Qt.AlignCenter, percentage_text)
        
        painter.restore()