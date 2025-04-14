import serial
import json
import time

class JSONSerialReader:
    def __init__(self, port, baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0.1)  # Added small timeout
        self.latest_json = None
        # Clear any pending data
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.1)  # Allow time for buffer clearing
        
    def poll(self):
        if self.ser.in_waiting:  # Check if data is available
            data = self.ser.readline()
            if data:
                try:
                    self.latest_json = json.loads(data.decode().strip())
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"Error reading: {e}")

    def get_latest(self):
        return self.latest_json

    def send(self, obj):
        line = json.dumps(obj) + '\n'
        self.ser.write(line.encode())
        self.ser.flush()  # Make sure data is sent immediately