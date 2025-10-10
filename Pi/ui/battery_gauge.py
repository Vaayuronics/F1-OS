from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPixmap
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
        
        # Cache previous value to avoid unnecessary repaints
        self._prev_battery_level = -1
        self._static_cache = None
        self._cached_size = None
        self._battery_rect = None
        self._terminal_rect = None
        self._padding = 4
    
    def setBatteryLevel(self, level):
        """Set the battery level (0-100)."""
        new_level = max(0, min(100, level))
        # Only update if battery level changed by at least 1%
        if abs(new_level - self._prev_battery_level) >= 1.0:
            self.battery_level = new_level
            self._prev_battery_level = new_level
            self.update()
    
    def getBatteryLevel(self):
        """Get the current battery level."""
        return self.battery_level

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._static_cache = None
        self._cached_size = None
    
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
        # Reduce antialiasing for performance (battery is mostly rectangles)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, False)  # Disabled for performance
        painter.setClipRect(event.rect())  # Only paint dirty region
        
        current_size = self.size()
        if self._static_cache is None or self._cached_size != current_size:
            self._rebuild_static_cache()
            self._cached_size = current_size

        if self._static_cache:
            painter.drawPixmap(0, 0, self._static_cache)

        self._drawBatteryFill(painter)
        self._drawBatteryPercentage(painter)
    
    def _rebuild_static_cache(self):
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            self._static_cache = None
            return

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(30, 30, 30))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        icon_width = rect.width() * 0.6
        icon_height = rect.height() * 0.5
        icon_x = (rect.width() - icon_width) / 2
        icon_y = rect.height() * 0.15

        self._battery_rect = QRectF(icon_x, icon_y, icon_width, icon_height)

        terminal_width = icon_width * 0.3
        terminal_height = icon_height * 0.12
        terminal_x = icon_x + (icon_width - terminal_width) / 2
        terminal_y = icon_y - terminal_height
        self._terminal_rect = QRectF(terminal_x, terminal_y, terminal_width, terminal_height)

        painter.setPen(QPen(QColor(200, 200, 200), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self._battery_rect, 6, 6)
        painter.drawRoundedRect(self._terminal_rect, 2, 2)

        painter.end()
        self._static_cache = pixmap

    def _drawBatteryFill(self, painter):
        if not self._battery_rect:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        if self.battery_level <= 0:
            painter.restore()
            return

        battery_rect = self._battery_rect
        fill_height = battery_rect.height() * (self.battery_level / 100)
        fill_y = battery_rect.bottom() - fill_height

        if self.battery_level > 60:
            fill_color = QColor(0, 255, 0)
        elif self.battery_level > 30:
            fill_color = QColor(255, 165, 0)
        else:
            fill_color = QColor(255, 0, 0)

        painter.setBrush(QBrush(fill_color))
        painter.setPen(Qt.NoPen)

        fill_rect = QRectF(
            battery_rect.left() + self._padding,
            fill_y + self._padding,
            battery_rect.width() - (self._padding * 2),
            fill_height - self._padding
        )

        if fill_rect.height() > 0:
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