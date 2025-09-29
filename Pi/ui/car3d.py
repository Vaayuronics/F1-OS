from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QFrame
from PySide6.QtGui import QColor, QVector3D, QSurfaceFormat, QQuaternion
from PySide6.QtCore import Qt, QSize, QUrl, QTimer, Signal
from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
from PySide6.Qt3DInput import Qt3DInput
import os

class Car3DWidget(QWidget):
    """Widget that displays a 3D model of an F1 car."""
    
    def __init__(self, model_path=None, parent=None):
        """Initialize the 3D car widget."""
        super().__init__(parent)
        self.setMinimumSize(20, 30)  # Ultra small minimum size for tiny screen
        self.model_path = model_path
        self.model_loaded = False
        self.model_scale = 1.0
        
        # Configure surface format for better rendering
        surface_format = QSurfaceFormat()
        surface_format.setSamples(4)  # Antialiasing
        surface_format.setDepthBufferSize(24)
        QSurfaceFormat.setDefaultFormat(surface_format)
        
        # Set up layout for the 3D view
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create a frame to contain the 3D view
        container_frame = QFrame(self)
        container_frame.setFrameStyle(QFrame.StyledPanel)
        container_frame.setStyleSheet("background-color: #232323; border-radius: 5px;")
        container_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        container_layout = QVBoxLayout(container_frame)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Create a Qt3D window with minimal size constraints
        self.view = Qt3DExtras.Qt3DWindow()
        self.view.setFlags(Qt.Widget)  # Make sure it behaves like a regular widget
        
        self.container = QWidget.createWindowContainer(self.view, container_frame)
        self.container.setFocusPolicy(Qt.StrongFocus)  # Allow keyboard focus
        self.container.setMinimumSize(QSize(20, 30))  # Even smaller minimum for ultra-compact view
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Force the container to respect very small sizes
        self.container.resize(40, 50)
        
        container_layout.addWidget(self.container)
        layout.addWidget(container_frame)
        
        # Log the model path
        if model_path:
            print(f"Setting up 3D scene with model: {model_path}")
            print(f"File exists: {os.path.exists(model_path)}")
        
        # Set up the 3D scene
        self.setup_scene()
    
    def setup_scene(self):
        """Set up the 3D scene with the car model."""
        # Create root entity
        self.rootEntity = Qt3DCore.QEntity()
        
        # Set a dark background color for the view
        self.view.defaultFrameGraph().setClearColor(QColor(35, 35, 40))
        
        # Create a material for the model
        self.material = Qt3DExtras.QPhongMaterial(self.rootEntity)
        self.material.setDiffuse(QColor(220, 50, 50))  # Bright red color
        self.material.setSpecular(QColor(255, 255, 255))
        self.material.setShininess(150)
        
        # Create model entity
        self.modelEntity = Qt3DCore.QEntity(self.rootEntity)
        
        # Create transform component for the model
        self.modelTransform = Qt3DCore.QTransform()
        self.modelEntity.addComponent(self.modelTransform)
        
        # Default model size
        self.model_width = 10
        self.model_height = 10
        self.model_depth = 10
        
        # Set up the car model
        if self.model_path and os.path.exists(self.model_path):
            # Detect file extension
            _, ext = os.path.splitext(self.model_path)
            ext = ext.lower()
            
            if ext == '.stl':
                # For STL files, use a mesh loaded directly
                self.modelMesh = Qt3DRender.QMesh()
                self.modelMesh.setSource(QUrl.fromLocalFile(self.model_path))
                self.modelEntity.addComponent(self.modelMesh)
                self.modelEntity.addComponent(self.material)
                
                # Connect to the status changed signal to detect loading
                self.modelMesh.statusChanged.connect(self.handle_mesh_status_changed)
                
                # STL models are usually in mm, scale appropriately
                self.modelTransform.setScale(0.1)
                
            elif ext in ['.fbx', '.obj']:
                # For FBX/OBJ files use scene loader
                self.modelLoader = Qt3DRender.QSceneLoader(self.modelEntity)
                self.modelLoader.setSource(QUrl.fromLocalFile(self.model_path))
                self.modelEntity.addComponent(self.modelLoader)
                
                print(f"Loading {ext} model: {self.model_path}")
                
                # Connect to the status changed signal to detect loading
                self.modelLoader.statusChanged.connect(self.handle_scene_status_changed)
                
                # Set a neutral scale for FBX models - typically they're already in reasonable units
                self.modelTransform.setScale(1.0)
            
            print(f"Model transform set, scale: {self.modelTransform.scale()}")
        else:
            # Use a sphere as fallback
            print("Using fallback sphere model")
            self.modelMesh = Qt3DExtras.QSphereMesh()
            self.modelMesh.setRadius(5.0)
            self.modelMesh.setRings(32)
            self.modelMesh.setSlices(32)
            
            self.modelTransform.setScale(1.0)
            self.modelEntity.addComponent(self.modelMesh)
            self.modelEntity.addComponent(self.material)
            self.model_loaded = True
        
        # Add comprehensive lighting
        self.setupLights()
        
        # Set camera
        self.camera = self.view.camera()
        self.camera.lens().setPerspectiveProjection(45.0, 16.0/9.0, 0.1, 1000.0)
        self.camera.setPosition(QVector3D(0, 0, 20))
        self.camera.setViewCenter(QVector3D(0, 0, 0))
        self.camera.setUpVector(QVector3D(0, 1, 0))
        
        # Use a better orbit camera controller
        self.camController = Qt3DExtras.QOrbitCameraController(self.rootEntity)
        self.camController.setLinearSpeed(80.0)
        self.camController.setLookSpeed(300.0)
        self.camController.setZoomInLimit(0.01)  # Allow very close zoom for small models
        self.camController.setCamera(self.camera)
        
        # Set root entity
        self.view.setRootEntity(self.rootEntity)
        
        # Initialize wheel tracking
        self.wheel_entities = []
        self.wheel_transforms = []
        self.current_wheel_angle = 0.0
    
    def setupLights(self):
        """Set up comprehensive lighting for the scene."""
        # Ambient light for overall scene illumination
        self.ambient_light = Qt3DCore.QEntity(self.rootEntity)
        ambient_light_component = Qt3DRender.QDirectionalLight(self.ambient_light)
        ambient_light_component.setColor(QColor(100, 100, 100))
        ambient_light_component.setIntensity(0.5)
        self.ambient_light.addComponent(ambient_light_component)
        
        # Create multiple point lights around the object
        light_positions = [
            QVector3D(20, 20, 20),   # Top-right-front
            QVector3D(-20, 20, 20),  # Top-left-front
            QVector3D(0, -20, 20),   # Bottom-front
            QVector3D(0, 0, -20)     # Back
        ]
        
        light_colors = [
            QColor(255, 255, 255),  # White
            QColor(230, 230, 255),  # Slightly blue
            QColor(255, 255, 230),  # Slightly yellow
            QColor(230, 255, 230)   # Slightly green
        ]
        
        light_intensities = [1.0, 0.8, 0.8, 0.7]
        
        self.lights = []
        
        for i, pos in enumerate(light_positions):
            light_entity = Qt3DCore.QEntity(self.rootEntity)
            light = Qt3DRender.QPointLight(light_entity)
            light.setColor(light_colors[i])
            light.setIntensity(light_intensities[i])
            
            light_transform = Qt3DCore.QTransform(light_entity)
            light_transform.setTranslation(pos)
            
            light_entity.addComponent(light)
            light_entity.addComponent(light_transform)
            
            self.lights.append(light_entity)
    
    def handle_mesh_status_changed(self, status):
        """Handle mesh loading status changes."""
        if status == Qt3DRender.QMesh.Ready:
            print("STL mesh loaded successfully")
            self.model_loaded = True
            # Try to find wheel entities after model loads
            QTimer.singleShot(500, self.find_wheel_entities)
        elif status == Qt3DRender.QMesh.Error:
            print("Error loading STL mesh")
    
    def handle_scene_status_changed(self, status):
        """Handle scene loading status changes."""
        if status == Qt3DRender.QSceneLoader.Ready:
            print("FBX/OBJ scene loaded successfully")
            self.model_loaded = True
            # Try to find wheel entities after model loads
            QTimer.singleShot(1000, self.find_wheel_entities)
        elif status == Qt3DRender.QSceneLoader.Error:
            print("Error loading FBX/OBJ scene")
    
    def setWheelAngle(self, angle):
        """Set the wheel rotation angle in degrees."""
        self.turn_wheels(angle)
    
    def getWheelAngle(self):
        """Get the current wheel rotation angle."""
        return self.current_wheel_angle
    
    def get_camera_settings(self):
        """Get current camera position, view center, and up vector."""
        if hasattr(self, 'camera'):
            pos = self.camera.position()
            center = self.camera.viewCenter()
            up = self.camera.upVector()
            return {
                'position': [pos.x(), pos.y(), pos.z()],
                'viewCenter': [center.x(), center.y(), center.z()],
                'upVector': [up.x(), up.y(), up.z()]
            }
        return None
    
    def set_camera_settings(self, settings):
        """Set camera position, view center, and up vector from settings."""
        if hasattr(self, 'camera') and settings:
            try:
                if 'position' in settings:
                    pos = settings['position']
                    self.camera.setPosition(QVector3D(pos[0], pos[1], pos[2]))
                
                if 'viewCenter' in settings:
                    center = settings['viewCenter']
                    self.camera.setViewCenter(QVector3D(center[0], center[1], center[2]))
                
                if 'upVector' in settings:
                    up = settings['upVector']
                    self.camera.setUpVector(QVector3D(up[0], up[1], up[2]))
                    
                print(f"Loaded camera settings: pos={settings.get('position')}, center={settings.get('viewCenter')}")
            except Exception as e:
                print(f"Error setting camera settings: {e}")
    
    def find_wheel_entities(self):
        """Find wheel entities in the loaded model by name patterns."""
        self.wheel_entities = []
        self.wheel_transforms = []
        
        if hasattr(self, 'modelEntity'):
            # Common wheel naming patterns
            wheel_patterns = [
                'wheel', 'tire', 'rim', 'front', 'rear', 'left', 'right',
                'fl', 'fr', 'rl', 'rr',  # front-left, front-right, etc.
                'wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr'
            ]
            
            # Recursively search for wheel entities
            self._search_for_wheels(self.modelEntity, wheel_patterns)
            
            print(f"Found {len(self.wheel_entities)} potential wheel entities")
            return len(self.wheel_entities) > 0
        
        return False
    
    def _search_for_wheels(self, entity, patterns):
        """Recursively search for entities with wheel-like names."""
        try:
            # Check if this entity has a name that suggests it's a wheel
            if hasattr(entity, 'objectName'):
                name = entity.objectName().lower()
                for pattern in patterns:
                    if pattern in name:
                        print(f"Found potential wheel entity: {name}")
                        
                        # Create or find transform component for this entity
                        transform = None
                        for component in entity.components():
                            if isinstance(component, Qt3DCore.QTransform):
                                transform = component
                                break
                        
                        if not transform:
                            # Create a new transform if none exists
                            transform = Qt3DCore.QTransform()
                            entity.addComponent(transform)
                        
                        self.wheel_entities.append(entity)
                        self.wheel_transforms.append(transform)
                        break
            
            # Search child entities
            for child in entity.childNodes():
                if isinstance(child, Qt3DCore.QEntity):
                    self._search_for_wheels(child, patterns)
                    
        except Exception as e:
            print(f"Error searching for wheels: {e}")
    
    def rotate_wheels(self, rotation_degrees):
        """Rotate wheels around their rotation axis by the specified degrees."""
        if not self.wheel_transforms:
            # Try to find wheels if we haven't already
            self.find_wheel_entities()
        
        for transform in self.wheel_transforms:
            try:
                # Create rotation around the wheel's local axis (usually Y or Z)
                # Most wheels rotate around Y-axis, but we can try both
                rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), rotation_degrees)
                transform.setRotation(rotation)
            except Exception as e:
                print(f"Error rotating wheel: {e}")

    def turn_wheels(self, angle_degrees):
        """Rotate all found wheel entities by the specified angle in degrees."""
        self.current_wheel_angle = angle_degrees
        
        if not self.wheel_transforms:
            # Try to find wheels if we haven't already
            self.find_wheel_entities()
        
        for transform in self.wheel_transforms:
            try:
                # Create rotation around the wheel's local axis (usually Y or Z)
                # Most wheels rotate around Y-axis, but we can try both
                rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), angle_degrees)
                transform.setRotation(rotation)
            except Exception as e:
                print(f"Error rotating wheel: {e}")
    
    def set_wheel_rotation_axis(self, axis_vector):
        """Set the rotation axis for wheels (default is Y-axis: 0,1,0)."""
        self.wheel_rotation_axis = axis_vector
    
    def animate_wheel_rotation(self, speed_rpm):
        """Animate wheel rotation based on speed (RPM)."""
        if speed_rpm == 0:
            return
            
        # Convert RPM to degrees per second (360 degrees per rotation)
        degrees_per_second = speed_rpm * 6  # 60 seconds/minute * 360 degrees/rotation / 60
        
        # For smooth animation, you might want to use a QTimer
        # This is a simple version that sets rotation based on current time
        import time
        current_time = time.time()
        total_rotation = (current_time * degrees_per_second) % 360
        
        self.rotate_wheels(total_rotation)