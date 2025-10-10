import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QConicalGradient
)
from PySide6.QtCore import (
    Qt, QRect, QPoint, QRectF, QPointF
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
        
        # Qt optimizations
        self.setAttribute(Qt.WA_OpaquePaintEvent)  # No need to erase background
        self.setAttribute(Qt.WA_NoSystemBackground)  # We draw everything ourselves
        self.setUpdatesEnabled(True)
        
        # Cache previous values to avoid unnecessary repaints
        self._prev_value = -1
        self._prev_throttle = -1
        self._prev_center_value = None
        
        # Pre-compute gauge geometry (will be calculated on first paint)
        self._geom = None
        self._static_cache = None
    
    def setValue(self, value):
        """Set the current value of the gauge."""
        new_value = max(0, min(self.max_value, value))
        # Only update if value actually changed (avoid unnecessary repaints)
        if abs(new_value - self._prev_value) > 0.5:  # Threshold to reduce micro-updates
            self.current_value = new_value
            self._prev_value = new_value
            self.update()
    
    def getValue(self):
        """Get the current value of the gauge."""
        return self.current_value
    
    def setTitle(self, title):
        """Change the title of the gauge."""
        self.title = title
        self._invalidate_static_cache()
        self.update()
    
    def setMaxValue(self, max_value):
        """Change the maximum value of the gauge."""
        self.max_value = max_value
        self.current_value = min(self.current_value, self.max_value)
        self._invalidate_static_cache()
        self.update()
    
    def setThrottle(self, throttle):
        """Set the throttle value (0-1 range)"""
        new_throttle = min(max(0, throttle), 1.0)
        # Only update if throttle actually changed significantly
        if abs(new_throttle - self._prev_throttle) > 0.01:  # 1% threshold
            self.throttle = new_throttle
            self._prev_throttle = new_throttle
            self.update()
    
    def getThrottle(self):
        """Get the current throttle value"""
        return self.throttle
    
    def setCenterValue(self, value):
        """Set a custom value to display in the center (e.g., gear number)"""
        # Only update if value actually changed
        if value != self._prev_center_value:
            self.custom_center_value = value
            self._prev_center_value = value
            self.update()
    
    def getCenterValue(self):
        """Get the custom center value"""
        return self.custom_center_value
    
    def clearCenterValue(self):
        """Clear the custom center value to show the normal gauge value"""
        self.custom_center_value = None
        self.update()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._invalidate_static_cache()

    def _invalidate_static_cache(self):
        self._static_cache = None
        self._geom = None

    def paintEvent(self, event):
        """Render the gauge on screen."""
        painter = QPainter(self)
        painter.setClipRect(event.rect())
        if self._static_cache is None or self._static_cache.size() != self.size():
            self._rebuild_static_cache()

        if self._static_cache:
            painter.drawPixmap(0, 0, self._static_cache)

        if not self._geom:
            return

        # Dynamic overlays
        self._drawThrottleArc(painter)
        self._drawValueArc(painter)
        self._drawCenterReadout(painter)
    
    def _rebuild_static_cache(self):
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            self._static_cache = None
            self._geom = None
            return

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(30, 30, 30))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        center_x = rect.width() / 2
        center_y = rect.height() / 2
        center_point = QPointF(center_x, center_y)
        radius = min(center_x, center_y) - 10
        base_size = min(rect.width(), rect.height()) * 0.9

        start_angle = 225
        span_angle = -270

        value_arc_width = 10
        value_arc_rect = QRectF(
            center_x - radius + 15,
            center_y - radius + 15,
            (radius * 2) - 30,
            (radius * 2) - 30,
        )

        throttle_inner_radius = base_size * 0.28
        throttle_thickness = base_size * 0.04
        throttle_rect = QRectF(
            center_point.x() - throttle_inner_radius,
            center_point.y() - throttle_inner_radius,
            throttle_inner_radius * 2,
            throttle_inner_radius * 2,
        )

        # Cache geometry for dynamic draws
        self._geom = {
            "center": center_point,
            "size": base_size,
            "start_angle": start_angle,
            "span_angle": span_angle,
            "value_arc_rect": value_arc_rect,
            "value_arc_width": value_arc_width,
            "throttle_rect": throttle_rect,
            "throttle_thickness": throttle_thickness,
            "throttle_inner_radius": throttle_inner_radius,
        }

        # Draw static throttle background arc
        painter.setPen(QPen(QColor(40, 40, 40), throttle_thickness, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(throttle_rect, start_angle * 16, span_angle * 16)

        # Draw outer ring
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(radius), int(radius))

        # Draw title text once (static)
        painter.setPen(QColor(200, 200, 200))
        title_font = painter.font()
        title_font.setPointSize(8)
        painter.setFont(title_font)
        painter.drawText(QRect(0, int(center_y + radius / 2), width, 30), Qt.AlignCenter, self.title)

        # Draw background value arc
        painter.setPen(QPen(QColor(60, 60, 60), value_arc_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawArc(value_arc_rect, start_angle * 16, span_angle * 16)

        # Draw tick marks and labels
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        tick_font = painter.font()
        tick_font.setPointSize(12)
        tick_font.setBold(True)
        painter.setFont(tick_font)

        for i in range(11):
            angle = math.radians(225 - i * 27)
            inner_x = center_x + (radius - 20) * math.cos(angle)
            inner_y = center_y - (radius - 20) * math.sin(angle)
            outer_x = center_x + (radius - 10) * math.cos(angle)
            outer_y = center_y - (radius - 10) * math.sin(angle)
            painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))

            if i % 2 == 0:
                text_x = center_x + (radius - 35) * math.cos(angle)
                text_y = center_y - (radius - 35) * math.sin(angle)
                tick_value = int(i * self.max_value / 10)

                if self.max_value == 14000:
                    tick_label = f"{tick_value // 1000}"
                elif self.max_value >= 1000:
                    if tick_value >= 1000 and tick_value % 1000 == 0:
                        tick_label = f"{tick_value // 1000}k"
                    else:
                        tick_label = f"{tick_value}"
                else:
                    tick_label = f"{tick_value}"

                rect_label = QRect(int(text_x) - 30, int(text_y) - 15, 60, 30)
                painter.drawText(rect_label, Qt.AlignCenter, tick_label)

        painter.end()
        self._static_cache = pixmap

    def _drawThrottleArc(self, painter):
        """Draw a throttle arc beneath the RPM arc as a curved bar with gradient colors"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        geom = self._geom
        start_angle = geom["start_angle"]
        span_angle = geom["span_angle"]

        arc_rect = geom["throttle_rect"]
        arc_thickness = geom["throttle_thickness"]

        # Draw the background arc (already cached visually but re-draw to ensure
        # the visible area stays fresh when using partial updates)
        painter.setPen(QPen(QColor(40, 40, 40), arc_thickness, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(arc_rect, start_angle * 16, span_angle * 16)

        if self.throttle > 0:
            gradient = QConicalGradient(geom["center"], start_angle - 90)
            gradient.setColorAt(0.0, QColor(0, 255, 0))
            gradient.setColorAt(0.5, QColor(255, 165, 0))
            gradient.setColorAt(1.0, QColor(255, 0, 0))
            painter.setPen(QPen(QBrush(gradient), arc_thickness, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(
                arc_rect,
                start_angle * 16,
                int(span_angle * 16 * self.throttle)
            )

        center = geom["center"]
        inner_radius = geom["throttle_inner_radius"]

        painter.setPen(Qt.white)
        font = painter.font()
        dynamic_font_size = max(12, int(geom["size"] * 0.05))
        font.setPointSize(dynamic_font_size)
        painter.setFont(font)
        
        # Position below the main display, closer to the bottom of the gauge
        # Split into two lines: label on top, value below
        label_text = f"{self.throttle_label}"  # Just the label (TH, ENG_TUN, etc.)
        value_text = f"{int(self.throttle * 100)}%"  # Just the percentage
        
        # Also adjust the text rectangle size based on the gauge size
        # Draw label text (smaller, above) - lowered position
        label_rect = QRectF(
            center.x() - inner_radius,
            center.y() + geom["size"] * 0.08,
            inner_radius * 2,
            inner_radius * 0.2
        )
        painter.drawText(label_rect, Qt.AlignCenter, label_text)
        
        # Draw value text (below the label) - lowered position
        value_rect = QRectF(
            center.x() - inner_radius,
            center.y() + geom["size"] * 0.14,
            inner_radius * 2,
            inner_radius * 0.2  # Smaller height for value
        )
        painter.drawText(value_rect, Qt.AlignCenter, value_text)
        
        painter.restore()
    
    def _drawValueArc(self, painter):
        """Draw the value arc (RPM) on the gauge."""
        painter.setRenderHint(QPainter.Antialiasing, False)

        progress = self.current_value / self.max_value if self.max_value > 0 else 0
        progress = max(0.0, min(1.0, progress))

        geom = self._geom
        if progress <= 0:
            return

        if progress < 0.7:
            gradient_color = QColor(0, 255, 0)
        elif progress < 0.9:
            gradient_color = QColor(255, 165, 0)
        else:
            gradient_color = QColor(255, 0, 0)

        painter.setPen(QPen(gradient_color, geom["value_arc_width"], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawArc(
            geom["value_arc_rect"],
            int(geom["start_angle"] * 16),
            int(geom["span_angle"] * 16 * progress)
        )

    def _drawCenterReadout(self, painter):
        geom = self._geom
        center = geom["center"]
        painter.setPen(QColor(255, 255, 255))

        if self.custom_center_value is not None:
            value_font = painter.font()
            value_font.setPointSize(48)
            value_font.setBold(True)
            painter.setFont(value_font)
            painter.drawText(QRect(0, int(center.y() - 50), self.width(), 70), Qt.AlignCenter, str(self.custom_center_value))
            return

        if "RPM" in self.title.upper():
            rpm_value = int(self.current_value)
            if rpm_value >= 1000:
                rpm_str = str(rpm_value)
                top_digits = rpm_str[:-3]
                bottom_digits = rpm_str[-3:]

                top_font = painter.font()
                top_font.setPointSize(32)
                top_font.setBold(True)
                painter.setFont(top_font)
                painter.drawText(QRect(0, int(center.y() - 52), self.width(), 35), Qt.AlignCenter, top_digits)

                bottom_font = painter.font()
                bottom_font.setPointSize(24)
                bottom_font.setBold(True)
                painter.setFont(bottom_font)
                painter.drawText(QRect(0, int(center.y() - 22), self.width(), 35), Qt.AlignCenter, bottom_digits)
            else:
                small_font = painter.font()
                small_font.setPointSize(40)
                small_font.setBold(True)
                painter.setFont(small_font)
                painter.drawText(QRect(0, int(center.y() - 50), self.width(), 70), Qt.AlignCenter, str(rpm_value))
        else:
            value_font = painter.font()
            value_font.setPointSize(48)
            value_font.setBold(True)
            painter.setFont(value_font)
            painter.drawText(QRect(0, int(center.y() - 50), self.width(), 70), Qt.AlignCenter, f"{int(self.current_value)}")
    
