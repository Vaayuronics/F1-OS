import os
import time
import json
import sounddevice as sd
import numpy as np
import soundfile as sf
from scipy.signal import resample

class EngineAudioSimulator:
    def __init__(self, base_path="sounds2", timestamp_file="timestamps.json"):
        self.base_path = base_path
        self.gear = 1
        self.power = 0.0
        self.gear_speeds = [1.5, 1.4, 1.3, 1.15, 1.0, 0.9, 0.8]  # Playback speed per gear
        self.audio_data = {}
        self.timestamps = self._load_timestamps(os.path.join(base_path, timestamp_file))
        self.current_stream = None
        self.prev_mph = 0.0
        self.rpm = 4000
        self.target_rpm = 4000
        self.fs = 44100  # Target sample rate
        self.state = "idle"  # idle, accel, decel, max_rpm
        self.transition_smooth = 0.05  # Lower value for more gradual transitions
        
        # Playback position tracking
        self.accel_position = 0
        self.decel_position = 0
        self.idle_position = 0
        self.max_rpm_position = 0
        
        # RPM transition tracking
        self.last_rpm_change_time = time.time()
        self.rpm_stable = False
        self.rpm_stable_position = 0
        self.last_accel_pos = 0
        
        # State transition tracking
        self.last_state_change = time.time()
        self.crossfade_duration = 0.05  # seconds
        
        # Add a flag to track if we reached max_rpm naturally
        self.reached_max_rpm_naturally = False
        # Track the speed factor for max RPM playback
        self.max_rpm_speed_factor = 1.0
        # Add gear shifting tracking
        self.shifting = False
        self.shift_start_time = 0
        self.shift_duration = 0.1  # seconds for shift to complete
        self.last_shift_rpm = 4000  # RPM before last shift
        
        self._load_all_audio()
        self._start_continuous_stream()

    def _load_all_audio(self):
        files = ["accel.wav", "decel.wav", "idle.wav", "max_rpm.wav"]
        for f in files:
            path = os.path.join(self.base_path, f)
            audio, sr = sf.read(path)
            if sr != self.fs:
                num_samples = int(len(audio) * self.fs / sr)
                audio = resample(audio, num_samples)
            self.audio_data[f] = audio

    def _load_timestamps(self, path):
        with open(path, "r") as f:
            data = json.load(f)

        return {str(mk) : {int(k): float(v) for k, v in data.get(mk).items()} for mk, mv in data.items()}

    def _get_rpm_timestamp(self, acceltype, rpm):
        rpm = int(rpm)
        # Use interpolation between timestamp points for smoother transitions
        available_rpms = sorted(list(map(int, self.timestamps.get(acceltype).keys())))
        
        # If exact match, return it
        if rpm in available_rpms:
            return self.timestamps.get(acceltype).get(rpm, 0.0)
            
        # Find surrounding RPM values for interpolation
        lower_rpm = max([r for r in available_rpms if r <= rpm], default=available_rrps[0])
        higher_rpm = min([r for r in available_rpms if r >= rpm], default=available_rpms[-1])
        
        if lower_rpm == higher_rpm:
            return self.timestamps.get(acceltype).get(lower_rpm, 0.0)
            
        # Linear interpolation between timestamp points
        lower_ts = self.timestamps.get(acceltype).get(lower_rpm, 0.0)
        higher_ts = self.timestamps.get(acceltype).get(higher_rpm, 0.0)
        
        # Calculate interpolated timestamp
        fraction = (rpm - lower_rpm) / (higher_rpm - lower_rpm)
        return lower_ts + fraction * (higher_ts - lower_ts)

    def _get_rpm_from_position(self, position):
        """Convert audio position to RPM value using timestamp data"""
        if self.state == "accel":
            # Find the closest timestamp position
            position_seconds = position / self.fs
            timestamps = sorted([(int(k), float(v)) for k, v in self.timestamps["accel"].items()], 
                                key=lambda x: x[1])
            
            # If we're before the first timestamp, return the lowest RPM
            if position_seconds <= timestamps[0][1]:
                return timestamps[0][0]
            
            # If we're after the last timestamp, return the highest RPM
            if position_seconds >= timestamps[-1][1]:
                return timestamps[-1][0]
            
            # Find the two surrounding timestamps
            for i in range(len(timestamps) - 1):
                if timestamps[i][1] <= position_seconds < timestamps[i+1][1]:
                    # Linear interpolation between RPM values
                    low_rpm, low_time = timestamps[i]
                    high_rpm, high_time = timestamps[i+1]
                    
                    # Calculate interpolated RPM
                    fraction = (position_seconds - low_time) / (high_time - low_time)
                    return low_rpm + int(fraction * (high_rpm - low_rpm))
            
            # Fallback
            return int(self.rpm)
        
        elif self.state == "decel":
            # Similar lookup for decel timestamps
            position_seconds = position / self.fs
            timestamps = sorted([(int(k), float(v)) for k, v in self.timestamps["decel"].items()], 
                                key=lambda x: x[1])
            
            # If we're before the first timestamp, return the highest RPM (decel starts at high RPM)
            if position_seconds <= timestamps[0][1]:
                return timestamps[0][0]
            
            # If we're after the last timestamp, return the lowest RPM
            if position_seconds >= timestamps[-1][1]:
                return timestamps[-1][0]
            
            # Find the two surrounding timestamps
            for i in range(len(timestamps) - 1):
                if timestamps[i][1] <= position_seconds < timestamps[i+1][1]:
                    # Linear interpolation between RPM values
                    high_rpm, low_time = timestamps[i]
                    low_rpm, high_time = timestamps[i+1]
                    
                    # Calculate interpolated RPM
                    fraction = (position_seconds - low_time) / (high_time - low_time)
                    return high_rpm - int(fraction * (high_rpm - low_rpm))
            
            # Fallback
            return int(self.rpm)
        
        else:
            # For idle and max_rpm, use existing RPM
            return int(self.rpm)

    def _start_continuous_stream(self):
        """Start a continuous audio stream with smooth transitions"""
        
        def audio_callback(outdata, frames, time_info, status):
            if status:
                print(f"Status: {status}")
            
            # Determine the current RPM based on audio position
            if self.state == "accel" or self.state == "decel":
                position = self.accel_position if self.state == "accel" else self.decel_position
                current_rpm = self._get_rpm_from_position(position)
                
                # Only update RPM if not shifting
                if not self.shifting:
                    self.rpm = current_rpm
            elif self.state == "max_rpm":
                # In max_rpm state, RPM should stay at 18000
                if not self.shifting:
                    self.rpm = 18000
            
            # If we're shifting, adjust RPM smoothly to target
            if self.shifting:
                # Calculate how far we are through the shift (0-1)
                shift_progress = min(1.0, (time.time() - self.shift_start_time) / self.shift_duration)
                
                # If shift is complete, clear the shifting flag
                if shift_progress >= 1.0:
                    self.shifting = False
                else:
                    # Smooth transition to target RPM during shift
                    self.rpm = self.last_shift_rpm + (self.target_rpm - self.last_shift_rpm) * shift_progress
            
            # Prepare output buffer with silence
            output_buffer = np.zeros((frames, self.audio_data["idle.wav"].shape[1] 
                                      if len(self.audio_data["idle.wav"].shape) > 1 else 1))
            
            # Handle state-specific audio playback
            if self.state == "idle":
                # Simple looping for idle state
                chunk = self._get_looping_chunk("idle.wav", self.idle_position, frames)
                self.idle_position = (self.idle_position + frames) % len(self.audio_data["idle.wav"])
                output_buffer = chunk
                
            elif self.state == "max_rpm":
                # Fix the max_rpm audio looping
                # Get speed factor based on current gear
                speed_factor = self.max_rpm_speed_factor
                
                # Get a chunk of max_rpm audio for looping
                chunk = self._get_looping_chunk("max_rpm.wav", self.max_rpm_position, frames)
                self.max_rpm_position = (self.max_rpm_position + frames) % len(self.audio_data["max_rpm.wav"])
                
                # Apply the speed factor if not 1.0
                if speed_factor != 1.0:
                    try:
                        # We need to resample using the proper speed factor
                        adjusted_frames = int(frames / speed_factor)
                        temp_chunk = self._get_looping_chunk("max_rpm.wav", self.max_rpm_position, adjusted_frames)
                        chunk = resample(temp_chunk, frames)
                    except Exception as e:
                        print(f"Max RPM resampling issue: {e}")
                        # Use the original chunk as fallback
                
                # Ensure correct output dimensions
                if len(chunk) < frames:
                    padding = np.zeros((frames - len(chunk), 
                                      chunk.shape[1] if len(chunk.shape) > 1 else 1))
                    chunk = np.vstack((chunk, padding)) if len(chunk.shape) > 1 else np.append(chunk, padding)
                elif len(chunk) > frames:
                    chunk = chunk[:frames]
                
                output_buffer = chunk
                
            elif self.state == "accel":
                # Get the gear-adjusted playback speed
                speed_factor = self.gear_speeds[self.gear - 1]
                
                # Get position in the audio file based on current RPM
                # This is a key change - use RPM to determine position when needed
                if self.shifting or self.rpm_stable == False:
                    # During shifting or when RPM is changing, position based on current RPM
                    rpm_position = self._get_rpm_timestamp("accel", int(self.rpm))
                    self.accel_position = int(rpm_position * self.fs)
                
                # Then proceed with normal audio playback from current position
                chunk_start = self.accel_position
                adjusted_frames = int(frames * speed_factor)
                chunk_end = min(chunk_start + adjusted_frames, len(self.audio_data["accel.wav"]))
                
                # Get the audio chunk
                if chunk_end - chunk_start < adjusted_frames:
                    # We've reached the end of the file - transition to max_rpm
                    print("Reached end of acceleration audio, switching to max RPM")
                    self.state = "max_rpm"
                    self.max_rpm_position = 0
                    self.reached_max_rpm_naturally = True
                    self.max_rpm_speed_factor = speed_factor
                    
                    # Get max_rpm audio with proper speed factor
                    adjusted_max_frames = int(frames * speed_factor)
                    max_chunk = self.audio_data["max_rpm.wav"][:adjusted_max_frames]
                    if speed_factor != 1.0:
                        try:
                            max_chunk = resample(max_chunk, frames)
                        except:
                            print("Resampling issue with max_rpm audio")
                            max_chunk = np.zeros(frames)
                    
                    chunk = max_chunk
                else:
                    chunk = self.audio_data["accel.wav"][chunk_start:chunk_end]
                    self.accel_position = chunk_end  # Advance position
                
                # After updating position, calculate the current RPM based on the new position
                # This is important for accurate RPM reporting
                if not self.shifting and self.state == "accel":
                    self.rpm = self._get_rpm_from_position(self.accel_position)
                
                # Rest of audio processing code...
                if chunk.size > 0:
                    # Resample to match desired playback speed
                    if speed_factor != 1.0 and self.state == "accel":  # Only resample accel audio
                        try:
                            chunk = resample(chunk, frames)
                        except:
                            # Fallback for resampling issues
                            print(f"Resampling issue at pos {chunk_start}, len {len(chunk)}")
                            chunk = np.zeros(frames)
                        
                        # Make sure output is correct size
                        if len(chunk) > frames:
                            output_buffer = chunk[:frames]
                        else:
                            # Pad if needed (shouldn't usually happen)
                            pad_length = frames - len(chunk)
                            if pad_length > 0:
                                if len(chunk.shape) > 1:
                                    padding = np.zeros((pad_length, chunk.shape[1]))
                                else:
                                    padding = np.zeros(pad_length)
                                chunk = np.vstack((chunk, padding)) if len(chunk.shape) > 1 else np.append(chunk, padding)
                            output_buffer = chunk
                
            elif self.state == "decel":
                # Similar to accel, but for deceleration
                if self.shifting or self.rpm_stable == False:
                    # Position based on current RPM during shifts
                    rpm_position = self._get_rpm_timestamp("decel", int(self.rpm))
                    self.decel_position = int(rpm_position * self.fs)
                
                # Continue with normal decel audio processing
                # For deceleration, calculate position based on RPM
                rpm_position = self._get_rpm_timestamp("decel", int(self.rpm))
                sample_position = int(rpm_position * self.fs)
                
                # Ensure we don't read past the end of the audio file
                if sample_position + frames < len(self.audio_data["decel.wav"]):
                    chunk = self.audio_data["decel.wav"][sample_position:sample_position + frames]
                    output_buffer = chunk
                else:
                    # Transition to idle if we reach the end of decel audio
                    self.state = "idle"
                    chunk = self._get_looping_chunk("idle.wav", 0, frames)
                    self.idle_position = frames
                    output_buffer = chunk
                
                # Update RPM based on new position
                if not self.shifting and self.state == "decel":
                    self.rpm = self._get_rpm_from_position(self.decel_position)
            
            # Apply output buffer to actual audio output
            outdata[:] = output_buffer.reshape(frames, -1)

        # Start the continuous stream
        self.current_stream = sd.OutputStream(
            callback=audio_callback,
            samplerate=self.fs,
            channels=self.audio_data["idle.wav"].shape[1] if len(self.audio_data["idle.wav"].shape) > 1 else 1,
            blocksize=512  # Smaller block size for more responsive audio
        )
        self.current_stream.start()
    
    def _get_looping_chunk(self, audio_file, position, frames):
        """Get a chunk of audio with proper looping"""
        audio = self.audio_data[audio_file]
        total_length = len(audio)
        
        # Handle wrap-around for looping audio
        if position + frames <= total_length:
            # Simple case - just get the chunk
            return audio[position:position + frames]
        else:
            # We need to loop back to the beginning
            first_part = audio[position:]
            remaining = frames - len(first_part)
            second_part = audio[:remaining]
            
            # Stack the parts together
            return np.vstack((first_part, second_part))

    def _stop_stream(self):
        if self.current_stream:
            self.current_stream.stop()
            self.current_stream.close()
            self.current_stream = None

    def shift_gear(self, new_gear, shifting=True):
        """Handle gear shifts properly by adjusting RPM"""
        if new_gear == self.gear:
            return
            
        # Record the RPM before shifting
        self.last_shift_rpm = self.rpm
        
        # Calculate target RPM after shifting
        rpm_change = 2000  # Approximate RPM change per gear
        
        if new_gear > self.gear:
            # Shifting up: RPM drops
            self.target_rpm = max(4000, self.rpm - rpm_change)
        else:
            # Shifting down: RPM increases
            self.target_rpm = min(18000, self.rpm + rpm_change)
        
        # Set shifting flag and start time
        self.shifting = True
        self.shift_start_time = time.time()
        
        # Update gear
        self.gear = new_gear
        
        # Update max_rpm speed factor
        self.max_rpm_speed_factor = self.gear_speeds[new_gear - 1]

    def update(self, power, gear, mph, shifting=False):
        prev_rpm = self.rpm
        prev_state = self.state
        prev_gear = self.gear
        
        self.power = max(0.0, min(1.0, power))
        
        # Handle gear changes with proper RPM adjustment
        if gear != self.gear:
            # Use our shift_gear method
            self.shift_gear(gear)
        else:
            # Normal non-shifting update
            self.gear = gear
            
            # Always update max_rpm speed factor when gear changes
            if self.state == "max_rpm":
                self.max_rpm_speed_factor = self.gear_speeds[gear - 1]
        
        # Determine the appropriate state based on conditions
        new_state = self.state
        
        if self.power < 0.05:
            # Only go to idle state if power drops very low
            new_state = "idle"
            self.reached_max_rpm_naturally = False
        elif self.power > 0.95 or self.rpm >= 17800:  # Close enough to max RPM
            # Go to max_rpm state when at full throttle or very high RPM
            new_state = "max_rpm"
            self.target_rpm = 18000
        else:
            # Significant throttle reduction should exit max_rpm state
            throttle_dropped = (self.power < 0.7) and prev_state == "max_rpm"
            
            # Keep in max_rpm state if:
            # 1. We're already there naturally, AND
            # 2. Throttle hasn't dropped significantly, AND
            # 3. Gear hasn't changed OR we're above a high RPM threshold
            if self.reached_max_rpm_naturally and not throttle_dropped and (gear == prev_gear or self.rpm > 17000):
                # Stay in max_rpm state
                new_state = "max_rpm"
            # Deceleration check
            elif mph < self.prev_mph - 1.0:
                new_state = "decel"
                self.reached_max_rpm_naturally = False
            else:
                # Default to acceleration
                new_state = "accel"
                
                # Reset flag if coming from max_rpm
                if prev_state == "max_rpm":
                    self.reached_max_rpm_naturally = False
        
        # Update state if changed
        if new_state != self.state:
            # Reset RPM stability when state changes
            self.rpm_stable = False
            self.last_state_change = time.time()
            
            # Reset reached_max_rpm_naturally when transitioning from max_rpm to accel
            if self.state == "max_rpm" and new_state == "accel":
                self.reached_max_rpm_naturally = False
                
            # Update state after flag resets
            self.state = new_state
            
            # Reset positions when state changes
            if new_state == "accel" and prev_state != "accel":
                rpm_position = self._get_rpm_timestamp("accel", int(self.rpm))
                self.accel_position = int(rpm_position * self.fs)
            elif new_state == "decel" and prev_state != "decel":
                rpm_position = self._get_rpm_timestamp("decel", int(self.rpm))
                self.decel_position = int(rpm_position * self.fs)
            elif new_state == "max_rpm" and prev_state != "max_rpm":
                # Reset max_rpm position to beginning when entering max_rpm state
                self.max_rpm_position = 0
                self.max_rpm_speed_factor = self.gear_speeds[gear - 1]
                
                # If we reached max_rpm naturally from accel, set the flag
                if prev_state == "accel" and self.rpm >= 17800:
                    self.reached_max_rpm_naturally = True
        
        # Update previous speed
        self.prev_mph = mph
        
    def __del__(self):
        self._stop_stream()
