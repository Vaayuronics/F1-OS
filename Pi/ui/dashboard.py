from PySide6.QtWidgets import (QMainWindow, QFrame, QSplitter, 
                              QSizePolicy, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QApplication, QScrollArea)
from PySide6.QtCore import Qt, QSettings, QSize, Signal, QTimer
from PySide6.QtGui import QFont, QSurfaceFormat
from ui.gauge import GaugeWidget
from ui.car2d import Car2DWidget
from ui.battery_gauge import BatteryGaugeWidget
from ui.volume_gauge import VolumeGaugeWidget
import sys

MAX_RPM = 14000 # Max RPM for the gauge, actual should go to about 14.5k
UPDATE_MS = 50  # Update interval in milliseconds (20Hz - reduced from 30Hz to lower CPU usage on Pi)

class NotificationFrame(QWidget):
    """Individual notification frame that auto-destroys after duration."""
    
    # Signal emitted when notification is about to be destroyed
    notification_closed = Signal(object)
    
    def __init__(self, title, subtitle="", duration_ms=2000, 
                 background_color="#2D2D2D", title_color="white", 
                 subtitle_color="#CCCCCC", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 400)  # Square notification
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)
        
        # Create container frame for styling
        self.container = QFrame()
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {background_color};
                border: 2px solid #555555;
                border-radius: 15px;
            }}
        """)
        
        # Container layout
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(10)
        container_layout.setAlignment(Qt.AlignCenter)
        
        # Title label (large font)
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {title_color}; background-color: transparent;")
        
        # Subtitle label (smaller font)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet(f"color: {subtitle_color}; background-color: transparent;")
        
        # Hide subtitle if empty
        if not subtitle:
            self.subtitle_label.hide()
        
        # Add labels to container
        container_layout.addWidget(self.title_label)
        container_layout.addWidget(self.subtitle_label)
        
        # Add container to main layout
        layout.addWidget(self.container)
        
        # Timer for auto-destroy
        self.destroy_timer = QTimer()
        self.destroy_timer.setSingleShot(True)
        self.destroy_timer.timeout.connect(self._on_destroy_timeout)
        self.destroy_timer.start(duration_ms)
        
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _on_destroy_timeout(self):
        """Called when the destroy timer expires."""
        self.notification_closed.emit(self)
        self.deleteLater()


class NotificationManager(QWidget):
    """Manages multiple stacked notification frames."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # Don't block clicks
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Track active notifications (oldest first)
        self.active_notifications = []
        
        # Spacing between notifications
        self.notification_spacing = 10
        
        # Position from top of parent
        self.top_margin = 20
        
        self.hide()  # Start hidden, show when first notification appears
    
    def show_notification(self, title, subtitle="", duration_ms=2000, 
                         background_color="#2D2D2D", title_color="white", 
                         subtitle_color="#CCCCCC"):
        """
        Create and show a new notification frame.
        
        Args:
            title (str): Main title text (large font)
            subtitle (str): Subtitle text (smaller font), optional
            duration_ms (int): Duration to show notification in milliseconds
            background_color (str): Background color
            title_color (str): Title text color
            subtitle_color (str): Subtitle text color
        """
        # Create new notification frame
        notification = NotificationFrame(
            title=title,
            subtitle=subtitle,
            duration_ms=duration_ms,
            background_color=background_color,
            title_color=title_color,
            subtitle_color=subtitle_color,
            parent=self.parent()
        )
        
        # Connect close signal
        notification.notification_closed.connect(self._on_notification_closed)
        
        # Add to active list (append to end, oldest at front)
        self.active_notifications.append(notification)
        
        # Reposition all notifications
        self._reposition_notifications()
        
        # Show manager if hidden
        if not self.isVisible():
            self.show()
    
    def _on_notification_closed(self, notification):
        """Called when a notification is closed/destroyed."""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
        
        # Reposition remaining notifications
        self._reposition_notifications()
        
        # Hide manager if no more notifications
        if not self.active_notifications:
            self.hide()
    
    def _reposition_notifications(self):
        """Reposition all active notifications in a vertical stack (oldest on top)."""
        if not self.parent():
            return
        
        parent_rect = self.parent().geometry()
        center_x = parent_rect.x() + (parent_rect.width() - 400) // 2  # Center horizontally
        
        current_y = parent_rect.y() + self.top_margin
        
        # Position from top to bottom (oldest first)
        for notification in self.active_notifications:
            notification.move(center_x, current_y)
            current_y += notification.height() + self.notification_spacing

