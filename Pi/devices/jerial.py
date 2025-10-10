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

    def send_receive(self, data: dict) -> dict:
        self.send(data)
        return self.receive()
  
    def poll(self) -> dict:
        return self.send_receive({"command": "poll"})
    
    def consume(self, button_name : list[str]) -> dict:
        return self.send_receive({"command": "consume states", "buttons": button_name})

    def get_latest(self):
        return self.latest_json

    def send(self, obj):
        while self.ser.in_waiting > 0:
            self.ser.readline()  # Clear out any old data
        line = json.dumps(obj) + '\n'
        self.ser.write(line.encode())
        self.ser.flush()  # Make sure data is sent immediately

    def receive(self) -> dict:
        while self.ser.in_waiting == 0:
            time.sleep(0.01)  # Wait for data to arrive

        data = self.ser.readline()
        if data:
            try:
                self.latest_json = json.loads(data.decode().strip())
                return self.latest_json
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"Error reading: {e}")
        return None