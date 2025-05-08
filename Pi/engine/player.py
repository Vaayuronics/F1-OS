import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import resampy
import threading
import os
import queue


class EngineAudioPlayer:
    def __init__(self, rev_up_path, rev_down_path):
        self.sr = 48000
        self.rev_up_data = self._load_and_preprocess_audio(rev_up_path)
        self.rev_down_data = self._load_and_preprocess_audio(rev_down_path)

        self.buffer = queue.Queue(maxsize=10)  # for smooth stream
        self.stream = sd.OutputStream(
            samplerate=self.sr,
            channels=2 if self.rev_up_data.ndim == 2 else 1,
            dtype='float32',
            callback=self._audio_callback
        )
        self.stream.start()

        self._end_of_file = False
        self._lock = threading.Lock()

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

    def _audio_callback(self, outdata, frames, time_info, status):
        try:
            data = self.buffer.get(timeout=0.1)
            if len(data) < frames:
                outdata[:len(data)] = data
                outdata[len(data):] = 0
            else:
                outdata[:] = data[:frames]
                # Return remaining data to buffer if any
                if len(data) > frames:
                    self.buffer.put(data[frames:], timeout=0.05)
        except queue.Empty:
            outdata[:] = np.zeros_like(outdata)

    def play_chunk(self, rev_up=True, start_time=0.0, speed=1.0, duration=0.1):
        """
        Queue a chunk of audio to play smoothly via streaming.
        Returns True if chunk hits or exceeds end of file.
        """
        data = self.rev_up_data if rev_up else self.rev_down_data
        start_sample = int(start_time * self.sr)
        total_samples = data.shape[0]
        requested_samples = int(duration * speed * self.sr)
        end_sample = start_sample + requested_samples

        if start_sample >= total_samples:
            return True

        chunk = data[start_sample:min(end_sample, total_samples)]

        if speed != 1.0:
            if chunk.ndim == 1:
                chunk = resampy.resample(chunk, self.sr * speed, self.sr)
            else:
                chunk = resampy.resample(chunk.T, self.sr * speed, self.sr).T

        try:
            self.buffer.put_nowait(chunk)
        except queue.Full:
            pass  # drop if too much queued

        return end_sample >= total_samples

    def stop(self):
        self.stream.stop()
        self.stream.close()


import time

player = EngineAudioPlayer("audio/accel.wav", "audio/decel.wav")
counter = 0.0
duration = 1  # seconds

while True:
    done = player.play_chunk(
        rev_up=True,
        start_time=counter,
        speed=1.0,
        duration=duration
    )
    counter += duration
    if done:
        print("End of audio.")
        break
    time.sleep(duration)  # overlapping calls are OK
