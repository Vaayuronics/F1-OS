'''
To preserve steering angle when car turns on and off, 
have the angle be continuously saved to a file on the system. Tare the gyro to the previous angle.
'''

from machine import Pin, I2C
import time
import os
from include.bno055 import *

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
        self.angle_offset = self._tare_gyro(self._load_saved_angle())
        self.lin_acc = (0,0,0)
        self.rot_acc = (0,0,0)
        self.temp = 0
        self.angles = (0,0,0)

    def update_linear_acc(self) -> tuple:
        """Updates the linear acceleration.\n
        Wrapped by the poll function.\n
        Returns a list containing the linear acceleration values in 3 dimensions"""
        self.linear_acc = self.imu.lin_acc()
        return self.linear_acc
    
    def get_linear_acc(self) -> tuple:
        """Returns a list containing the linear acceleration values in 3 dimensions."""
        return self.linear_acc
    
    def update_rotational_acc(self) -> tuple:
        """Updates the rotational acceleration.\n
        Wrapped by the poll function.\n
        Returns a list containing the rotational acceleration values in 3 dimensions."""
        self.rot_acc = self.imu.gyro()
        return self.rot_acc
    
    def get_rotational_acc(self) -> tuple:
        """Returns a list containing the rotational acceleration values in 3 dimensions."""
        return self.rot_acc
    
    def update_temperature(self) -> int:
        """Updates the temperature.\n
        Wrapped by the poll function.\n
        Returns a int value for the temperature"""
        self.temp = self.imu.temperature()
        return self.temp

    def get_temperature(self) -> int:
        """Returns a int value for the temperature"""
        return self.temp

    def update_angles(self) -> tuple:
        """Updates the compass angles.\n
        Wrapped by the poll function.\n
        Returns the yaw, pitch, and roll."""
        yaw, pitch, roll = self.imu.euler()
        # Apply the offset to the yaw (steering angle)
        adjusted_yaw = yaw - self.angle_offset
        # Normalize to 0-360
        if adjusted_yaw < 0:
            adjusted_yaw += 360
        elif adjusted_yaw >= 360:
            adjusted_yaw -= 360

        self.angles = (adjusted_yaw, pitch, roll)
        return self.angles
    
    def get_angles(self) -> tuple:
        """Returns the yaw, pitch, and roll as a tuple."""
        return self.angles

    def get_compass_formatted(self) -> tuple:
        """Returns a list of strings of the compass values formatted nicely."""
        values = self.get_compass()
        return (self.format_value(values[0]), 
                self.format_value(values[1]), 
                self.format_value(values[2]))
    
    def format_value(self, val : int) -> str:
        """Format a value for display"""
        if val >= 10 or val <= -10:
            return f"{val:5.1f}"[:5]  # Two digits before decimal, one after for negative values
        elif val >= 0:
            return f"{val: 5.2f}"  # Extra space for single-digit positive numbers
        else:
            return f"{val:05.2f}"[:5]  # Negative numbers take one space for the sign

    def set_power_mode(self, mode) -> None:
        """Sets the BNO055's power mode.\n
        Used to make the BNO more power efficient.\n
        Modes: POWER_NORMAL, POWER_LOW, POWER_SUSPEND.
        """
        self.imu._write(POWER_REGISTER, mode)
        
    def set_function_mode(self, mode) -> None:
        """Sets the BNO055's function mode.\n
        Used to turn off certain parts for power efficiency.\n
        Modes: IMUPLUS_MODE [Only gyro and accel], NDOF_MODE [Everything].
        """
        self.imu.mode(mode)
    
    def get_steer(self) -> float:
        """Returns just the calibrated steering angle (yaw)"""
        return self.get_angles()[0]
    
    def _save_angle(self) -> None:
        """Save the current steering angle to persistent storage"""
        try:
            angle = self.get_steer()
            with open("steering_angle.txt", "w") as f:
                f.write(str(angle))
        except Exception as e:
            print(f"Error saving angle: {e}")
    
    def _load_saved_angle(self) -> int:
        """Load the previously saved steering angle"""
        try:
            if self._file_exists("steering_angle.txt"):
                with open("steering_angle.txt", "r") as f:
                    return float(f.read().strip())
        except Exception as e:
            print(f"Error loading angle: {e}")
        return 0  # Default angle if no saved value
    
    def _tare_gyro(self, angle : int) -> int:
        """
        Tare the gyro to a specific angle.\n
        This sets up an offset that will be applied to future compass readings.\n
        Returns the offset.
        """
        current_yaw = self.imu.euler()[0]  # Get raw yaw without applying offset
        
        # Calculate the offset needed to make current_yaw equal to target
        angle_offset = current_yaw - angle
        
        # Normalize the offset
        if angle_offset < 0:
            angle_offset += 360
        elif angle_offset >= 360:
            angle_offset -= 360
            
        print(f"Gyro tared. Current raw: {current_yaw}°, Target: {angle}°, Offset: {angle_offset}°")
        return angle_offset
    
    def poll(self) -> None:
        '''Wrapper for gryo update functions'''
        self.update_angles()
        self.update_linear_acc()
        self.update_rotational_acc()
        self.update_temperature()
        self._save_angle()

    def _file_exists(self, filepath) -> bool:
        """Returns if a file exists or not"""
        try:
            os.stat(filepath)
            return True
        except OSError:
            return False
