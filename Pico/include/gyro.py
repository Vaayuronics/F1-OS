from machine import Pin, I2C
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
        # Apply the offsets
        adjusted_yaw = yaw - self.offsets[0]
        adjusted_pitch = pitch - self.offsets[1]
        adjusted_roll = roll - self.offsets[2]
        # Normalize to 0-360
        if adjusted_yaw < 0:
            adjusted_yaw += 360
        elif adjusted_yaw >= 360:
            adjusted_yaw -= 360

        if adjusted_pitch < 0:
            adjusted_pitch += 360
        elif adjusted_pitch >= 360:
            adjusted_pitch -= 360

        if adjusted_roll < 0:
            adjusted_roll += 360
        elif adjusted_roll >= 360:
            adjusted_roll -= 360

        self.angles = (adjusted_yaw, adjusted_pitch, adjusted_roll)
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
        
    def tare_gyro(self, angles : tuple) -> None:
        """
        Tare the gyro to given yaw, pitch, and roll as a tuple.\n
        This sets up an offset that will be applied to future compass readings."""
        current_yaw, current_pitch, current_roll = self.imu.euler()
        
        # Calculate the offset needed to make current_yaw equal to target
        yaw_offset = current_yaw - angles[0]
        pitch_offset = current_pitch - angles[1]
        roll_offset = current_roll - angles[2]
        
        # Normalize the offset
        if yaw_offset < 0:
            yaw_offset += 360
        elif yaw_offset >= 360:
            yaw_offset -= 360

        if pitch_offset < 0:
            pitch_offset += 360
        elif pitch_offset >= 360:
            pitch_offset -= 360

        if roll_offset < 0:
            roll_offset += 360
        elif roll_offset >= 360:
            roll_offset -= 360

        self.offsets = (yaw_offset, pitch_offset, roll_offset)
    
    def poll(self) -> None:
        '''Wrapper for the update functions.\n
        This function should be included in the main while loop.\n
        Use get functions to access the values during compute.'''
        self.update_angles()
        self.update_linear_acc()
        self.update_rotational_acc()
        self.update_temperature()

    
