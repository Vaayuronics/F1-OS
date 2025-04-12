from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QPainter, QConicalGradient, QColor
import sys
import math
import os

# PyDracula imports
from modules.ui_main import Ui_MainWindow
from modules.ui_functions import UIFunctions
from modules.app_settings import Settings

class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.rpm = 0
        self.speed = 0

        # Set background to transparent to blend with PyDracula theme
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: transparent;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(100)  # Update every 100ms

    def update_dashboard(self):
        self.rpm = (self.rpm + 100) % 8000  # Simulate RPM (0-8000)
        self.speed = (self.speed + 1) % 240  # Simulate Speed (0-240)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw RPM Gauge
        self.draw_gauge(painter, 150, 150, 100, self.rpm / 8000, "RPM", self.rpm)

        # Draw Speedometer
        self.draw_gauge(painter, 400, 150, 100, self.speed / 240, "Speed", self.speed)

    def draw_gauge(self, painter, x, y, radius, value, label, display_value):
        painter.save()
        painter.translate(x, y)

        # Draw background circle
        painter.setBrush(Qt.black)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-radius, -radius, 2 * radius, 2 * radius)

        # Draw gradient arc
        gradient = QConicalGradient(0, 0, -90)
        gradient.setColorAt(0.0, QColor(0, 255, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 0))
        gradient.setColorAt(1.0, QColor(255, 0, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPie(-radius, -radius, 2 * radius, 2 * radius, 90 * 16, -value * 360 * 16)

        # Draw text
        painter.setPen(Qt.white)
        painter.drawText(-radius, radius + 20, 2 * radius, 20, Qt.AlignCenter, f"{label}: {display_value}")

        painter.restore()


class DashboardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set up the PyDracula UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # PyDracula theme setup
        Settings.ENABLE_CUSTOM_TITLE_BAR = True
        self.setWindowTitle("Car Dashboard")
        
        # Setup window controls (minimize, maximize, close buttons)
        UIFunctions.uiDefinitions(self)
        
        # Show dashboard in the content area
        self.dashboard = DashboardWidget()
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.addWidget(self.dashboard)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Add container to the PyDracula content area
        self.ui.appLayout.addWidget(container)
        #content_area_layout.addWidget(container)
        
        # Apply PyDracula dark theme
        self.theme = "themes/py_dracula_dark.qss"
        UIFunctions.theme(self, self.theme, self.ui)  # Apply the theme to the UI
        
        # Show the application
        self.show()


if __name__ == "__main__":
    # Make sure the current directory contains PyDracula modules
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    app = QApplication(sys.argv)
    window = DashboardApp()
    sys.exit(app.exec())