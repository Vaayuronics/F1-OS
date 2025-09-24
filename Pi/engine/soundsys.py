from scipy.io import wavfile
import librosa, numpy as np
import time
import sys

BASE_OUTPUT_PATH = "engine/modio/"

# Load audio with proper error handling
accel, fs = librosa.load("engine/audio/accel.wav", sr=None)  # Keep original sample rate
print(f"Loaded audio: {len(accel)/fs:.2f} seconds, {fs} Hz")

song_2_times_faster = librosa.effects.time_stretch(song, rate=2)
print(f"2x speed duration: {len(song_2_times_faster)/fs:.2f} seconds")

song_4_times_faster = librosa.effects.time_stretch(song, rate=4)
print(f"4x speed duration: {len(song_4_times_faster)/fs:.2f} seconds")

wavfile.write(f"{BASE_OUTPUT_PATH}song_2_times_faster.wav", fs, song_2_times_faster)
wavfile.write(f"{BASE_OUTPUT_PATH}song_4_times_faster.wav", fs, song_4_times_faster)

