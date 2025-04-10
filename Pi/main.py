#from pedal import Pedal
import transmission
import serial

ser = serial.Serial('/dev/ttyACM0', 115200, timeout = 1)

def send(message : dict):
    message = "Hello from Raspberry Pi 5!"
    ser.write(message.encode('utf-8'))
    
    # Read response from Pico
    if ser.in_waiting > 0:
        response = ser.readline().decode('utf-8').strip()
        print(f"Received: {response}")

if __name__ == "__main__":
    print("Starting System")