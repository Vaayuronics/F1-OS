import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath
)
from PySide6.QtCore import (
    Qt, QRect, QRectF
)

class VolumeGaugeWidget(QWidget):
    """Widget that displays a vertical volume gauge with percentage."""
    
    def __init__(self, title="VOL", icon_type="speaker", parent=None):
        """Initialize the volume gauge widget."""
        super().__init__(parent)
        self.volume_level = 50  # Volume level 0-100
        self.title = title
        self.icon_type = icon_type  # "speaker" or "engine"
        self.setMinimumSize(60, 120)  # Same size as battery gauge
        self.setMaximumWidth(100)
        
        # Cache previous value to avoid unnecessary repaints
        self._prev_volume_level = -1
    
    def setVolumeLevel(self, level):
        """Set the volume level (0-100)."""
        new_level = max(0, min(100, level))
        # Only update if volume changed by at least 1%
        if abs(new_level - self._prev_volume_level) >= 1.0:
            self.volume_level = new_level
            self._prev_volume_level = new_level
            self.update()
    
    def getVolumeLevel(self):
        """Get the current volume level."""
        return self.volume_level
    
    def paintEvent(self, event):
        """Render the volume gauge on screen."""
        painter = QPainter(self)
        # Reduce antialiasing for performance (volume gauge is mostly rectangles)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, False)  # Disabled for performance
        painter.setClipRect(event.rect())  # Only paint dirty region
        
        # Calculate dimensions
        rect = self.rect()
        center_x = rect.width() / 2
        
        # Draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(rect)
        
        # Draw volume icon and level
        self._drawVolumeIcon(painter)
        self._drawVolumePercentage(painter)
    
    def _drawVolumeIcon(self, painter):
        """Draw an enlarged volume icon that fills the available space."""
        painter.save()
        
        # DISABLE antialiasing for faster rendering of dynamic fill bar
        painter.setRenderHint(QPainter.Antialiasing, False)
        
        rect = self.rect()
        center_x = rect.width() / 2
        
        # Define icon area (upper portion of widget)
        icon_height = rect.height() * 0.6  # 60% of widget height
        icon_width = rect.width() * 0.8    # 80% of widget width
        icon_rect = QRectF(
            center_x - icon_width/2,
            rect.height() * 0.1,  # Start 10% down from top
            icon_width,
            icon_height
        )
        
        # Draw volume bar background
        bar_rect = QRectF(
            center_x - icon_width/4,
            icon_rect.y() + icon_height * 0.2,
            icon_width/2,
            icon_height * 0.6
        )
        
        # Draw volume bar outline
        painter.setPen(QPen(QColor(150, 150, 150), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(bar_rect)
        
        # Draw volume fill based on level
        if self.volume_level > 0:
            fill_height = (bar_rect.height() * self.volume_level / 100)
            fill_rect = QRectF(
                bar_rect.x() + 2,
                bar_rect.y() + bar_rect.height() - fill_height - 2,
                bar_rect.width() - 4,
                fill_height
            )
            
            # Color based on volume level
            if self.volume_level >= 75:
                fill_color = QColor(255, 100, 100)  # Red for high volume
            elif self.volume_level >= 50:
                fill_color = QColor(255, 165, 0)    # Orange for medium
            elif self.volume_level >= 25:
                fill_color = QColor(255, 255, 0)    # Yellow for low-medium
            else:
                fill_color = QColor(100, 255, 100)  # Green for low
            
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(fill_rect)
        
        # Draw icon based on type
        if self.icon_type == "speaker":
            self._drawSpeakerIcon(painter, icon_rect)
        elif self.icon_type == "engine":
            self._drawEngineIcon(painter, icon_rect)
        
        painter.restore()
    
    def _drawSpeakerIcon(self, painter, icon_rect):
        """Draw a simple speaker icon."""
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(Qt.NoBrush)
        
        center_x = icon_rect.center().x()
        center_y = icon_rect.y() + icon_rect.height() * 0.15
        
        # Draw speaker cone (triangle)
        speaker_size = min(icon_rect.width(), icon_rect.height()) * 0.15
        cone_path = QPainterPath()
        cone_path.moveTo(center_x - speaker_size/2, center_y - speaker_size/3)
        cone_path.lineTo(center_x + speaker_size/2, center_y - speaker_size/3)
        cone_path.lineTo(center_x, center_y + speaker_size/2)
        cone_path.closeSubpath()
        
        painter.drawPath(cone_path)
        
        # Draw sound waves
        for i in range(2):
            wave_radius = speaker_size * (1.5 + i * 0.7)
            painter.drawArc(
                int(center_x - wave_radius/2),
                int(center_y - wave_radius/2),
                int(wave_radius),
                int(wave_radius),
                -45 * 16,  # Start angle
                90 * 16    # Span angle
            )
    
    def _drawEngineIcon(self, painter, icon_rect):
        """Draw a simple engine/gear icon."""
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(Qt.NoBrush)
        
        center_x = icon_rect.center().x()
        center_y = icon_rect.y() + icon_rect.height() * 0.15
        
        # Draw engine block (rectangle)
        engine_size = min(icon_rect.width(), icon_rect.height()) * 0.2
        engine_rect = QRectF(
            center_x - engine_size/2,
            center_y - engine_size/3,
            engine_size,
            engine_size * 0.8
        )
        painter.drawRect(engine_rect)
        
        # Draw exhaust lines
        line_spacing = engine_size * 0.15
        for i in range(3):
            y_pos = center_y - engine_size/6 + i * line_spacing
            painter.drawLine(
                int(center_x + engine_size/2 + 3),
                int(y_pos),
                int(center_x + engine_size/2 + engine_size/3),
                int(y_pos)
            )
    
    def _drawVolumePercentage(self, painter):
        """Draw the volume percentage at the bottom."""
        painter.save()
        
        rect = self.rect()
        
        # Set up font for percentage display
        font = QFont()
        font.setPointSize(max(8, int(rect.height() * 0.08)))  # Dynamic font size
        font.setBold(True)
        painter.setFont(font)
        
        # Draw title
        painter.setPen(QColor(150, 150, 150))
        title_rect = QRectF(0, rect.height() * 0.65, rect.width(), rect.height() * 0.15)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)
        
        # Draw percentage
        painter.setPen(Qt.white)
        percentage_text = f"{int(self.volume_level)}%"
        percentage_rect = QRectF(0, rect.height() * 0.8, rect.width(), rect.height() * 0.2)
        painter.drawText(percentage_rect, Qt.AlignCenter, percentage_text)
        
        painter.restore()