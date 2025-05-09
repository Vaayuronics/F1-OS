import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import resampy
import threading
import queue
import time
import os


class EngineAudioPlayer:
    def __init__(self, rev_up_path, rev_down_path):
        self.sr = 48000
        self.rev_up_data = self._load_and_preprocess_audio(rev_up_path)
        self.rev_down_data = self._load_and_preprocess_audio(rev_down_path)

        # Increase buffer size and add a minimum buffer threshold
        self.buffer = queue.Queue(maxsize=100)  # Increased from 50
        self.buffer_target = 5  # Aim to keep at least 5 chunks in buffer
        self.running = True
        self.playback_started = False

        self.stream = sd.OutputStream(
            samplerate=self.sr,
            channels=2 if self.rev_up_data.ndim == 2 else 1,
            dtype='float32',
            blocksize=1024,
            latency='high'
        )
        self.stream.start()

        self.writer_thread = threading.Thread(target=self._buffer_writer, daemon=True)
        self.writer_thread.start()

    def _load_and_preprocess_audio(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        sr, data = wav.read(path)
        if data.dtype != np.float32:
            data = data / np.iinfo(data.dtype).max
        data = data.astype(np.float32)

        if sr != self.sr:
            if data.ndim == 1:
                data = resampy.resample(data, sr, self.sr)
            else:
                data = resampy.resample(data.T, sr, self.sr).T
        return data

    def _buffer_writer(self):
        while self.running:
            try:
                # Only start consuming when we have enough data
                if not self.playback_started and self.buffer.qsize() >= self.buffer_target:
                    self.playback_started = True
                
                # If buffer runs critically low, introduce a small wait to rebuild
                if self.playback_started and self.buffer.qsize() < 2:
                    time.sleep(0.02)  # Short delay to allow buffer to refill
                
                chunk = self.buffer.get(timeout=0.1)
                # Ensure the data is contiguous before writing
                chunk = np.ascontiguousarray(chunk)
                self.stream.write(chunk)
            except queue.Empty:
                time.sleep(0.01)

    def play_chunk(self, rev_up=True, start_time=0.0, speed=1.0, duration=0.2):
        data = self.rev_up_data if rev_up else self.rev_down_data
        start_sample = int(start_time * self.sr)
        total_samples = data.shape[0]
        requested_samples = int(duration * speed * self.sr)
        end_sample = start_sample + requested_samples

        if start_sample >= total_samples:
            return True

        chunk = data[max(0, start_sample):min(end_sample, total_samples)]

        # Resample for speed
        if speed != 1.0:
            if chunk.ndim == 1:
                chunk = resampy.resample(chunk, self.sr * speed, self.sr)
            else:
                chunk = resampy.resample(chunk.T, self.sr * speed, self.sr).T
                
            # Apply very small fade in/out to reduce clicking
            fade_samples = min(int(0.005 * self.sr), len(chunk) // 8)  # 5ms or 1/8 of chunk
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                if chunk.ndim == 1:  # Mono
                    chunk[:fade_samples] *= fade_in
                    chunk[-fade_samples:] *= fade_out
                else:  # Stereo
                    chunk[:fade_samples] *= fade_in.reshape(-1, 1)
                    chunk[-fade_samples:] *= fade_out.reshape(-1, 1)

        try:
            # Make sure data is contiguous when putting in buffer
            chunk = np.ascontiguousarray(chunk)
            self.buffer.put_nowait(chunk)
        except queue.Full:
            # If buffer is full, we shouldn't discard data - try again with timeout
            try:
                self.buffer.put(chunk, timeout=0.05)
            except queue.Full:
                pass  # Now we can give up

        return end_sample >= total_samples

    def stop(self):
        self.running = False
        self.writer_thread.join()
        self.stream.stop()
        self.stream.close()

    def get_buffer_status(self):
        """Return the current buffer size and maximum capacity"""
        return self.buffer.qsize(), self.buffer.maxsize


# Example usage - only run this if the script is executed directly
if __name__ == "__main__":
    import time
    
    player = EngineAudioPlayer("Pi/engine/audio/accel.wav", "Pi/engine/audio/decel.wav")
    counter = 0.0
    speed = 1.25
    chunk_duration = 1.0  # Original chunk duration
    actual_duration = chunk_duration / speed  # Actual playback duration after speed adjustment
    up = True
    
    # Pre-buffer some audio before starting
    print("Pre-buffering audio...")
    for i in range(10):  # Buffer 10 chunks before starting
        player.play_chunk(rev_up=up, start_time=counter, speed=speed, duration=chunk_duration)
        counter += chunk_duration
    counter = 0.0  # Reset counter
    
    try:
        start_time = time.time()
        next_chunk_time = start_time
        
        while True:
            # Calculate time until next chunk should be processed
            current_time = time.time()
            time_to_next = next_chunk_time - current_time
            
            if time_to_next > 0:
                time.sleep(time_to_next)
            
            # Process chunk
            done = player.play_chunk(rev_up=up, start_time=counter, speed=speed, duration=chunk_duration)
            
            # Update for next iteration with the correct timing
            counter += chunk_duration
            next_chunk_time += actual_duration  # Schedule based on actual playback duration
            
            if done:
                print("End of file reached.")
                counter = 0.0
                up = not up
                
    except KeyboardInterrupt:
        print("Stopping playback...")
    finally:
        player.stop()
