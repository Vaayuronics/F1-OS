import time
import keyboard
from engineSimp import SimpleEngineAudio  # Adjust import if needed

def main():
    engine = SimpleEngineAudio()
    throttle = 0.0
    gear = 1
    mph = 0.0

    last_upshift_time = 0
    last_downshift_time = 0
    last_loop_time = time.time()

    print("Hold SPACE to throttle. Press Q to upshift, W to downshift. CTRL+C to exit.")

    try:
        while True:
            current_time = time.time()

            # Check throttle
            if keyboard.is_pressed('space'):
                throttle = min(1.0, throttle + 0.01)
            else:
                throttle = max(0.0, throttle - 0.05)

            # Debounced upshift
            if keyboard.is_pressed('q') and current_time - last_upshift_time > 0.5:
                gear = min(7, gear + 1)
                last_upshift_time = current_time
                print(f"Upshift to gear {gear}")

            # Debounced downshift
            if keyboard.is_pressed('w') and current_time - last_downshift_time > 0.5:
                gear = max(1, gear - 1)
                last_downshift_time = current_time
                print(f"Downshift to gear {gear}")

            # Simulate MPH from throttle for demo
            mph = throttle * 60  # You can replace with actual speed input later

            # Call engine update
            engine.update(throttle, gear, mph)

            # Run loop ~60 FPS
            time.sleep(0.016)  # 16 ms

    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
