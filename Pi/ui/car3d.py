from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel
)
from PySide6.QtGui import (
    QColor, QQuaternion, QVector3D
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QSize
)
from PySide6.Qt3DCore import Qt3DCore
from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender
from car2d import CarWidget
from orbit import OrbitTransformController

class Car3DWidget(QWidget):
    """Widget that displays a 3D model of an F1 car with animations."""
    
    def __init__(self, stl_path=None, parent=None, is3d : bool = True):
        """Initialize the 3D car widget."""
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.stl_path = stl_path
        self.animation_running = False
        self.is3d = is3d
        
        # Set up layout for the 3D view
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if is3d:
            # Create a Qt3D window
            self.view = Qt3DExtras.Qt3DWindow()
            self.container = QWidget.createWindowContainer(self.view)
            self.container.setMinimumSize(QSize(400, 400))
            layout.addWidget(self.container)
            
            # Set up the 3D scene
            self.setup_scene()
            
            # Set up animation
            self.setup_animations()
        else:
            # Use the 2D car widget as fallback
            self.car_2d = CarWidget()
            layout.addWidget(self.car_2d)
    
    def setup_scene(self):
        """Set up the 3D scene with simple test objects."""
        # Create root entity
        self.rootEntity = Qt3DCore.QEntity()
        
        # Set a dark background color for the view
        self.view.defaultFrameGraph().setClearColor(QColor(30, 30, 30))
        
        # Create a material for all objects
        self.material = Qt3DExtras.QPhongMaterial(self.rootEntity)
        self.material.setDiffuse(QColor(255, 50, 50))  # Bright red color
        self.material.setSpecular(QColor(255, 255, 255))
        self.material.setShininess(150)
        
        # Create a torus
        self.torusEntity = Qt3DCore.QEntity(self.rootEntity)
        self.torusMesh = Qt3DExtras.QTorusMesh()
        self.torusMesh.setRadius(5)
        self.torusMesh.setMinorRadius(1)
        self.torusMesh.setRings(100)
        self.torusMesh.setSlices(20)
        
        self.torusTransform = Qt3DCore.QTransform()
        self.torusTransform.setScale3D(QVector3D(1.5, 1, 0.5))
        self.torusTransform.setRotation(QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 45))
        
        self.torusEntity.addComponent(self.torusMesh)
        self.torusEntity.addComponent(self.torusTransform)
        self.torusEntity.addComponent(self.material)
        
        # Create a sphere
        self.sphereEntity = Qt3DCore.QEntity(self.rootEntity)
        self.sphereMesh = Qt3DExtras.QSphereMesh()
        self.sphereMesh.setRadius(3)
        
        self.sphereTransform = Qt3DCore.QTransform()
        self.controller = OrbitTransformController(self.sphereTransform)
        self.controller.setTarget(self.sphereTransform)
        self.controller.setRadius(15)
        
        self.sphereEntity.addComponent(self.sphereMesh)
        self.sphereEntity.addComponent(self.sphereTransform)
        self.sphereEntity.addComponent(self.material)
        
        # Add a light
        self.light_entity = Qt3DCore.QEntity(self.rootEntity)
        self.light = Qt3DRender.QPointLight(self.light_entity)
        self.light.setColor(QColor(255, 255, 255))
        self.light.setIntensity(1.5)
        light_transform = Qt3DCore.QTransform(self.light_entity)
        light_transform.setTranslation(QVector3D(0, 0, 40))
        self.light_entity.addComponent(self.light)
        self.light_entity.addComponent(light_transform)
        
        # Set camera
        self.camera = self.view.camera()
        self.camera.setPosition(QVector3D(0, 0, 40))
        self.camera.setViewCenter(QVector3D(0, 0, 0))
        
        # Set up camera controller
        self.camController = Qt3DExtras.QOrbitCameraController(self.rootEntity)
        self.camController.setLinearSpeed(50)
        self.camController.setLookSpeed(180)
        self.camController.setCamera(self.camera)
        
        # Set root entity
        self.view.setRootEntity(self.rootEntity)
    
    def setup_animations(self):
        """Set up animation for the sphere."""
        # Sphere rotation animation
        self.sphereRotateTransformAnimation = QPropertyAnimation(self.sphereTransform)
        self.sphereRotateTransformAnimation.setTargetObject(self.controller)
        self.sphereRotateTransformAnimation.setPropertyName(b"angle")
        self.sphereRotateTransformAnimation.setStartValue(0)
        self.sphereRotateTransformAnimation.setEndValue(360)
        self.sphereRotateTransformAnimation.setDuration(10000)
        self.sphereRotateTransformAnimation.setLoopCount(-1)
        self.sphereRotateTransformAnimation.start()
    
    def start_animation(self):
        """Start the animation if not already running."""
        if not self.animation_running and hasattr(self, 'sphereRotateTransformAnimation'):
            self.sphereRotateTransformAnimation.start()
            self.animation_running = True
    
    def stop_animation(self):
        """Stop the animation if it's running."""
        if self.animation_running and hasattr(self, 'sphereRotateTransformAnimation'):
            self.sphereRotateTransformAnimation.pause()
            self.animation_running = False
    
    def setWheelAngle(self, angle):
        """Set the wheel angle (for API compatibility with 2D widget)."""
        if not self.is3d and hasattr(self, 'car_2d'):
            self.car_2d.setWheelAngle(angle)
    
    def getWheelAngle(self):
        """Get the wheel angle (for API compatibility with 2D widget)."""
        if not self.is3d and hasattr(self, 'car_2d'):
            return self.car_2d.getWheelAngle()
        return 0