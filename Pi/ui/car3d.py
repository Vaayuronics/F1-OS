from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QFrame, QPushButton, QHBoxLayout
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
        self.setMinimumSize(400, 400)
        self.model_path = model_path
        self.model_loaded = False
        self.model_scale = 1.0
        self.focus_button = None
        self.reset_button = None
        
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
        
        # Add button controls in a horizontal layout
        button_layout = QHBoxLayout()
        
        # Focus button 
        self.focus_button = QPushButton("Focus Camera")
        self.focus_button.setStyleSheet("background-color: #444; color: white; padding: 5px;")
        self.focus_button.clicked.connect(self.focus_on_model)
        button_layout.addWidget(self.focus_button)
        
        # Reset view button
        self.reset_button = QPushButton("Reset View")
        self.reset_button.setStyleSheet("background-color: #444; color: white; padding: 5px;")
        self.reset_button.clicked.connect(self.reset_camera)
        button_layout.addWidget(self.reset_button)
        
        container_layout.addLayout(button_layout)
        
        # Create a Qt3D window
        self.view = Qt3DExtras.Qt3DWindow()
        self.view.setFlags(Qt.Widget)  # Make sure it behaves like a regular widget
        
        self.container = QWidget.createWindowContainer(self.view, container_frame)
        self.container.setFocusPolicy(Qt.StrongFocus)  # Allow keyboard focus
        self.container.setMinimumSize(QSize(300, 300))
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        container_layout.addWidget(self.container)
        layout.addWidget(container_frame)
        
        # Log the model path
        if model_path:
            print(f"Setting up 3D scene with model: {model_path}")
            print(f"File exists: {os.path.exists(model_path)}")
        
        # Set up the 3D scene
        self.setup_scene()
        
        # Schedule auto-focus after model loads with a slight delay
        QTimer.singleShot(1000, self.focus_on_model)
    
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
            self.focus_on_model()
        elif status == Qt3DRender.QMesh.Error:
            print("Error loading STL mesh")
    
    def handle_scene_status_changed(self, status):
        """Handle scene loading status changes."""
        if status == Qt3DRender.QSceneLoader.Ready:
            print("FBX/OBJ scene loaded successfully")
            self.model_loaded = True
            QTimer.singleShot(500, self.focus_on_model)  # Additional delay for complex models
        elif status == Qt3DRender.QSceneLoader.Error:
            print("Error loading FBX/OBJ scene")
    
    def focus_on_model(self):
        """Focus the camera on the model, adjusting scale and position."""
        if self.model_path:
            print(f"Focusing camera on model: {self.model_path}")
            
            # Get file extension
            _, ext = os.path.splitext(self.model_path)
            ext = ext.lower()
            
            # Handle different model types
            if ext == '.stl':
                # STL files are often in mm, scale and position camera accordingly
                self.camera.setPosition(QVector3D(0, 0, 30))
                self.camera.setViewCenter(QVector3D(0, 0, 0))
                self.camera.setUpVector(QVector3D(0, 1, 0))
                
            elif ext in ['.fbx', '.obj']:
                # FBX/OBJ models often need a different camera setup
                # Position the camera to view the model from a good angle
                self.camera.setPosition(QVector3D(10, 10, 30))
                self.camera.setViewCenter(QVector3D(0, 0, 0))
                self.camera.setUpVector(QVector3D(0, 1, 0))
                
                # Try different scales for FBX models
                current_scale = self.modelTransform.scale()
                # If the model is too small, try scaling it up
                if current_scale < 0.1 or current_scale > 100:
                    self.modelTransform.setScale(1.0)
                    print(f"Reset scale to 1.0 for FBX model")
        else:
            # Default view for the fallback model
            self.camera.setPosition(QVector3D(15, 15, 15))
            self.camera.setViewCenter(QVector3D(0, 0, 0))
            self.camera.setUpVector(QVector3D(0, 1, 0))
    
    def reset_camera(self):
        """Reset the camera to a default position to find the model."""
        print("Resetting camera view")
        
        # Move camera far enough to see the entire scene
        self.camera.setPosition(QVector3D(0, 0, 50))
        self.camera.setViewCenter(QVector3D(0, 0, 0))
        self.camera.setUpVector(QVector3D(0, 1, 0))
        
        # Reset model scale if needed
        self.modelTransform.setScale(1.0)
        print(f"Reset model scale to 1.0")

    def setWheelAngle(self, angle):
        """Placeholder for steering wheel angle."""
        pass
    
    def getWheelAngle(self):
        """Placeholder for getting wheel angle."""
        return 0