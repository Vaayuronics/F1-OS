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
        
        # Cache the car pixmap to avoid redrawing every frame
        self._cached_pixmap = None
        self._cached_size = None
        
    def paintEvent(self, event):
        """Draw a stylized F1 car from top-down view."""
        painter = QPainter(self)
        painter.setClipRect(event.rect())  # Only paint dirty region
        
        # Check if we need to regenerate the cached pixmap
        current_size = self.size()
        if self._cached_pixmap is None or self._cached_size != current_size:
            self._regenerate_cache()
            self._cached_size = current_size
        
        # Simply draw the cached pixmap (MUCH faster than redrawing vector graphics)
        if self._cached_pixmap:
            painter.drawPixmap(0, 0, self._cached_pixmap)
        else:
            # Fallback if cache failed
            painter.fillRect(self.rect(), self.bg_color)
    
    def _regenerate_cache(self):
        """Regenerate the cached car pixmap (called only when widget resizes)."""
        width = self.width()
        height = self.height()
        
        if width <= 0 or height <= 0:
            return
        
        # Create a new pixmap with the current widget size
        self._cached_pixmap = self._cached_pixmap or QPainter.createPixmap(width, height)
        self._cached_pixmap = QPainter.createPixmap(width, height)
        self._cached_pixmap.fill(self.bg_color)
        
        painter = QPainter(self._cached_pixmap)
        # Enable antialiasing for smooth graphics (only when caching)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
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
        painter.end()  # Finish drawing to the cached pixmap
        
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
