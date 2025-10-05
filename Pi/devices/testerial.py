import serial
import json
import time
import threading

class JSONSerialReader:
    def __init__(self, port, baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0.5)  # Reasonable timeout
        self.latest_json = None
        self.port_name = port
        self.lock = threading.Lock()
        # Clear any pending data
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.1)
        
    def poll(self) -> dict:
        with self.lock:
            # Clear old data quickly
            if self.ser.in_waiting > 0:
                self.ser.reset_input_buffer()

            # Send poll command
            line = json.dumps({"command": "poll"}) + '\n'
            self.ser.write(line.encode())
            self.ser.flush()

            # Wait for data to arrive (should be immediate)
            timeout = 2.0
            start_time = time.time()
            while self.ser.in_waiting == 0:
                if time.time() - start_time > timeout:
                    print(f"[{self.port_name}] No data arrived")
                    return None
                time.sleep(0.01)

            # Give a moment for full message to arrive
            time.sleep(0.05)
            
            # Read all available bytes at once
            bytes_available = self.ser.in_waiting
            if bytes_available > 0:
                try:
                    data = self.ser.read(bytes_available)
                    decoded = data.decode('utf-8').strip()
                    
                    # Handle multiple lines - take the last complete one
                    if '\n' in decoded:
                        lines = decoded.split('\n')
                        for line in reversed(lines):
                            if line.strip():
                                decoded = line.strip()
                                break
                    
                    self.latest_json = json.loads(decoded)
                    return self.latest_json
                    
                except json.JSONDecodeError as e:
                    print(f"[{self.port_name}] JSON error: {e}")
                    print(f"  Data (first 200 chars): {decoded[:200]}")
                except UnicodeDecodeError as e:
                    print(f"[{self.port_name}] Unicode error: {e}")
                except Exception as e:
                    print(f"[{self.port_name}] Error: {e}")
            
            return None

    def get_latest(self):
        return self.latest_json

    def send(self, obj):
        with self.lock:
            line = json.dumps(obj) + '\n'
            self.ser.write(line.encode())
            self.ser.flush()