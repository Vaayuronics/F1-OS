from devices.jerial import JSONSerialReader
import time

print("Testing Pico timing...")
pico = JSONSerialReader("/dev/pico")

for i in range(5):
    print(f"\n--- Test {i+1} ---")
    start = time.time()
    result = pico.poll(max_wait=3.0)
    elapsed = time.time() - start
    
    print(f"Total time: {elapsed:.3f}s")
    print(f"Result: {result}")
    
    time.sleep(0.5)

pico.ser.close()