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

        self.buffer = queue.Queue(maxsize=50)
        self.running = True

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
                chunk = self.buffer.get(timeout=0.1)
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

        chunk = data[start_sample:min(end_sample, total_samples)]

        # Resample for speed
        if speed != 1.0:
            if chunk.ndim == 1:
                chunk = resampy.resample(chunk, self.sr * speed, self.sr)
            else:
                chunk = resampy.resample(chunk.T, self.sr * speed, self.sr).T

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
    
    player = EngineAudioPlayer("audio/accel.wav", "audio/decel.wav")
    counter = 0.0
    chunk_duration = 0.05  # Even smaller chunks for more continuous playback
    up = True
    
    while True:
        
        # Process chunk
        done = player.play_chunk(rev_up=up, start_time=counter, speed=1.0, duration=chunk_duration)
        time.sleep(chunk_duration)
        
        # Update for next iteration
        counter += chunk_duration
        
        if done:
            print("End of file reached.")
            counter = 0.0
            up = not up
