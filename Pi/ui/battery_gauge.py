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
        self.setMinimumSize(80, 200)
        self.setMaximumWidth(120)
    
    def setBatteryLevel(self, level):
        """Set the battery level (0-100)."""
        self.battery_level = max(0, min(100, level))
        self.update()
    
    def getBatteryLevel(self):
        """Get the current battery level."""
        return self.battery_level
    
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
        
        # Draw battery icon and bar
        self._drawBatteryIcon(painter)
        self._drawBatteryBar(painter)
        self._drawBatteryPercentage(painter)
    
    def _drawBatteryIcon(self, painter):
        """Draw a simple battery icon on the left side."""
        painter.save()
        
        rect = self.rect()
        icon_size = 30
        icon_x = 15
        icon_y = rect.height() / 2 - icon_size / 2
        
        # Draw battery outline
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(Qt.NoBrush)
        
        # Main battery body
        battery_rect = QRectF(icon_x, icon_y, icon_size * 0.7, icon_size)
        painter.drawRoundedRect(battery_rect, 3, 3)
        
        # Battery terminal (top nub)
        terminal_width = icon_size * 0.3
        terminal_height = icon_size * 0.15
        terminal_x = icon_x + (icon_size * 0.7 - terminal_width) / 2
        terminal_y = icon_y - terminal_height
        terminal_rect = QRectF(terminal_x, terminal_y, terminal_width, terminal_height)
        painter.drawRect(terminal_rect)
        
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
            
            fill_rect = QRectF(
                battery_rect.left() + 2, 
                fill_y + 2,
                battery_rect.width() - 4, 
                fill_height - 2
            )
            painter.drawRoundedRect(fill_rect, 2, 2)
        
        painter.restore()
    
    def _drawBatteryBar(self, painter):
        """Draw the vertical colored bar next to the battery icon."""
        painter.save()
        
        rect = self.rect()
        bar_width = 20
        bar_height = rect.height() * 0.6
        bar_x = rect.width() - bar_width - 10
        bar_y = (rect.height() - bar_height) / 2
        
        # Draw background bar
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        bar_rect = QRectF(bar_x, bar_y, bar_width, bar_height)
        painter.drawRoundedRect(bar_rect, 5, 5)
        
        # Draw filled portion
        if self.battery_level > 0:
            fill_height = bar_height * (self.battery_level / 100)
            fill_y = bar_y + bar_height - fill_height
            
            # Create gradient color based on level
            if self.battery_level > 60:
                fill_color = QColor(0, 255, 0)  # Green
            elif self.battery_level > 30:
                fill_color = QColor(255, 165, 0)  # Orange
            else:
                fill_color = QColor(255, 0, 0)  # Red
            
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.NoPen)
            
            fill_rect = QRectF(
                bar_x + 2, 
                fill_y + 2,
                bar_width - 4, 
                fill_height - 4
            )
            painter.drawRoundedRect(fill_rect, 3, 3)
        
        painter.restore()
    
    def _drawBatteryPercentage(self, painter):
        """Draw the percentage text below the bar."""
        painter.save()
        
        rect = self.rect()
        
        # Set font (same size as gauge tick marks - 24pt)
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        
        # Draw percentage text
        percentage_text = f"{int(self.battery_level)}%"
        text_rect = QRect(0, int(rect.height() * 0.8), rect.width(), int(rect.height() * 0.2))
        painter.drawText(text_rect, Qt.AlignCenter, percentage_text)
        
        painter.restore()