import serial
import json

class JSONSerialReader:
    def __init__(self, port, baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0)
        self.latest_json = None

    def poll(self):
        data = self.ser.readline()
        try:
            self.latest_json = json.loads(data.decode().strip())
        except json.JSONDecodeError:
            pass

    def get_latest(self):
        return self.latest_json

    def send(self, obj):
        line = json.dumps(obj) + '\n'
        self.ser.write(line.encode())