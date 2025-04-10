from machine import Pin, SoftI2C
import lib.OLED as OLED
from ezFont import ezFBfont
import time

class LCD:
    # Display constants
    OLED_WIDTH = 128  # Pixel Width of the OLED
    OLED_HEIGHT = 32  # Pixel Height of the OLED
    OLED_STEP_HEIGHT = 8  # How much space each character takes height wise
    OLED_STEP_WIDTH = 8  # How much space each character takes width wise
    
    def __init__(self, font, sda_pin : int, scl_pin : int):
        """
        Initialize the LCD display with the specified font.
        
        Args:
            font: Font module to use for display
            sda_pin (int): SDA pin number, default is 2
            scl_pin (int): SCL pin number, default is 3
        """
        try:
            i2c = SoftI2C(sda=Pin(sda_pin), scl=Pin(scl_pin))
            self.oled = ezFBfont(OLED.SSD1306_I2C(self.OLED_WIDTH, self.OLED_HEIGHT, i2c, addr=0x3c), font)
            self.text_lines = ["", "", "", ""]  # Store the 4 most recent lines
            self.initialized = True
        except Exception as e:
            print(f"LCD initialization failed: {e}")
            self.oled = None
            self.initialized = False
    
    def is_initialized(self):
        """Check if LCD was properly initialized"""
        return self.initialized
    
    def displayText(self, text, x, y) -> None:
        """
        Displays text on screen at the specified x and y positions.
        
        Args:
            text (str): The text to display
            x (int): X position
            y (int): Y position
        """
        if self.oled is None:
            raise ValueError("OLED failed to initialize")
        if not isinstance(text, str):
            raise TypeError("Text must be a string")
        
        # Update the text_lines array based on y position
        line_index = y // self.OLED_STEP_HEIGHT
        if 0 <= line_index < len(self.text_lines):
            # If x is 0, replace the entire line
            if x == 0:
                self.text_lines[line_index] = text
            else:
                # Otherwise, update the specific part of the line
                current_line = self.text_lines[line_index]
                # Pad the current line if needed
                if len(current_line) < x:
                    current_line = current_line.ljust(x)
                
                # Replace characters at position x
                new_line = current_line[:x] + text
                # If the new text doesn't extend to the end of the existing line
                if x + len(text) < len(current_line):
                    new_line += current_line[x + len(text):]
                
                self.text_lines[line_index] = new_line
        
        self.oled.write(text, x, y)
        self.oled.show()
    
    def clearScreen(self) -> None:
        """Clear the Screen by setting everything to spaces"""
        if self.oled is None:
            raise ValueError("OLED failed to initialize")
        self.oled.fill(0)
        self.oled.show()
        self.text_lines = ["", "", "", ""]  # Reset stored lines
    
    def displayScroll(self, text) -> None:
        """
        Displays text at the bottom of the screen and scrolls everything up.
        
        Args:
            text (str): The text to display at the bottom
        """
        if self.oled is None:
            raise ValueError("OLED failed to initialize")
        if not isinstance(text, str):
            raise TypeError("Text must be a string")
        
        # Scroll stored text lines up
        self.text_lines.pop(0)  # Remove the oldest line
        self.text_lines.append(text)  # Add the new line
        
        # Clear the screen
        self.oled.fill(0)
        
        # Display all lines
        for i, line in enumerate(self.text_lines):
            y_pos = i * self.OLED_STEP_HEIGHT
            self.oled.write(line, 0, y_pos)
        
        self.oled.show()
    
    def display_centered(self, text, y=None):
        """
        Display text centered on the screen
        
        Args:
            text (str): Text to display
            y (int): Y position (if None, centers vertically too)
        """
        if self.oled is None:
            raise ValueError("OLED failed to initialize")
            
        if not isinstance(text, str):
            raise TypeError("Text must be a string")
            
        # Calculate center position
        text_width = len(text) * self.OLED_STEP_WIDTH
        x = max(0, (self.OLED_WIDTH - text_width) // 2)
        
        if y is None:
            y = (self.OLED_HEIGHT - self.OLED_STEP_HEIGHT) // 2
            
        self.displayText(text, x, y)

    def wait(self, delay_ms):
        """
        Wait for specified milliseconds
        
        Args:
            delay_ms (int): Delay in milliseconds
        """
        time.sleep(delay_ms / 1000.0)
