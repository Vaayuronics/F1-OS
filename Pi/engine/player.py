import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import resampy
import threading
import queue
import time
import os

SAMPLE_RATE = 48000  # Sample rate for audio playback

class EngineAudioPlayer:
    def __init__(self, rev_up_path, rev_down_path, chunk_duration, target = 10):
        self.rev_up_data = self._load_and_preprocess_audio(rev_up_path)
        self.rev_down_data = self._load_and_preprocess_audio(rev_down_path)

        # Increase buffer size and add a minimum buffer threshold
        self.buffer = queue.Queue(maxsize=100)  # Increased from 50
        self.buffer_target = target
        self.running = True
        self.playback_started = False
        block_size = self._calculate_optimal_blocksize(chunk_duration)
        print(f"Block size: {block_size} samples.")

        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=2 if self.rev_up_data.ndim == 2 else 1,
            dtype='float32',
            blocksize=block_size,
            latency=0.1
        )
        self.stream.start()

        self.writer_thread = threading.Thread(target=self._buffer_writer, daemon=True)
        self.writer_thread.start()

    def _calculate_optimal_blocksize(self, chunk_duration):
        """Calculate the optimal blocksize based on typical chunk parameters"""
        # Calculate samples for a typical chunk after resampling
        samples_per_chunk = int(chunk_duration * SAMPLE_RATE)
            
        # Make sure it's a power of 2 for optimal performance
        # Find the nearest power of 2 that's equal or greater than our size
        power_of_2 = 2
        while power_of_2 < samples_per_chunk:
            power_of_2 *= 2
            if power_of_2 > 8192:  # Limit to a reasonable maximum
                power_of_2 = 8192
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
        return data

    def _buffer_writer(self):
        while self.running:
            try:
                # Only start consuming when we have enough data
                if not self.playback_started and self.buffer.qsize() >= self.buffer_target:
                    self.playback_started = True
                            
                chunk = self.buffer.get(timeout=0.1)
                self.stream.write(chunk)
            except queue.Empty:
                pass

    def play_chunk(self, rev_up, start_time, speed, duration):
        data = self.rev_up_data if rev_up else self.rev_down_data
        start_sample = int(start_time * SAMPLE_RATE * speed)
        total_samples = data.shape[0]
        requested_samples = int(duration * speed * SAMPLE_RATE)
        end_sample = start_sample + requested_samples

        if start_sample >= total_samples:
            return True

        chunk = data[max(0, start_sample):min(end_sample, total_samples)]

        # Resample for speed
        if speed != 1.0:
            if chunk.ndim == 1:
                chunk = resampy.resample(chunk, SAMPLE_RATE * speed, SAMPLE_RATE)
            else:
                chunk = resampy.resample(chunk.T, SAMPLE_RATE * speed, SAMPLE_RATE).T
                
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

        # Make sure data is contiguous when putting in buffer
        chunk = np.ascontiguousarray(chunk)
        try:
            self.buffer.put_nowait(chunk)
        except queue.Full:
            # If the buffer is full, we can either drop the chunk or wait
            # Here we choose to drop the chunk
            print("Buffer full, dropping chunk")

        return end_sample >= total_samples

    def stop(self):
        self.running = False
        self.writer_thread.join()
        self.stream.stop()
        self.stream.close()


# Example usage - only run this if the script is executed directly
if __name__ == "__main__":
    import time
    
    counter = 0.0
    dur = 1 # Use larger chunks for more stability
    up = True
    sp = 1.25  # Speed
    player = EngineAudioPlayer("Pi/engine/audio/accel.wav", "Pi/engine/audio/decel.wav", dur, 5)
        
    while True:
        # Process chunk
        buffer_dur = sp * (dur+3)
        done = player.play_chunk(rev_up=up, start_time=counter, speed=sp, duration=buffer_dur)
        
        # Update for next iteration
        counter += buffer_dur

        time.sleep(dur) # Sleep for the duration of the chunk minus a small buffer

        if done:
            print("End of file reached.")
            counter = 0.0
            up = not up
