#!/usr/bin/env python3
"""
Test script to preview the new 2D car widget standalone.
Run this to see how the 2D car looks without running the full dashboard.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

# Add parent directory to path so we can import from ui
sys.path.insert(0, '..')
from ui.car2d import Car2DWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D F1 Car Widget Test")
        self.setGeometry(100, 100, 400, 600)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create the car widget
        self.car = Car2DWidget()
        layout.addWidget(self.car)
        
        # Optionally test different colors
        # self.car.setBodyColor("#0000FF")  # Blue
        # self.car.setAccentColor("#FFD700")  # Gold


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
