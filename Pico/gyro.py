'''
To preserve steering angle when car turns on and off, 
have the angle be continuously saved to a file on the system. Tare the gyro to the previous angle.
'''

from machine import Pin, I2C
import time
import os
from lib.bno055 import *

# Power Modes
POWER_NORMAL = const(0x00)
POWER_LOW = const(0x01)
POWER_SUSPEND = const(0x02)
# Power Register for writing
POWER_REGISTER = const(0x3e)

# Function Modes
IMUPLUS_MODE = const(0x08)
NDOF_MODE = const(0x0c)

class Gyro:
    def __init__(self, sdaNum : int, sclNum : int):
        """Initialize the gyro with BNO055"""
        i2cGyro = I2C(0, sda=Pin(sdaNum), scl=Pin(sclNum))
        self.imu = BNO055(i2cGyro)
        
        # Load previously saved angle if exists
        self.last_angle = self._load_saved_angle()
        self.angle_offset = 0.0  # Initialize offset for taring

    def get_linear_acc(self) -> tuple:
        """Returns a list containing the linear acceleration values in 3 dimensions"""
        return self.imu.lin_acc()
    
    def get_rotational_acc(self) -> tuple:
        """Returns a list containing the rotational acceleration values in 3 dimensions."""
        return self.imu.gyro()

    def get_temperature(self) -> int:
        """Returns a float value for the temperature"""
        return self.imu.temperature()

    def get_compass(self) -> tuple:
        """Returns the yaw, pitch, and roll."""
        yaw, pitch, roll = self.imu.euler()
        # Apply the offset to the yaw (steering angle)
        adjusted_yaw = yaw - self.angle_offset
        # Normalize to 0-360
        if adjusted_yaw < 0:
            adjusted_yaw += 360
        elif adjusted_yaw >= 360:
            adjusted_yaw -= 360
        return (adjusted_yaw, pitch, roll)

    def get_compass_formatted(self) -> tuple:
        """Returns a list of strings of the compass values formatted nicely."""
        values = self.get_compass()
        return (self.format_value(values[0]), 
                self.format_value(values[1]), 
                self.format_value(values[2]))
    
    def format_value(self, val):
        """Format a value for display"""
        if val >= 10 or val <= -10:
            return f"{val:5.1f}"[:5]  # Two digits before decimal, one after for negative values
        elif val >= 0:
            return f"{val: 5.2f}"  # Extra space for single-digit positive numbers
        else:
            return f"{val:05.2f}"[:5]  # Negative numbers take one space for the sign

    def set_power_mode(self, mode) -> None:
        """Sets the BNO055's power mode
        Used to make the BNO more power efficient
        Modes: POWER_NORMAL, POWER_LOW, POWER_SUSPEND
        """
        self.imu._write(POWER_REGISTER, mode)
        
    def set_function_mode(self, mode) -> None:
        """Sets the BNO055's function mode
        Used to turn off certain parts for power efficiency
        Modes: IMUPLUS_MODE [Only gyro and accel], NDOF_MODE [Everything]
        """
        self.imu.mode(mode)
    
    def get_steering_angle(self) -> float:
        """Returns just the calibrated steering angle (yaw)"""
        return self.get_compass()[0]
    
    def save_angle(self):
        """Save the current steering angle to persistent storage"""
        try:
            angle = self.get_steering_angle()
            with open("steering_angle.txt", "w") as f:
                f.write(str(angle))
            self.last_angle = angle
        except Exception as e:
            print(f"Error saving angle: {e}")
    
    def _load_saved_angle(self):
        """Load the previously saved steering angle"""
        try:
            if self._file_exists("steering_angle.txt"):
                with open("steering_angle.txt", "r") as f:
                    return float(f.read().strip())
        except Exception as e:
            print(f"Error loading angle: {e}")
        return 0.0  # Default angle if no saved value
    
    def tare_gyro(self, angle=None):
        """
        Tare the gyro to a specific angle, or the last saved angle if None.
        This sets up an offset that will be applied to future compass readings.
        """
        target = angle if angle is not None else self.last_angle
        current_yaw = self.imu.euler()[0]  # Get raw yaw without applying offset
        
        # Calculate the offset needed to make current_yaw equal to target
        self.angle_offset = current_yaw - target
        
        # Normalize the offset
        if self.angle_offset < 0:
            self.angle_offset += 360
        elif self.angle_offset >= 360:
            self.angle_offset -= 360
            
        print(f"Gyro tared. Current raw: {current_yaw}°, Target: {target}°, Offset: {self.angle_offset}°")
        return target
    
    def _file_exists(self, filepath) -> bool:
        """Returns if a file exists or not"""
        try:
            os.stat(filepath)
            return True
        except OSError:
            return False
