import time
import keyboard  # pip install keyboard
from engine_audio_simulator import EngineAudioSimulator

sim = EngineAudioSimulator(
    base_path="sounds2",
    timestamp_file="timestamps.json"
)

throttle = 0.0
gear = 1
mph = 0.0
last_q_press = 0
last_w_press = 0
last_debug_time = 0
last_space_time = 0
last_k_time = 0

GEAR_MIN = 1
GEAR_MAX = 7
PRESS_INTERVAL = 0.2
ACC_INTERVAL = 0.1
THROTTLE_INCREMENT = 0.05
THROTTLE_DECREMENT = 0.05

print("Engine Audio Simulator Test")
print("---------------------------")
print("Space: Increase Throttle")
print("K: Decrease Throttle")
print("Q: Upshift")
print("W: Downshift")
print("Esc: Exit")

try:
    while True:
        if keyboard.is_pressed("esc"):
            break
            
        current_time = time.time()

        # Handle throttle - make it more continuous for smoother audio transitions
        if keyboard.is_pressed("space") and current_time - last_space_time >= ACC_INTERVAL:
            throttle = min(throttle + THROTTLE_INCREMENT, 1.0)
            last_space_time = current_time
            print(f"Throttle increased: {throttle:.2f}")
            
        if keyboard.is_pressed("k") and current_time - last_k_time >= ACC_INTERVAL:
            throttle = max(throttle - THROTTLE_DECREMENT, 0.0)
            last_k_time = current_time
            print(f"Throttle decreased: {throttle:.2f}")

        # Handle gear shifts with proper RPM changes
        prev_gear = gear
        
        # Handle gear up (Q key)
        if keyboard.is_pressed("q") and current_time - last_q_press >= PRESS_INTERVAL:
            gear = min(GEAR_MAX, gear + 1)
            last_q_press = current_time
            print(f"Upshifted to gear {gear}")

        # Handle gear down (W key)
        if keyboard.is_pressed("w") and current_time - last_w_press >= PRESS_INTERVAL:
            gear = max(GEAR_MIN, gear - 1)
            last_w_press = current_time
            print(f"Downshifted to gear {gear}")

        # Simulate speed with better physics
        if throttle > 0.05:
            # More realistic acceleration based on gear and throttle
            # Higher gears give less acceleration but more top speed
            accel_factor = 0.2 + (gear / 14.0)  # More gentle acceleration
            drag_factor = 0.005 * (mph ** 2)  # Aerodynamic drag increases with speed squared
            mph += (throttle * accel_factor) - drag_factor
        else:
            # Natural deceleration with engine braking
            decel_rate = 0.2 + (0.01 * mph)  # Deceleration increases with speed
            mph = max(0.0, mph - decel_rate)
        
        # Pass shifting flag to indicate when we're actively changing gears
        shifting = (gear != prev_gear)
        sim.update(throttle, gear, mph, shifting)
        
        # Print debug info including actual RPM
        if current_time - last_debug_time >= 2.0:
            print(f"Status: Throttle: {throttle:.2f}, Gear: {gear}, Speed: {mph:.1f} mph, RPM: {sim.rpm:.0f}, State: {sim.state}")
            last_debug_time = current_time
            
        time.sleep(0.01)  # 100Hz update rate
        
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    # Clean up
    del sim
