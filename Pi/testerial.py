import serial
import json
import time
import threading

class JSONSerialReader:
    def __init__(self, port, baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0.1)
        self.latest_json = None
        self.port_name = port
        self.lock = threading.Lock()
        self.poll_count = 0
        # Clear any pending data
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.1)
        print(f"[{self.port_name}] Initialized")
        
    def poll(self) -> dict:
        with self.lock:
            self.poll_count += 1
            poll_id = self.poll_count
            poll_start = time.time()
            
            # Clear old data
            clear_start = time.time()
            cleared_bytes = 0
            while self.ser.in_waiting > 0:
                self.ser.readline()
                cleared_bytes += 1
            clear_time = time.time() - clear_start
            
            if cleared_bytes > 0:
                print(f"[{self.port_name}] Poll #{poll_id}: Cleared {cleared_bytes} old lines in {clear_time:.3f}s")

            # Send poll command
            send_start = time.time()
            self.send_unlocked({"command": "poll"})
            send_time = time.time() - send_start

            # Wait for response
            wait_start = time.time()
            timeout = 3.0
            waited_iterations = 0
            
            while self.ser.in_waiting == 0:
                waited_iterations += 1
                elapsed = time.time() - wait_start
                
                # Print waiting status every second
                if int(elapsed) > int(elapsed - 0.01):
                    print(f"[{self.port_name}] Poll #{poll_id}: Still waiting... {elapsed:.1f}s (checked {waited_iterations} times)")
                
                if elapsed > timeout:
                    print(f"[{self.port_name}] Poll #{poll_id}: TIMEOUT after {elapsed:.3f}s")
                    print(f"  Cleared: {cleared_bytes} lines in {clear_time:.3f}s")
                    print(f"  Send: {send_time:.3f}s")
                    print(f"  Waited: {waited_iterations} iterations")
                    return None
                time.sleep(0.01)
            
            wait_time = time.time() - wait_start

            # Read response
            read_start = time.time()
            data = self.ser.readline()
            read_time = time.time() - read_start
            
            total_time = time.time() - poll_start
            
            # Always log timing for debugging
            print(f"[{self.port_name}] Poll #{poll_id}: {total_time:.3f}s total")
            print(f"  Clear: {clear_time:.3f}s, Send: {send_time:.3f}s, Wait: {wait_time:.3f}s ({waited_iterations} iter), Read: {read_time:.3f}s")
            
            if data:
                try:
                    decoded = data.decode().strip()
                    print(f"  Data length: {len(decoded)} chars")
                    self.latest_json = json.loads(decoded)
                    return self.latest_json
                except json.JSONDecodeError as e:
                    print(f"[{self.port_name}] JSON error: {e}")
                    print(f"  Raw data (first 200 chars): {data[:200]}")
                except Exception as e:
                    print(f"[{self.port_name}] Error: {e}")
            else:
                print(f"[{self.port_name}] Poll #{poll_id}: No data received")
            
            return None

    def get_latest(self):
        return self.latest_json

    def send(self, obj):
        with self.lock:
            self.send_unlocked(obj)
    
    def send_unlocked(self, obj):
        """Internal send without lock (when already locked)"""
        line = json.dumps(obj) + '\n'
        bytes_written = self.ser.write(line.encode())
        self.ser.flush()
        # Verify write
        if bytes_written != len(line):
            print(f"[{self.port_name}] WARNING: Only wrote {bytes_written}/{len(line)} bytes")