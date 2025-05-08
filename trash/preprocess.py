import os
import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment

OUTPUT_DIR = "audio_cleaned"
FILES = ["max_rpm.wav"] #"accel.wav", "decel.wav", "idle.wav", 
TARGET_SR = 44100

os.makedirs(OUTPUT_DIR, exist_ok=True)

def preprocess_audio(file_name):
    path = os.path.join("audio", file_name)
    print(f"Processing {file_name}...")

    # Load audio (stereo to mono, keep original sample rate)
    y, sr = librosa.load(path, sr=None, mono=True)

    # Normalize volume
    y = y / np.max(np.abs(y))

    # Trim silence (optional, mainly for idle/max)
    y, _ = librosa.effects.trim(y, top_db=20)

    # Resample to target
    if sr != TARGET_SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)

    # Pad for looping (idle/max only)
    if "idle" in file_name or "max" in file_name:
        y = np.concatenate([y, y[:TARGET_SR//10]])  # ~100ms tail padding

    # Export cleaned mono file
    out_path = os.path.join(OUTPUT_DIR, file_name)
    sf.write(out_path, y, TARGET_SR)
    print(f"Saved cleaned audio to {out_path}\n")

for f in FILES:
    preprocess_audio(f)
