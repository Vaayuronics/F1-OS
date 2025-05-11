import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import resampy
import queue
import time
import os
from threading import Thread

SAMPLE_RATE = 44100  # Sample rate for audio playback

class EngineAudioStatus:
    '''Class to represent the status of the audio engine.'''
    def __init__(self, end_of_file, dropped, waitTime, position, error=None):
        self.end_of_file = end_of_file
        self.dropped = dropped
        self.waitTime = waitTime
        self.position = position
        self.error = error
        
    def __getitem__(self, key):
        if key == 'done':
            return self.end_of_file
        elif key == 'dropped':
            return self.dropped
        elif key == 'waitTime':
            return self.waitTime
        elif key == 'position':
            return self.position
        elif key == 'error':
            return self.error
        else:
            raise KeyError(f"Invalid key: {key}")
        
class EngineChunk:
    def __init__(self, data, duration):
        self.data = data
        self.duration = duration

    def __getitem__(self, key):
        if key == 'data':
            return self.data
        elif key == 'duration':
            return self.duration
        else:
            raise KeyError(f"Invalid key: {key}")
        
class EngineAudioPlayer:
    def __init__(self, rev_up_path, rev_down_path, chunk_duration, target = 1, max_buffer_size = 2):
        self.rev_up_data = self._load_and_preprocess_audio(rev_up_path)
        self.rev_down_data = self._load_and_preprocess_audio(rev_down_path)

        # Increase buffer size and add a minimum buffer threshold
        self.buffer = queue.Queue(maxsize=max_buffer_size)
        self.buffer_target = target
        self.running = True
        self.playback_started = False
        block_size = self._calculate_optimal_blocksize(chunk_duration)

        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=2 if self.rev_up_data.ndim == 2 else 1,
            dtype='float32',
            blocksize=block_size,
            latency='low'
        )
        self.stream.start()

        self.writer_thread = Thread(target=self._buffer_writer, daemon=True)
        self.writer_thread.start()
        print("Audio player initialized and started.")

    def _calculate_optimal_blocksize(self, chunk_duration):
        """Calculate the optimal blocksize based on typical chunk parameters"""
        # Calculate samples for a typical chunk after resampling
        samples_per_chunk = int(chunk_duration * SAMPLE_RATE)
            
        # Make sure it's a power of 2 for optimal performance
        # Find the nearest power of 2 that's equal or greater than our size
        power_of_2 = 2
        while power_of_2 < samples_per_chunk:
            power_of_2 *= 2
            if power_of_2 > 4096:  # Limit to a reasonable maximum
                power_of_2 = 4096
                break
                
        # If we're close to the lower power of 2, use that instead
        if samples_per_chunk < (power_of_2 * 0.75) and power_of_2 > 2:
            power_of_2 //= 2
        
        print(f"Optimal blocksize: {power_of_2} samples (original chunk size: {samples_per_chunk})")
        return power_of_2

    def _load_and_preprocess_audio(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        sr, data = wav.read(path)
        if data.dtype != np.float32:
            data = data / np.iinfo(data.dtype).max
        data = data.astype(np.float32)

        if sr != SAMPLE_RATE:
            if data.ndim == 1:
                data = resampy.resample(data, sr, SAMPLE_RATE)
            else:
                data = resampy.resample(data.T, sr, SAMPLE_RATE).T
        print(f"Loaded and preprocessed audio from {path}: {data.shape} samples at {SAMPLE_RATE} Hz")
        return data

    def _buffer_writer(self):
        while self.running:
            try:
                start_time = time.time()
                # Only start consuming when we have enough data
                if not self.playback_started and self.buffer.qsize() >= self.buffer_target:
                    self.playback_started = True
                    print("Reached Target Size, starting playback.")
                
                if self.playback_started:
                    print("Writing to stream...")
                    chunk = self.buffer.get(timeout=0.1)
                    self.stream.write(chunk['data'])
                    elapsed = time.time() - start_time
                    print(f"Chunk duration: {chunk['duration']:.4f}s, Processing time: {elapsed:.4f}s")
                    #time.sleep(chunk['duration'] - elapsed)
            except queue.Empty:
                print("Buffer empty, waiting for data...")
                pass
            except Exception as e:
                print(f"Error in buffer writer: {e}")
                self.stop()

    def play_chunk(self, rev_up, start_time, speed, duration) -> EngineAudioStatus:
        if(self.running == False):
            print("Audio player is not running.")
            return EngineAudioStatus(False, False, 0, 0, "Audio player is not running.")
        print("Playing chunk...")
        data = self.rev_up_data if rev_up else self.rev_down_data
        start_sample = int(start_time * SAMPLE_RATE) # * speed
        total_samples = data.shape[0]
        requested_samples = int(duration * speed * SAMPLE_RATE)
        end_sample = start_sample + requested_samples
        print("\tCalculated Chunk")

        if start_sample >= total_samples:
            # End of file reached
            return EngineAudioStatus(True, False, 0, start_time)

        chunk = data[start_sample:min(end_sample, total_samples)]
        print("\tChunk sliced")

        # Resample for speed
        if speed != 1.0:
            print("\tResampling chunk")
            if chunk.ndim == 1:
                chunk = resampy.resample(chunk, SAMPLE_RATE * speed, SAMPLE_RATE, parallel=True)
            else:
                chunk = resampy.resample(chunk.T, SAMPLE_RATE * speed, SAMPLE_RATE, parallel=True).T
            print("\tChunk resampled, applying fade")

            # Apply very small fade in/out to reduce clicking
            fade_samples = min(int(0.005 * SAMPLE_RATE), len(chunk) // 8)  # 5ms or 1/8 of chunk
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                if chunk.ndim == 1:  # Mono
                    chunk[:fade_samples] *= fade_in
                    chunk[-fade_samples:] *= fade_out
                else:  # Stereo
                    chunk[:fade_samples] *= fade_in.reshape(-1, 1)
                    chunk[-fade_samples:] *= fade_out.reshape(-1, 1)
                print("\tFade applied")

        print("\tEnsuring chunk is contiguous")
        # Make sure data is contiguous when putting in buffer
        chunk = np.ascontiguousarray(chunk)
    
        print("\tPutting chunk in buffer")
        dropped = False
        try:
            self.buffer.put_nowait(EngineChunk(chunk, duration))
            print("\t\tChunk added to buffer")
        except queue.Full:
            dropped = True
            print("\t\tBuffer full, dropping chunk")

        print("\t\tBuffer size:", self.buffer.qsize())

        print("\tDone")
        return EngineAudioStatus(False, dropped, duration, start_time + duration)

    def stop(self):
        self.running = False
        self.writer_thread.join()
        self.stream.stop()
        self.stream.close()

import tkinter as tk
class EngineAudioUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Engine Audio Control")
        
        # Initial speed value
        self.sp = 1
        
        # Create a slider for speed
        self.speed_slider = tk.Scale(
            root, 
            from_=0.25, 
            to=3.0, 
            resolution=0.01,
            orient=tk.HORIZONTAL, 
            label="Speed",
            length=300,
            command=self.update_speed
        )
        self.speed_slider.set(self.sp)
        self.speed_slider.pack(padx=20, pady=20)
        
        # Audio player and status variables
        self.running = True
        self.player = None
        self.audio_thread = Thread(target=self.run_audio, daemon=True)
        self.audio_thread.start()
        
        # Set up cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def update_speed(self, val):
        self.sp = float(val)
        print(f"Speed updated to: {self.sp}")
        
    def run_audio(self):
        counter = 0.0
        dur = 0.05
        up = True
        self.player = EngineAudioPlayer("Pi/engine/audio/accel.wav", "Pi/engine/audio/decel.wav", dur)
        
        while self.running:
            # Process chunk
            done = self.player.play_chunk(rev_up=up, start_time=counter, speed=self.sp, duration=dur)
            if(done['error']):
                print(f"Error: {done['error']}")
                break
            
            # Update for next iteration
            if not done['dropped']:
                counter += done["waitTime"]

            if done['done']:
                print("End of file reached.")
                counter = 0.0
                up = not up
                
    def on_closing(self):
        self.running = False
        if self.player:
            self.player.stop()
        self.root.destroy()


# Example usage - only run this if the script is executed directly
if __name__ == "__main__":
    root = tk.Tk()
    app = EngineAudioUI(root)
    root.mainloop()
