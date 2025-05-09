import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import resampy
import threading
import queue
import time
import os

BASE_SR = 48000


class EngineAudioPlayer:
    def __init__(self, rev_up_path, rev_down_path):
        self.sr = BASE_SR
        self.rev_up_data = self._load_and_preprocess_audio(rev_up_path)
        self.rev_down_data = self._load_and_preprocess_audio(rev_down_path)

        self.buffer = queue.Queue(maxsize=50)
        self.running = True

        #Output stream is at 48000Hz but when respampling the data to speed up or slow down the sample rate changes which may cause issues
        self.stream = sd.OutputStream(
            samplerate=BASE_SR,
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

        if sr != BASE_SR:
            if data.ndim == 1:
                data = resampy.resample(data, sr, BASE_SR)
            else:
                data = resampy.resample(data.T, sr, BASE_SR).T
        return data

    def _buffer_writer(self):
        while self.running:
            if not self.buffer.empty():
                chunk = self.buffer.get(timeout=0.1)
                chunk = np.ascontiguousarray(chunk, dtype=np.float32)
                self.stream.write(chunk)

    def play_chunk(self, rev_up, start_time, speed, duration):
        if self.sr != self.sr * speed:
            self.sr = self.sr * speed
            # self.stream.close()
            # self.stream = sd.OutputStream(
            #     samplerate=self.sr * speed,
            #     channels=2 if self.rev_up_data.ndim == 2 else 1,
            #     dtype='float32',
            #     blocksize=1024,
            #     latency='high'
            # )
            # self.stream.start()

        data = self.rev_up_data if rev_up else self.rev_down_data
        start_sample = int(start_time * BASE_SR)
        total_samples = data.shape[0]
        requested_samples = int(duration * self.sr)
        end_sample = start_sample + requested_samples

        if start_sample >= total_samples:
            return True

        chunk = data[start_sample:min(end_sample, total_samples)]

        # Resample for speed

        if chunk.ndim == 1:
            chunk = resampy.resample(chunk, BASE_SR, self.sr)
        else:
            chunk = resampy.resample(chunk.T, BASE_SR, self.sr).T

        try:
            self.buffer.put_nowait(chunk)
        except queue.Full:
            pass

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
    chunk_duration = 0.05  # Even smaller chunks for more continuous playback
    up = True
    
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
            done = player.play_chunk(rev_up=up, start_time=counter, speed=1.25, duration=chunk_duration)
            
            # Update for next iteration
            counter += chunk_duration
            next_chunk_time += chunk_duration  # Schedule next chunk at fixed intervals
            
            # Buffer status monitoring (less frequent to reduce overhead)
            if counter % 1 < chunk_duration:
                buffer_size, buffer_max = player.get_buffer_status()
                real_time = time.time() - start_time
                print(f"Time: {real_time:.2f}s, Counter: {counter:.2f}s, Buffer: {buffer_size}/{buffer_max}")
                
                # Adjust if timing is drifting
                drift = real_time - counter
                if abs(drift) > 0.1:  # If we're more than 100ms off
                    print(f"Correcting timing drift of {drift:.3f}s")
                    next_chunk_time = time.time() + chunk_duration
            
            if done:
                print("End of file reached.")
                counter = 0.0
                up = not up
                
    except KeyboardInterrupt:
        print("Stopping playback...")
    finally:
        player.stop()
