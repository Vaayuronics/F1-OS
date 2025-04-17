#!/usr/bin/env python3
"""
F1 Dashboard Application with 3D Visualization
Provides telemetry gauges and 3D car visualization.
"""
import sys
from PySide6.QtWidgets import QApplication

from dashboard import F1Dashboard

def main():
    """Main function to initialize and run the application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a more modern look
    
    dashboard = F1Dashboard(stl_path=None)  # Don't use STL path for now
    dashboard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
