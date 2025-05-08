import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import resampy
import os

class EngineAudioPlayer:
    def __init__(self, rev_up_path, rev_down_path):
        self.sr = 48000  # Target playback sample rate
        self.rev_up_data = self._load_and_preprocess_audio(rev_up_path)
        self.rev_down_data = self._load_and_preprocess_audio(rev_down_path)

    def _load_and_preprocess_audio(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        sr, data = wav.read(path)

        if data.dtype != np.float32:
            data = data / np.iinfo(data.dtype).max
        data = data.astype(np.float32)

        if sr != self.sr:
            # Resample to 48kHz if needed
            if data.ndim == 1:
                data = resampy.resample(data, sr, self.sr)
            else:
                data = resampy.resample(data.T, sr, self.sr).T
        return data

    def play_chunk(self, rev_up=True, start_time=0.0, speed=1.0, duration=0.1):
        """
        Play a chunk of audio and return True if it reached or exceeded the end of the file.

        Args:
            rev_up (bool): True for rev-up file, False for rev-down.
            start_time (float): Where to start in seconds.
            speed (float): Playback speed multiplier.
            duration (float): Duration of playback (in seconds, real-time).

        Returns:
            bool: True if this was the last chunk or went past end of audio, False otherwise.
        """
        data = self.rev_up_data if rev_up else self.rev_down_data
        sr = self.sr
        start_sample = int(start_time * sr)
        total_samples = data.shape[0]

        # Duration in source data depends on speed
        requested_samples = int(duration * speed * sr)
        end_sample = start_sample + requested_samples

        if start_sample >= total_samples:
            return True  # Already past end

        chunk = data[start_sample:min(end_sample, total_samples)]

        # Speed-adjust via resampling
        if speed != 1.0:
            if chunk.ndim == 1:
                chunk = resampy.resample(chunk, sr * speed, sr)
            else:
                chunk = resampy.resample(chunk.T, sr * speed, sr).T

        sd.play(chunk, sr, blocking=False)

        # If we reached or exceeded the end of the audio file
        return end_sample >= total_samples

import time
player = EngineAudioPlayer("rev_up.wav", "rev_down.wav")

while True:
    finished = player.play_chunk(
        rev_up=True,
        start_time=2.0,
        speed=1.3,
        duration=0.1
    )
    
    if finished:
        print("End of file reached")

    time.sleep(0.05)