class F1Dashboard(QMainWindow):
    """Main dashboard window that displays gauges and car visualization."""
    
    def __init__(self, settings_file_path: str = None, model_path: str = None):
        """Initialize the dashboard with all widgets and layouts.""" 
        # Create QApplication if it doesn't exist
        if not QApplication.instance():
            
            # Configure OpenGL surface format for GPU rendering
            fmt = QSurfaceFormat()
            fmt.setRenderableType(QSurfaceFormat.OpenGLES)  # Force OpenGL ES (guaranteed on RPi 4)
            fmt.setVersion(2, 0)  # OpenGL ES 2.0
            fmt.setProfile(QSurfaceFormat.NoProfile)  # ES doesn't use profiles
            fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)  # Double buffering for smooth rendering
            fmt.setSwapInterval(1)  # VSync on (prevent tearing)
            fmt.setDepthBufferSize(24)  # 24-bit depth buffer
            fmt.setStencilBufferSize(8)  # 8-bit stencil buffer
            fmt.setSamples(0)  # Disable MSAA to reduce GPU load (can enable if GPU has headroom)
            QSurfaceFormat.setDefaultFormat(fmt)
            print("[Dashboard] Configured OpenGL ES 2.0 surface format for GPU rendering")
            
            # Set Qt application attributes for GPU acceleration
            QApplication.setAttribute(Qt.AA_UseOpenGLES, True)  # Force OpenGL ES backend
            QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, False)  # Disable software fallback
            QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)  # Share GL contexts (better performance)

            self.app = QApplication(sys.argv)
            self.app.setStyle('Fusion')  # Use Fusion style for a more modern look
            self.app.setApplicationName("F1-OS")
            self.app.setOrganizationName("F1-OS")
            
            print("[Dashboard] QApplication created with GPU rendering enabled")
        else:
            self.app = QApplication.instance()
            
        super().__init__()
        
        # Main window setup - borderless fullscreen for small screens
        self.setWindowTitle("")  # Remove title completely
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove window frame/title bar
        self.setMinimumSize(480, 600)  # Reduced minimum width to match screen
        self.setStyleSheet("background-color: #121212;")
        
        # Enable GPU-accelerated rendering for this window
        self.setAttribute(Qt.WA_OpaquePaintEvent)  # Tell Qt we paint entire widget (optimization)
        self.setAttribute(Qt.WA_NoSystemBackground)  # Don't waste time painting background
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)  # Reduce widget overhead
        
        # Note: GPU acceleration comes from the platform plugin (EGLFS) set via start.sh
        # Qt's raster engine is hardware-accelerated via V3D GPU driver when properly configured
        # with OpenGL ES 2.0 (see start.sh for environment variable configuration)
        
        # Set up settings from file path
        if settings_file_path:
            self.settings = QSettings(settings_file_path, QSettings.IniFormat)
        else:
            self.settings = QSettings("ui/dashboard_settings.ini", QSettings.IniFormat)
        
        self.telemetry_resize_callbacks = []
        
        # No longer using 3D model - using 2D vector graphics instead
        self.model_path = None
        self.show_model_fallback_notification = False
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create middle section with splitters for resizing
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(True)  # Allow collapsing for small screens
        
        # Set stretch factors to prevent linked movement
        # This helps maintain independent resizing of each section
        
        # RPM gauge - reduced minimum width for small screens
        self.rpm_gauge = GaugeWidget("RPM × 1000", MAX_RPM, "TH")
        self.rpm_gauge.setMinimumWidth(80)  # Reduced from 150 to 80
        self.rpm_gauge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # MPH gauge - reduced minimum width for small screens
        self.mph_gauge = GaugeWidget("MPH", 60, "ENG_TUN")
        self.mph_gauge.setMinimumWidth(80)  # Reduced from 150 to 80
        self.mph_gauge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # 2D Car visualization - lightweight image-based widget
        self.car_widget = Car2DWidget()
        self.car_widget.setMinimumWidth(20)
        self.car_widget.setMinimumHeight(30)
        self.car_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Add widgets to splitter
        self.main_splitter.addWidget(self.rpm_gauge)
        self.main_splitter.addWidget(self.car_widget)
        self.main_splitter.addWidget(self.mph_gauge)
        
        # Set stretch factors to prevent linked dragging behavior
        self.main_splitter.setStretchFactor(0, 1)  # RPM gauge - fixed proportion
        self.main_splitter.setStretchFactor(1, 1)  # 2D car widget - lightweight
        self.main_splitter.setStretchFactor(2, 1)  # MPH gauge - fixed proportion
        
        # Set initial sizes better suited for small screen (480px width)
        self.main_splitter.setSizes([120, 80, 120])  # Balanced layout with 2D car in center
        
        # Load saved splitter sizes if available
        self.load_splitter_settings()
        
        # Create a container for the upper part of the UI (just gauges)
        upper_container = QWidget()
        upper_layout = QVBoxLayout(upper_container)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addWidget(self.main_splitter, 5)  # Give more vertical space
        
        # Create the telemetry frame - very small minimum height for small screens
        self.telemetry_frame = QFrame()
        self.telemetry_frame.setStyleSheet("background-color: #1E1E1E; border-radius: 10px;")
        self.telemetry_frame.setMinimumHeight(50)  # Reduced from 80 to 50
        
        # Create main layout for telemetry frame
        telemetry_main_layout = QVBoxLayout(self.telemetry_frame)
        
        # Add title label
        telemetry_label = QLabel("TELEMETRY DATA")
        telemetry_label.setStyleSheet("color: #555; font-size: 14px;")
        telemetry_label.setAlignment(Qt.AlignCenter)
        telemetry_main_layout.addWidget(telemetry_label)
        
        # Create scroll area for telemetry data
        self.telemetry_scroll = QScrollArea()
        self.telemetry_scroll.setWidgetResizable(True)
        self.telemetry_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.telemetry_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.telemetry_scroll.setMinimumHeight(30)  # Ensure scroll area has minimum height
        self.telemetry_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.telemetry_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #333;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #666;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #888;
            }
        """)
        
        # Create widget to hold scrollable content
        self.telemetry_content_widget = QWidget()
        self.telemetry_content_layout = QVBoxLayout(self.telemetry_content_widget)
        self.telemetry_content_layout.setContentsMargins(5, 5, 5, 5)
        self.telemetry_content_layout.setSpacing(2)
        
        self.telemetry_scroll.setWidget(self.telemetry_content_widget)
        telemetry_main_layout.addWidget(self.telemetry_scroll)
        
        # Initialize telemetry widget pools for ultra-fast updates
        self._telemetry_widget_pool = {}  # Pool of reusable row widgets
        self._telemetry_active_keys = []  # Currently displayed keys in order
        self._max_telemetry_rows = 20  # Pre-allocate this many rows
        
        # Pre-create widget pool
        scroll_width = self.telemetry_scroll.width()
        base_font_size = max(8, min(14, int(scroll_width / 30)))
        for i in range(self._max_telemetry_rows):
            row_widget, label_widget, value_widget = self._create_telemetry_row(base_font_size)
            row_widget.hide()  # Start hidden
            self.telemetry_content_layout.addWidget(row_widget)
            self._telemetry_widget_pool[i] = {
                'row': row_widget,
                'label': label_widget,
                'value': value_widget,
                'key': None  # Current key being displayed
            }
        
        # Add stretch at the end
        self.telemetry_content_layout.addStretch()
        
        # Create volume gauges
        self.engine_volume_gauge = VolumeGaugeWidget("ENG", "engine")
        self.engine_volume_gauge.setVolumeLevel(75)  # Default engine volume
        
        self.music_volume_gauge = VolumeGaugeWidget("MUS", "speaker") 
        self.music_volume_gauge.setVolumeLevel(60)  # Default music volume
        
        # Create battery gauge
        self.battery_gauge = BatteryGaugeWidget()
        self.battery_gauge.setBatteryLevel(85)  # Default battery level
        
        # Create horizontal splitter for bottom section (telemetry + volume bars + battery)
        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.bottom_splitter.setHandleWidth(8)
        self.bottom_splitter.setChildrenCollapsible(False)
        self.bottom_splitter.addWidget(self.telemetry_frame)     # Telemetry on left
        self.bottom_splitter.addWidget(self.engine_volume_gauge) # Engine volume 
        self.bottom_splitter.addWidget(self.music_volume_gauge)  # Music volume
        self.bottom_splitter.addWidget(self.battery_gauge)       # Battery on right
        
        # Set initial sizes for bottom splitter (telemetry + 3 narrow gauges)
        self.bottom_splitter.setSizes([240, 60, 60, 60])  # More space for telemetry, equal space for gauges
        
        # Create a new vertical splitter to separate main content from bottom section
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.vertical_splitter.setHandleWidth(8)
        self.vertical_splitter.setChildrenCollapsible(False)
        self.vertical_splitter.addWidget(upper_container)     # Upper content first
        self.vertical_splitter.addWidget(self.bottom_splitter) # Bottom section with telemetry + battery
        
        # Set initial sizes for the vertical splitter - much more compact
        # On 480x800 screen, make bottom panel smaller
        self.vertical_splitter.setSizes([600, 120])  # Larger upper section, smaller bottom
        
        # Add the vertical splitter to the main layout
        main_layout.addWidget(self.vertical_splitter)
        
        # Style the splitter handle to make it more visible
        self.setStyleSheet("""
            QSplitter::handle {
                background-color: #555555;
                border: 1px solid #777777;
            }
            QSplitter::handle:hover {
                background-color: #666666;
            }
            QSplitter::handle:pressed {
                background-color: #777777;
            }
        """)
        
        # Connect splitter's splitterMoved signal
        self.vertical_splitter.splitterMoved.connect(self._on_telemetry_resize)
        self.bottom_splitter.splitterMoved.connect(self.save_bottom_splitter_settings)
        
        # Initialize window geometry and settings
        self._setup_window_geometry()
        self._connect_geometry_events()
        
        # Set up data pull timer (30Hz refresh rate) but DON'T start it yet
        self.data_timer = QTimer()
        self.data_timer.setTimerType(Qt.PreciseTimer)  # Use precise timing
        self.data_timer.timeout.connect(self._pull_and_apply_data)
        # Timer will be started in run() after window is shown
        
        # Enable Qt's automatic update coalescing for better performance
        self.setAttribute(Qt.WA_OpaquePaintEvent)  # We draw everything ourselves
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        # Initialize startup animation variables
        self.startup_animation_active = False
        self.startup_timer = QTimer()
        self.startup_timer.timeout.connect(self._update_startup_animation)
        self.animation_step = 0
        self.animation_phase = 0  # 0: ramp up, 1: oscillate
        self.animation_start_time = 0
        
        # Right bar mode tracking (engine tune vs regen braking)
        self.right_bar_mode = "engine"  # "engine" or "regen"
        self.engine_tune_value = 0.0
        self.regen_brake_value = 0.0
        
        # Create notification manager
        self.notification_manager = NotificationManager(self)
    
    def run(self):
        """Show the dashboard and run the application."""
        self.show()
        
        # Start the startup animation after showing
        self.start_startup_animation()
        return self.app.exec()
    
    def set_data_source(self, data_getter_func):
        """Set a function that returns the latest data dict."""
        self.external_data_source = data_getter_func
    
    def set_interrupted_event(self, event):
        """Set the threading.Event that signals shutdown."""
        self._interrupted_event = event
    
    def _pull_and_apply_data(self):
        """Pull data from external source and apply it (runs on UI thread via QTimer)."""
        if self.external_data_source:
            try:
                # Get latest data from shared dict (always current, never old)
                data = self.external_data_source()
                if data:
                    self._apply_data_dict(data)
            except RuntimeError:
                # Dashboard is being deleted, stop timer
                self.data_timer.stop()
            except Exception as e:
                print(f"[Dashboard] Error pulling data: {e}")
    
    def _apply_data_dict(self, data: dict):
        """Apply telemetry data to widgets. Must run on the UI thread."""
        if 'RPM' in data:
            self.setRPM(data['RPM'])
            data.pop('RPM')
        if 'Speed' in data:
            self.setSpeed(data['Speed'])
            data.pop('Speed')
        if 'Throttle' in data:
            if not self.startup_animation_active:
                self.setThrottle(data['Throttle'])
                data.pop('Throttle')
            else:
                data.pop('Throttle')  # Remove but don't apply during animation
        if 'Engine Tune' in data:
            if not self.startup_animation_active:
                self.setEnginetune(data['Engine Tune'])
                data.pop('Engine Tune')
            else:
                data.pop('Engine Tune')
        if 'Regen Brake' in data:
            if not self.startup_animation_active:
                self.setRegenBrake(data['Regen Brake'])
                data.pop('Regen Brake')
            else:
                data.pop('Regen Brake')
        if 'Mode Switch' in data:
            # Detect switch press (assuming it's a boolean or toggle signal)
            if data['Mode Switch']:
                self.toggle_right_bar_mode()
            data.pop('Mode Switch')
        if 'Wheel Rotation' in data:
            self.setWheelRotation(data['Wheel Rotation'])
            data.pop('Wheel Rotation')
        if 'Gear' in data:
            self.setGear(data['Gear'])
            data.pop('Gear')
        if 'Battery' in data:
            self.setBattery(data['Battery'])
            data.pop('Battery')
        if 'Engine Volume' in data:
            print(f"[DEBUG UI] Setting Engine Volume: {data['Engine Volume']}")
            self.setEngineVolume(data['Engine Volume'])
            data.pop('Engine Volume')
        if 'Music Volume' in data:
            print(f"[DEBUG UI] Setting Music Volume: {data['Music Volume']}")
            self.setMusicVolume(data['Music Volume'])
            data.pop('Music Volume')
        if 'Alert Title' in data:
            alert_title = data['Alert Title']
            alert_text = data['Alert Message'] if 'Alert Message' in data else ""
            self.show_notification(alert_title, alert_text, 3000)
            data.pop('Alert Title')
            if 'Alert Message' in data:
                data.pop('Alert Message')

        # Update telemetry display with remaining fields
        display_data = {k: v for k, v in data.items()}
        self.updateTelemetryDisplay(display_data)
    
    def enable_fullscreen(self):
        """Enable borderless fullscreen mode suitable for Raspberry Pi."""
        # Move to top-left corner and expand to full screen
        self.move(0, 0)
        self.showFullScreen()
        # Alternative: use desktop geometry for exact screen size
        # desktop = QApplication.desktop()
        # self.setGeometry(desktop.screenGeometry())
    
    def _setup_window_geometry(self):
        """Set up window size and position from settings."""
        # Set size from settings if available, otherwise use default for small screen
        if self.settings.contains("window/size"):
            size_str = self.settings.value("window/size")
            try:
                width, height = map(int, size_str.split(","))
                self.resize(width, height)
            except:
                self.resize(QSize(480, 800))  # Default to actual screen size
        else:
            self.resize(QSize(480, 800))  # Default to actual screen size
        
        # Set position from settings if available
        if self.settings.contains("window/position"):
            pos_str = self.settings.value("window/position")
            try:
                x, y = map(int, pos_str.split(","))
                self.move(x, y)
            except:
                # Use default position
                pass
        
        # Load telemetry box size if available
        if self.settings.contains("telemetry/size"):
            telemetry_size_str = self.settings.value("telemetry/size")
            try:
                width, height = map(int, telemetry_size_str.split(","))
                self.set_telemetry_box_size(width, height)
            except:
                # Use default telemetry box size
                pass
        
        # Important: Force load splitter settings here to make sure they're applied
        # after all other layout operations
        self.load_splitter_settings()
        
        # Load bottom splitter settings
        self.load_bottom_splitter_settings()
    
    def _connect_geometry_events(self):
        """Connect window resize and move events to save settings."""
        def on_window_geometry_changed():
            size = self.size()
            pos = self.pos()
            self.settings.setValue("window/size", f"{size.width()},{size.height()}")
            self.settings.setValue("window/position", f"{pos.x()},{pos.y()}")
            
            # Also save telemetry box size
            telemetry_size = self.get_telemetry_box_size()
            if telemetry_size:
                self.settings.setValue("telemetry/size", f"{telemetry_size[0]},{telemetry_size[1]}")
        
        self.resizeEvent = lambda event: (super(F1Dashboard, self).resizeEvent(event), on_window_geometry_changed())
        self.moveEvent = lambda event: (super(F1Dashboard, self).moveEvent(event), on_window_geometry_changed())
        
        # Connect telemetry box resize event
        self.connect_telemetry_resize_event(on_window_geometry_changed)
    
    def setRPM(self, rpm):
        """Set the RPM gauge value."""
        self.rpm_gauge.setValue(rpm)
    
    def setSpeed(self, speed):
        """Set the speed gauge value."""
        self.mph_gauge.setValue(speed)
    
    def getRPM(self):
        """Get current RPM value."""
        return self.rpm_gauge.getValue()
    
    def setGear(self, gear):
        """Set the gear display on the RPM gauge center."""
        # Format gear appropriately
        if gear == 0:
            gear_text = "N"  # Neutral
        elif gear == -1:
            gear_text = "R"  # Reverse
        else:
            gear_text = str(gear)  # Gear number
        
        self.rpm_gauge.setCenterValue(gear_text)
    
    def getGear(self):
        """Get current gear value from RPM gauge center."""
        return self.rpm_gauge.getCenterValue()
    
    def getSpeed(self):
        """Get current speed value."""
        return self.mph_gauge.getValue()
    
    def setThrottle(self, throttle):
        """Set the throttle value (0-1 range)."""
        self.rpm_gauge.setThrottle(throttle)
    
    def getThrottle(self):
        """Get current throttle value."""
        return self.rpm_gauge.getThrottle()
    
    def setBattery(self, battery_level):
        """Set the battery level (0-100)."""
        self.battery_gauge.setBatteryLevel(battery_level)
    
    def getBattery(self):
        """Get current battery level."""
        return self.battery_gauge.getBatteryLevel()
    
    def setEngineVolume(self, volume_level):
        """Set the engine volume level (0-100)."""
        self.engine_volume_gauge.setVolumeLevel(volume_level)
    
    def getEngineVolume(self):
        """Get current engine volume level."""
        return self.engine_volume_gauge.getVolumeLevel()
    
    def setMusicVolume(self, volume_level):
        """Set the music volume level (0-100)."""
        self.music_volume_gauge.setVolumeLevel(volume_level)
    
    def getMusicVolume(self):
        """Get current music volume level."""
        return self.music_volume_gauge.getVolumeLevel()
    
    def setTune(self, tune):
        """Internal method: Set the tune value based on current mode (0-1 range). Use setEnginetune() or setRegenBrake() directly instead."""
        if self.right_bar_mode == "engine":
            self.setEnginetune(tune)
        else:
            self.setRegenBrake(tune)
    
    def getTune(self):
        """Get current tune value based on active mode (engine or regen)."""
        return self.mph_gauge.getThrottle()
    
    def toggle_right_bar_mode(self):
        """Toggle between engine tune and regen braking mode."""
        if self.right_bar_mode == "engine":
            self.right_bar_mode = "regen"
            self.update_right_bar_display()
        else:
            self.right_bar_mode = "engine"
            self.update_right_bar_display()
        print(f"Right bar mode switched to: {self.right_bar_mode}")
    
    def update_right_bar_display(self):
        """Update the right bar label and value based on current mode."""
        if self.right_bar_mode == "engine":
            # Set label to engine tune
            if hasattr(self.mph_gauge, 'setLabel'):
                self.mph_gauge.setLabel("ENG_TUN")
            # Set current value to engine tune value
            if not self.startup_animation_active:
                self.mph_gauge.setThrottle(self.engine_tune_value)
        else:  # regen mode
            # Set label to regen
            if hasattr(self.mph_gauge, 'setLabel'):
                self.mph_gauge.setLabel("REGN")
            # Set current value to regen brake value
            if not self.startup_animation_active:
                self.mph_gauge.setThrottle(self.regen_brake_value)
    
    def setEnginetune(self, tune_value):
        """Set the engine tune value (0-1 range)."""
        self.engine_tune_value = tune_value
        # Update display if we're in engine mode (allow during startup animation)
        if self.right_bar_mode == "engine":
            self.mph_gauge.setThrottle(tune_value)
    
    def getEnginetune(self):
        """Get current engine tune value."""
        return self.engine_tune_value
    
    def setRegenBrake(self, regen_value):
        """Set the regen braking value (0-1 range)."""
        self.regen_brake_value = regen_value
        # Update display if we're in regen mode (allow during startup animation)
        if self.right_bar_mode == "regen":
            self.mph_gauge.setThrottle(regen_value)
    
    def getRegenBrake(self):
        """Get current regen braking value."""
        return self.regen_brake_value
    
    def getRightBarMode(self):
        """Get the current right bar mode ('engine' or 'regen')."""
        return self.right_bar_mode
    
    def show_notification(self, title, subtitle="", duration_ms=2000, background_color="#2D2D2D", title_color="#FFFFFF", subtitle_color="#CCCCCC"):
        """
        Show a temporary notification that stacks with other notifications.
        Each notification is independent and will auto-destroy after its duration.
        
        Args:
            title (str): Main title text (large font)
            subtitle (str): Subtitle text (smaller font), optional
            duration_ms (int): Duration to show notification in milliseconds (default: 2000ms = 2 seconds)
            background_color (str): Background color (default: dark gray)
            title_color (str): Title text color (default: white)
            subtitle_color (str): Subtitle text color (default: light gray)
        
        Example usage:
            dashboard.show_notification("HEADLIGHTS", "ON", 1500, "#1E4A2E", "white", "#90EE90")
            dashboard.show_notification("HAZARDS", "ACTIVATED", 2000, "#4A2E1E", "white", "#FFD700")
        """
        self.notification_manager.show_notification(title, subtitle, duration_ms, background_color, title_color, subtitle_color)
    
    def setWheelRotation(self, angle_degrees):
        """Set the wheel rotation angle in degrees."""
        self.car_widget.setWheelAngle(angle_degrees)
    
    def getWheelRotation(self):
        """Get the current wheel rotation angle."""
        return self.car_widget.getWheelAngle()
    
    def animateWheelsFromSpeed(self, speed_mph):
        """Animate wheel rotation based on vehicle speed."""
        # Convert speed to wheel RPM (rough approximation)
        # Assuming wheel diameter of ~24 inches (common for race cars)
        wheel_circumference_feet = 3.14159 * 2  # 24 inches = 2 feet
        feet_per_minute = speed_mph * 5280 / 60  # Convert MPH to feet per minute
        wheel_rpm = feet_per_minute / wheel_circumference_feet
        
        self.car_widget.animate_wheel_rotation(wheel_rpm)
    
    def resetValues(self):
        """Reset all dashboard values to zero/default."""
        self.rpm_gauge.setValue(0)
        self.rpm_gauge.setThrottle(0)
        self.mph_gauge.setValue(0)
    
    def _create_telemetry_row(self, base_font_size):
        """Create a reusable telemetry row widget."""
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel()
        label_widget.setStyleSheet(f"color: #AAA; font-size: {base_font_size}px;")
        label_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        label_widget.setWordWrap(True)
        
        value_widget = QLabel()
        value_widget.setStyleSheet(f"color: white; font-size: {base_font_size}px; font-weight: bold;")
        value_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        value_widget.setWordWrap(True)
        
        row_layout.addWidget(label_widget, 1)
        row_layout.addWidget(value_widget, 1)
        
        row_widget = QWidget()
        row_widget.setLayout(row_layout)
        row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        return row_widget, label_widget, value_widget
    
    def updateTelemetryDisplay(self, data_dict):
        """Update telemetry display with ZERO widget creation - only setText() calls."""
        if not data_dict:
            return  # Skip hiding - waste of time
        
        data_keys = list(data_dict.keys())
        num_items = len(data_keys)
        
        # Batch updates to reduce repaints (Qt will batch automatically, but we help it)
        updates_made = False
        
        # Update visible rows with new data (ONLY setText calls when values change)
        for i in range(min(num_items, self._max_telemetry_rows)):
            key = data_keys[i]
            value = data_dict[key]
            pool_entry = self._telemetry_widget_pool[i]
            
            # Only update label if key changed
            if pool_entry['key'] != key:
                pool_entry['label'].setText(f"{key}:")
                pool_entry['key'] = key
                pool_entry['row'].show()
                updates_made = True
            
            # Only update value if it actually changed (crucial optimization)
            value_str = str(value)
            if pool_entry.get('last_value') != value_str:
                pool_entry['value'].setText(value_str)
                pool_entry['last_value'] = value_str
                updates_made = True
        
        # Optional: force a single repaint if any updates were made
        # Qt usually batches these automatically, but this ensures it happens
        if updates_made and num_items < 5:  # Only for small updates
            self.telemetry_content_widget.update()
    
    def clearLayout(self, layout):
        """Helper method to clear a layout recursively."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
            elif child.layout():
                self.clearLayout(child.layout())
    
    def load_splitter_settings(self):
        """Load saved splitter sizes from settings.""" 
        if self.settings.contains("splitter/sizes"):
            # Convert the saved string back to a list of integers
            sizes_str = self.settings.value("splitter/sizes")
            try:
                if isinstance(sizes_str, str):
                    # Handle string representation
                    sizes = [int(x) for x in sizes_str.split(",")]
                else:
                    # Handle list representation
                    sizes = [int(x) for x in sizes_str]
                
                # Apply the sizes only if we have the right number of elements
                if len(sizes) == self.main_splitter.count():
                    self.main_splitter.setSizes(sizes)
                    # Force the layout to update immediately
                    self.main_splitter.refresh()
                    print(f"Loaded splitter sizes: {sizes}")
                    return True  # Successfully loaded
            except (ValueError, TypeError) as e:
                print(f"Error loading splitter sizes: {e}")
        
        return False  # Failed to load
    
    def save_splitter_settings(self):
        """Save current splitter sizes to settings.""" 
        sizes = self.main_splitter.sizes()
        # Store as comma-separated string to avoid type issues
        self.settings.setValue("splitter/sizes", ",".join(str(x) for x in sizes))
        print(f"Saved splitter sizes: {sizes}")
    
    def save_bottom_splitter_settings(self):
        """Save current bottom splitter sizes to settings.""" 
        sizes = self.bottom_splitter.sizes()
        # Store as comma-separated string to avoid type issues
        self.settings.setValue("bottom_splitter/sizes", ",".join(str(x) for x in sizes))
        print(f"Saved bottom splitter sizes: {sizes}")
    
    def load_bottom_splitter_settings(self):
        """Load saved bottom splitter sizes from settings.""" 
        if self.settings.contains("bottom_splitter/sizes"):
            # Convert the saved string back to a list of integers
            sizes_str = self.settings.value("bottom_splitter/sizes")
            try:
                if isinstance(sizes_str, str):
                    # Handle string representation
                    sizes = [int(x) for x in sizes_str.split(",")]
                else:
                    # Handle list representation
                    sizes = [int(x) for x in sizes_str]
                
                # Apply the sizes only if we have the right number of elements
                if len(sizes) == self.bottom_splitter.count():
                    self.bottom_splitter.setSizes(sizes)
                    print(f"Loaded bottom splitter sizes: {sizes}")
                else:
                    print(f"Bottom splitter size mismatch: saved {len(sizes)}, current {self.bottom_splitter.count()}")
            except Exception as e:
                print(f"Error loading bottom splitter sizes: {e}")
        
        return False  # Failed to load
    

    
    def closeEvent(self, event):
        """Override close event to save settings before closing.""" 
        self.save_splitter_settings()
        super().closeEvent(event)
    
    def set_telemetry_box_size(self, width, height):
        """
        Set the dimensions of the telemetry data box.
        
        Args:
            width (int): The width of the telemetry box
            height (int): The height of the telemetry box
        """
        if hasattr(self, 'vertical_splitter'):
            sizes = self.vertical_splitter.sizes()
            if len(sizes) >= 2:
                total_height = sum(sizes)
                # Set telemetry height (bottom widget)
                self.vertical_splitter.setSizes([total_height - height, height])
    
    def get_telemetry_box_size(self):
        """
        Get the current dimensions of the telemetry data box.
        
        Returns:
            tuple: A tuple containing (width, height) of the telemetry box
        """
        if hasattr(self, 'telemetry_frame') and hasattr(self, 'vertical_splitter'):
            sizes = self.vertical_splitter.sizes()
            if len(sizes) >= 2:
                return (self.telemetry_frame.width(), sizes[1])  # Second widget is telemetry
        return None
    
    def connect_telemetry_resize_event(self, callback):
        """
        Connect a callback function to be called when the telemetry box is resized.
        
        Args:
            callback (function): The function to call when the telemetry box is resized
        """
        if callback not in self.telemetry_resize_callbacks:
            self.telemetry_resize_callbacks.append(callback)
    
    def _on_telemetry_resize(self, pos, index):
        """
        Internal method called when the splitter is moved, triggering telemetry box resize.
        
        Args:
            pos (int): The position of the splitter
            index (int): The index of the splitter handle that was moved
        """
        # Execute all registered callbacks
        for callback in self.telemetry_resize_callbacks:
            callback()
    
    def reset_view(self):
        """Reset the dashboard view to default state and make gauges symmetrical."""
        # Reset any existing view settings
        
        # Make RPM and MPH gauges equal size
        if hasattr(self, 'main_splitter'):
            sizes = self.main_splitter.sizes()
            if len(sizes) == 3:  # RPM, car, MPH layout
                # Calculate total width
                total_width = sum(sizes)
                
                # Calculate gauge width (equal for both)
                gauge_width = int((total_width - sizes[1]) / 2)
                
                # Set sizes: [RPM gauge, car widget, MPH gauge]
                self.main_splitter.setSizes([gauge_width, sizes[1], gauge_width])
                
                # Save the new splitter sizes
                self.save_splitter_settings()
        
        # Reset other view elements as needed
    
    def start_startup_animation(self):
        """Start the startup animation sequence."""
        import time
        self.startup_animation_active = True
        self.animation_step = 0
        self.animation_phase = 0
        self.animation_start_time = time.time()
        self.startup_timer.start(16)  # ~60fps animation (16ms intervals)
        print("Starting startup animation...")
    
    def _update_startup_animation(self):
        """Update the startup animation each frame."""
        import time
        current_time = time.time()
        elapsed = current_time - self.animation_start_time
        
        if self.animation_phase == 0:
            # Phase 1: Ramp up from 0 to 100% over 2 seconds
            if elapsed < 2.0:
                progress = elapsed / 2.0  # 0.0 to 1.0
                throttle_value = progress  # 0.0 to 1.0
                tune_value = progress     # 0.0 to 1.0
                
                # Apply smooth easing (ease-out)
                throttle_value = 1 - (1 - throttle_value) ** 3
                tune_value = 1 - (1 - tune_value) ** 3
                rpm_eased = 1 - (1 - progress) ** 3
                speed_eased = 1 - (1 - progress) ** 3
                
                # Update all the gauges
                self.setThrottle(throttle_value)
                # Only animate the currently active right bar mode
                if self.right_bar_mode == "engine":
                    self.setEnginetune(tune_value)
                else:
                    self.setRegenBrake(tune_value)
                self.setRPM(rpm_eased * MAX_RPM)
                self.setSpeed(speed_eased * 60)
            else:
                # Move to phase 2
                self.animation_phase = 1
                self.animation_start_time = current_time  # Reset timer for phase 2
                
        elif self.animation_phase == 1:
            # Phase 2: Oscillate between 80-100% for 4 seconds
            if elapsed < 4.0:
                # Create oscillation between 0.8 and 1.0
                import math
                oscillation_frequency = 2.0  # 2 cycles per second
                sine_wave = math.sin(elapsed * oscillation_frequency * 2 * math.pi)
                
                # Map sine wave (-1 to 1) to range (0.8 to 1.0)
                base_value = 0.9  # Center point
                amplitude = 0.1   # ±10% oscillation
                throttle_value = base_value + (sine_wave * amplitude)
                tune_value = base_value + (sine_wave * amplitude * 0.8)  # Slightly different for variety
                
                # RPM and Speed oscillation (slightly different frequencies for variety)
                rpm_sine = math.sin(elapsed * 1.8 * 2 * math.pi)  # Slightly different frequency
                speed_sine = math.sin(elapsed * 2.2 * 2 * math.pi)  # Different frequency
                
                rpm_oscillation = base_value + (rpm_sine * amplitude * 0.9)
                speed_oscillation = base_value + (speed_sine * amplitude * 0.7)
                
                # Update all gauges
                self.setThrottle(throttle_value)
                self.setTune(tune_value)
                self.setRPM(rpm_oscillation * MAX_RPM)
                self.setSpeed(speed_oscillation * 60)
            else:
                # Animation complete
                self.end_startup_animation()
    
    def end_startup_animation(self):
        """End the startup animation and return to normal operation."""
        self.startup_timer.stop()
        self.startup_animation_active = False
        
        # Reset all gauges to default values
        self.setThrottle(0.0)
        self.setEnginetune(0.0)
        self.setRegenBrake(0.0)
        self.setRPM(0.0)
        self.setSpeed(0.0)
        
        print("Startup animation complete!")

        # INFO: TIMER STARTED HERE
        # Start data timer AFTER window is shown and ready
        self.data_timer.start(UPDATE_MS)
    
    def is_animation_active(self):
        """Check if startup animation is currently running."""
        return self.startup_animation_active