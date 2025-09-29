import numpy as np
import sounddevice as sd
import soundfile as sf
import json
import os

class EngineSim:
    def __init__(self, audio_dir="audio_cleaned", timestamp_json="timestamps.json"):
        self.samplerate = 44100
        self.chunk_ms = 50
        self.chunk_samples = int(self.samplerate * self.chunk_ms / 1000)

        self.audio = {
            "accel": self.load_audio(os.path.join(audio_dir, "accel.wav")),
            "decel": self.load_audio(os.path.join(audio_dir, "decel.wav")),
            "idle": self.load_audio(os.path.join(audio_dir, "idle.wav")),
            "max": self.load_audio(os.path.join(audio_dir, "max_rpm.wav")),
        }

        with open(timestamp_json, "r") as f:
            self.timestamps = json.load(f)

        self.stream = sd.OutputStream(samplerate=self.samplerate, channels=1, dtype='float32')
        self.stream.start()

        self.state = "idle"
        self.current_rpm = 4000
        self.prev_rpm = 4000
        self.idle_loop_index = 0
        self.max_loop_index = 0
        self.prev_chunk = np.zeros(self.chunk_samples)

    def load_audio(self, path):
        data, sr = sf.read(path)
        if data.ndim > 1:
            data = data[:, 0]  # convert to mono
        data = data.astype(np.float32)
        if sr != self.samplerate:
            raise ValueError(f"Expected {self.samplerate}Hz but got {sr}Hz in {path}")
        return data

    def get_timestamp(self, rpm, mode):
        rpm = str(int(rpm))
        return self.timestamps[mode].get(rpm, 0)

    def get_audio_chunk(self, audio, timestamp):
        start_sample = int(timestamp * self.samplerate)
        end_sample = start_sample + self.chunk_samples
        chunk = audio[start_sample:end_sample]
        if len(chunk) < self.chunk_samples:
            chunk = np.pad(chunk, (0, self.chunk_samples - len(chunk)))
        return chunk

    def crossfade_chunks(self, prev, next_chunk, fade_len=1000):
        fade_len = min(fade_len, len(prev), len(next_chunk))
        fade_in = np.linspace(0, 1, fade_len)
        fade_out = 1 - fade_in
        next_chunk[:fade_len] = (
            next_chunk[:fade_len] * fade_in + prev[-fade_len:] * fade_out
        )
        return next_chunk

    def update(self, acceleration):
        self.prev_rpm = self.current_rpm

        if acceleration > 0.1:
            self.state = "accel"
            self.current_rpm += acceleration * 500  # scale as needed
        elif acceleration < -0.1:
            self.state = "decel"
            self.current_rpm += acceleration * 500
        else:
            # maintain current state if at rpm extremes
            if self.current_rpm >= 18000:
                self.state = "max"
            elif self.current_rpm <= 4000:
                self.state = "idle"
            else:
                # coast state (maintain previous)
                pass

        self.current_rpm = max(4000, min(18000, self.current_rpm))

        # Play appropriate chunk
        self.play_chunk()

    def play_chunk(self):
        if self.state in ["accel", "decel"]:
            timestamp = self.get_timestamp(self.current_rpm, self.state)
            chunk = self.get_audio_chunk(self.audio[self.state], timestamp)
        elif self.state == "idle":
            self.idle_loop_index = (self.idle_loop_index + self.chunk_samples) % len(self.audio["idle"])
            chunk = self.audio["idle"][self.idle_loop_index:self.idle_loop_index + self.chunk_samples]
        elif self.state == "max":
            self.max_loop_index = (self.max_loop_index + self.chunk_samples) % len(self.audio["max"])
            chunk = self.audio["max"][self.max_loop_index:self.max_loop_index + self.chunk_samples]
        else:
            chunk = np.zeros(self.chunk_samples)

        if len(chunk) < self.chunk_samples:
            chunk = np.pad(chunk, (0, self.chunk_samples - len(chunk)))

        # Crossfade with previous chunk
        chunk = self.crossfade_chunks(self.prev_chunk, chunk)
        self.stream.write(chunk)
        self.prev_chunk = chunk.copy()

    def stop(self):
        self.stream.stop()
        self.stream.close()