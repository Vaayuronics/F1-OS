from PySide6.QtGui import (
    QMatrix4x4, QVector3D
)
from PySide6.QtCore import (
    Property, QObject, Signal
)

class OrbitTransformController(QObject):
    """Controller for orbital rotation animation."""
    
    angleChanged = Signal()
    radiusChanged = Signal()
    
    def __init__(self, parent):
        """Initialize the orbit controller."""
        super().__init__(parent)
        self._target = None
        self._matrix = QMatrix4x4()
        self._radius = 1
        self._angle = 0

    def setTarget(self, t):
        """Set the target transform to control."""
        self._target = t

    def getTarget(self):
        """Get the current target transform."""
        return self._target

    def setRadius(self, radius):
        """Set the orbit radius."""
        if self._radius != radius:
            self._radius = radius
            self.updateMatrix()
            self.radiusChanged.emit()

    def getRadius(self):
        """Get the current orbit radius."""
        return self._radius

    def setAngle(self, angle):
        """Set the orbit angle."""
        if self._angle != angle:
            self._angle = angle
            self.updateMatrix()
            self.angleChanged.emit()

    def getAngle(self):
        """Get the current orbit angle."""
        return self._angle

    def updateMatrix(self):
        """Update the transformation matrix based on current angle and radius."""
        self._matrix.setToIdentity()
        self._matrix.rotate(self._angle, QVector3D(0, 1, 0))
        self._matrix.translate(self._radius, 0, 0)
        if self._target is not None:
            self._target.setMatrix(self._matrix)

    # Define properties for animation support
    angle = Property(float, getAngle, setAngle, notify=angleChanged)
    radius = Property(float, getRadius, setRadius, notify=radiusChanged)