import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import resampy
import threading
import time
import os


class EngineAudioPlayer:
    def __init__(self, rev_up_path, rev_down_path, fade_duration=0.01, buffer_duration=2.0):
        self.sr = 48000
        self.fade_duration = fade_duration

        self.rev_up_data = self._load_and_preprocess_audio(rev_up_path)
        self.rev_down_data = self._load_and_preprocess_audio(rev_down_path)

        self.channels = 2 if self.rev_up_data.ndim == 2 else 1
        self.buffer_samples = int(buffer_duration * self.sr)
        self.buffer = np.zeros((self.buffer_samples, self.channels), dtype=np.float32)

        self.write_pos = 0
        self.read_pos = 0
        self.lock = threading.Lock()
        self.running = True

        self.stream = sd.OutputStream(
            samplerate=self.sr,
            channels=self.channels,
            dtype='float32',
            callback=self._callback,
            blocksize=1024
        )
        self.stream.start()

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

    def _apply_fade(self, chunk):
        fade_samples = int(self.fade_duration * self.sr)
        if len(chunk) < 2 * fade_samples:
            return chunk
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        if chunk.ndim == 1:
            chunk[:fade_samples] *= fade_in
            chunk[-fade_samples:] *= fade_out
        else:
            chunk[:fade_samples, :] *= fade_in[:, None]
            chunk[-fade_samples:, :] *= fade_out[:, None]
        return chunk

    def _callback(self, outdata, frames, time_info, status):
        with self.lock:
            end_pos = (self.read_pos + frames) % self.buffer_samples
            if self.read_pos < end_pos or end_pos == 0:
                outdata[:] = self.buffer[self.read_pos:self.read_pos + frames]
            else:
                part1 = self.buffer[self.read_pos:]
                part2 = self.buffer[:end_pos]
                outdata[:len(part1)] = part1
                outdata[len(part1):] = part2
            self.read_pos = end_pos

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
                chunk = resampy.resample(chunk, self.sr, int(self.sr / speed))
            else:
                chunk = resampy.resample(chunk, self.sr, int(self.sr / speed))

        # Ensure chunk is 2D
        if chunk.ndim == 1:
            chunk = np.expand_dims(chunk, axis=1)

        # Apply fade
        chunk = self._apply_fade(chunk)

        with self.lock:
            chunk_len = chunk.shape[0]
            end_write_pos = (self.write_pos + chunk_len) % self.buffer_samples
            if self.write_pos < end_write_pos or end_write_pos == 0:
                self.buffer[self.write_pos:self.write_pos + chunk_len] = chunk
            else:
                part1_len = self.buffer_samples - self.write_pos
                self.buffer[self.write_pos:] = chunk[:part1_len]
                self.buffer[:end_write_pos] = chunk[part1_len:]
            self.write_pos = end_write_pos

        return end_sample >= total_samples

    def stop(self):
        self.running = False
        self.stream.stop()
        self.stream.close()


import time

player = EngineAudioPlayer("audio/accel.wav", "audio/decel.wav")
counter = 0.0
duration = 0.2
rev = True

# Pre-fill buffer
for _ in range(10):
    done = player.play_chunk(rev_up=rev, start_time=counter, speed=1.0, duration=duration)
    counter += duration

# Runtime loop
try:
    while True:
        done = player.play_chunk(rev_up=rev, start_time=counter, speed=1.0, duration=duration)
        counter += duration
        if done:
            counter = 0.0
            rev = not rev
        time.sleep(duration - 0.05)  # Sleep for a bit less than the duration to avoid drift
except KeyboardInterrupt:
    player.stop()
