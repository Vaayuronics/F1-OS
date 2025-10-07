from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
import math


class Car2DWidget(QWidget):
    """Lightweight 2D F1 car widget - top-down view with simple vector graphics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(20, 30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Car colors
        self.body_color = QColor("#DC0000")  # Ferrari red
        self.accent_color = QColor("#FFFFFF")  # White accents
        self.tire_color = QColor("#1A1A1A")  # Dark tire color
        self.nose_color = QColor("#DC0000")
        self.cockpit_color = QColor("#2D2D2D")  # Dark cockpit
        
        # Background
        self.bg_color = QColor("#232323")
        
        # Qt optimizations for static content
        self.setAttribute(Qt.WA_StaticContents)  # Widget doesn't change
        self.setAttribute(Qt.WA_OpaquePaintEvent)  # We draw everything
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setUpdatesEnabled(True)
        
    def paintEvent(self, event):
        """Draw a stylized F1 car from top-down view."""
        painter = QPainter(self)
        # Disable antialiasing for max performance
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setClipRect(event.rect())  # Only paint dirty region
        
        # Fill background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        
        # Scale factor - car should fit nicely in the widget
        scale = min(width, height) / 100.0  # Base scale on 100 units
        
        # Center point
        cx = width / 2
        cy = height / 2
        
        # Car dimensions (in base units before scaling)
        car_length = 80
        car_width = 35
        
        # Draw from bottom to top (painter's algorithm)
        
        # 1. Draw rear wing
        painter.setPen(QPen(self.accent_color, 1.5 * scale))
        painter.setBrush(QBrush(self.body_color))
        rear_wing_rect = QRectF(
            cx - 20 * scale,
            cy + 30 * scale,
            40 * scale,
            6 * scale
        )
        painter.drawRoundedRect(rear_wing_rect, 2 * scale, 2 * scale)
        
        # 2. Draw rear tires
        painter.setBrush(QBrush(self.tire_color))
        painter.setPen(QPen(QColor("#3D3D3D"), 1 * scale))
        # Left rear tire
        painter.drawRoundedRect(
            QRectF(cx - 22 * scale, cy + 18 * scale, 8 * scale, 18 * scale),
            2 * scale, 2 * scale
        )
        # Right rear tire
        painter.drawRoundedRect(
            QRectF(cx + 14 * scale, cy + 18 * scale, 8 * scale, 18 * scale),
            2 * scale, 2 * scale
        )
        
        # 3. Draw main body (rear section)
        painter.setBrush(QBrush(self.body_color))
        painter.setPen(QPen(self.accent_color, 1 * scale))
        
        body_path = QPainterPath()
        # Start from rear
        body_path.moveTo(cx - 15 * scale, cy + 30 * scale)
        # Left side going forward
        body_path.lineTo(cx - 15 * scale, cy + 10 * scale)
        body_path.lineTo(cx - 18 * scale, cy - 5 * scale)
        # Curve to nose
        body_path.lineTo(cx - 10 * scale, cy - 25 * scale)
        body_path.lineTo(cx - 3 * scale, cy - 35 * scale)
        # Nose tip
        body_path.lineTo(cx, cy - 38 * scale)
        body_path.lineTo(cx + 3 * scale, cy - 35 * scale)
        # Right side
        body_path.lineTo(cx + 10 * scale, cy - 25 * scale)
        body_path.lineTo(cx + 18 * scale, cy - 5 * scale)
        body_path.lineTo(cx + 15 * scale, cy + 10 * scale)
        body_path.lineTo(cx + 15 * scale, cy + 30 * scale)
        # Close path
        body_path.closeSubpath()
        
        painter.drawPath(body_path)
        
        # 4. Draw cockpit (driver area)
        painter.setBrush(QBrush(self.cockpit_color))
        painter.setPen(QPen(self.accent_color, 1 * scale))
        cockpit_rect = QRectF(
            cx - 8 * scale,
            cy - 5 * scale,
            16 * scale,
            20 * scale
        )
        painter.drawRoundedRect(cockpit_rect, 3 * scale, 3 * scale)
        
        # 5. Draw front tires
        painter.setBrush(QBrush(self.tire_color))
        painter.setPen(QPen(QColor("#3D3D3D"), 1 * scale))
        # Left front tire
        painter.drawRoundedRect(
            QRectF(cx - 22 * scale, cy - 20 * scale, 8 * scale, 14 * scale),
            2 * scale, 2 * scale
        )
        # Right front tire
        painter.drawRoundedRect(
            QRectF(cx + 14 * scale, cy - 20 * scale, 8 * scale, 14 * scale),
            2 * scale, 2 * scale
        )
        
        # 6. Draw front wing
        painter.setPen(QPen(self.accent_color, 1.5 * scale))
        painter.setBrush(QBrush(self.body_color))
        front_wing_rect = QRectF(
            cx - 18 * scale,
            cy - 30 * scale,
            36 * scale,
            4 * scale
        )
        painter.drawRoundedRect(front_wing_rect, 2 * scale, 2 * scale)
        
        # 7. Draw number or accent details
        painter.setPen(QPen(self.accent_color, 2 * scale))
        painter.setBrush(Qt.NoBrush)
        # Racing stripe
        painter.drawLine(
            int(cx),
            int(cy - 30 * scale),
            int(cx),
            int(cy + 25 * scale)
        )
        
        # 8. Add some detail lines for aerodynamics
        painter.setPen(QPen(QColor("#FFFFFF"), 0.5 * scale, Qt.DotLine))
        # Side pods
        painter.drawLine(
            int(cx - 12 * scale),
            int(cy + 5 * scale),
            int(cx - 12 * scale),
            int(cy + 25 * scale)
        )
        painter.drawLine(
            int(cx + 12 * scale),
            int(cy + 5 * scale),
            int(cx + 12 * scale),
            int(cy + 25 * scale)
        )
    
    def setBodyColor(self, color):
        """Change the car body color."""
        if isinstance(color, str):
            self.body_color = QColor(color)
        else:
            self.body_color = color
        self.update()
    
    def setAccentColor(self, color):
        """Change the accent color."""
        if isinstance(color, str):
            self.accent_color = QColor(color)
        else:
            self.accent_color = color
        self.update()
