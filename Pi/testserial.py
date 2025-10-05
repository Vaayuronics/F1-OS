from testerial import JSONSerialReader
import time
import threading

print("Testing both devices separately and together...")

def test_device(name, port):
    device = JSONSerialReader(port)
    times = []
    for i in range(10):
        start = time.time()
        result = device.poll()
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"{name} #{i+1}: {elapsed:.3f}s - {result}")
        time.sleep(0.1)
    print(f"{name} average: {sum(times)/len(times):.3f}s")
    device.ser.close()

# Test separately
print("\n=== Testing Pico alone ===")
test_device("Pico", "/dev/pico")

print("\n=== Testing Arduino alone ===")
test_device("Arduino", "/dev/arduino")

# Test together in threads
print("\n=== Testing both in threads (like your code) ===")
pico = JSONSerialReader("/dev/pico")
arduino = JSONSerialReader("/dev/arduino")

def poll_loop(device, name):
    for i in range(5):
        start = time.time()
        result = device.poll()
        elapsed = time.time() - start
        print(f"{name} #{i+1}: {elapsed:.3f}s")
        time.sleep(0.01)

pico_thread = threading.Thread(target=poll_loop, args=(pico, "Pico"))
arduino_thread = threading.Thread(target=poll_loop, args=(arduino, "Arduino"))

pico_thread.start()
arduino_thread.start()

pico_thread.join()
arduino_thread.join()

pico.ser.close()
arduino.ser.close()