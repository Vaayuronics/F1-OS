import os
import time
import json
from pydub import AudioSegment
AudioSegment.converter = "C:/Users/Kp101/ffmpeg"
import simpleaudio as sa

class SimpleEngineAudio:
    def __init__(self, base_path="sounds2", timestamp_file="timestamps.json"):
        self.base_path = base_path
        self.timestamps = self._load_timestamps(os.path.join(base_path, timestamp_file))
        self.gear_ratios = [1.8, 1.6, 1.4, 1.2, 1.1, 1.05, 1.0]  # 1st to 7th gear
        self.current_audio = None
        self.play_obj = None
        self.start_time = None
        self.audio_key = None
        self.audio_offset = 0.0
        self.current_gear = 0
        self.last_mph = 0

    def _load_timestamps(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        return {k: {int(rpm): ts for rpm, ts in v.items()} for k, v in data.items()}

    def _get_audio_path(self, filename):
        return os.path.join(self.base_path, filename)

    def _play(self, key, start_time=0.0, speed=1.0, loop=False):
        if self.play_obj:
            self.play_obj.stop()

        file_path = self._get_audio_path(f"{key}.wav")
        audio = AudioSegment.from_wav(file_path)

        if start_time > 0:
            audio = audio[start_time * 1000:]

        if speed != 1.0:
            new_rate = int(audio.frame_rate * speed)
            audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
            audio = audio.set_frame_rate(44100)

        self.current_audio = audio
        self.audio_key = key
        self.audio_offset = start_time
        self.start_time = time.time()

        self.play_obj = sa.play_buffer(
            audio.raw_data,
            num_channels=audio.channels,
            bytes_per_sample=audio.sample_width,
            sample_rate=audio.frame_rate
        )

    def _is_done(self):
        return self.play_obj and not self.play_obj.is_playing()

    def _estimate_rpm(self):
        if not self.start_time or not self.audio_key:
            return 4000
        elapsed = time.time() - self.start_time + self.audio_offset
        ts = self.timestamps.get(self.audio_key, {})
        rpms = sorted(ts.keys())
        for i in range(1, len(rpms)):
            r0, r1 = rpms[i - 1], rpms[i]
            t0, t1 = ts[r0], ts[r1]
            if t0 <= elapsed < t1:
                ratio = (elapsed - t0) / (t1 - t0)
                return int(r0 + (r1 - r0) * ratio)
        return rpms[-1]

    def update(self, throttle: float, gear: int, mph: float):
        gear = max(1, min(gear, 7))
        ratio = self.gear_ratios[gear - 1]
        rpm = self._estimate_rpm()
        speed = ratio

        if throttle > 0.95 and self.audio_key == "accel" and self._is_done():
            self._play("max_rpm", loop=True)
            return

        if throttle < 0.05:
            if self.audio_key != "idle":
                self._play("idle", loop=True)
            return

        if mph < self.last_mph - 0.5:  # Decelerating
            ts = self.timestamps["decel"]
            rpm = max(4000, min(18000, rpm))
            start = ts.get(rpm, 0.0)
            self._play("decel", start_time=start, speed=speed)
        elif gear != self.current_gear:
            delta = 2000 * (-1 if gear > self.current_gear else 1)
            rpm = max(4000, min(18000, rpm + delta))
            start = self.timestamps["accel"].get(rpm, 0.0)
            self._play("accel", start_time=start, speed=speed)
        elif self.audio_key != "accel":
            self._play("accel", start_time=0.0, speed=speed)

        self.current_gear = gear
        self.last_mph = mph
