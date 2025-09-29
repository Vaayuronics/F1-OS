import os 
import time
import json
from pydub import AudioSegment
import simpleaudio as sa


class EngineAudioSimulator:
    def __init__(self, base_path="sounds", timestamp_file="timestamps.json"):
        self.base_path = base_path
        self.timestamp_data = self._load_timestamps(os.path.join(base_path, timestamp_file))
        self.gear = 0  # Neutral
        self.power = 0.0
        self.current_audio = None
        self.play_obj = None
        self.play_start_time = None
        self.audio_start_offset = 0.0
        self.throttle_mode = 1
        self.current_audio_key = None
        self.current_file_name = None
        self.rev_mode = None  # None, "rev_small", "rev_full", "rev_loop"
        self.engine_on = False
        self.engine_transitioning = False
        self.last_toggle_time = 0.0

    def _load_timestamps(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
        for k, v in data.items():
            data[k] = {int(rpm): ts for rpm, ts in v.items()}
        return data

    def _get_throttle_mode(self, power):
        if power < 0.25:
            return 1
        elif power < 0.5:
            return 2
        elif power < 0.75:
            return 3
        else:
            return 4

    def _get_speed_from_power(self, power):
        throttle_mode = self._get_throttle_mode(power)
        base_min = (throttle_mode - 1) * 0.25 + 0.05
        base_max = throttle_mode * 0.25
        speed = (power - base_min) / (base_max - base_min)
        speed = max(0.75, min(1.0, speed))
        return speed, throttle_mode

    def _get_audio_path(self, *parts):
        return os.path.join(self.base_path, *parts)

    def play_audio(self, file_path, start_time=0.0, speed=1.0, loop=False):
        if self.play_obj:
            self.play_obj.stop()

        audio = AudioSegment.from_wav(file_path)
        if start_time > 0:
            audio = audio[start_time * 1000:]

        if speed != 1.0:
            new_frame_rate = int(audio.frame_rate * speed)
            audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
            audio = audio.set_frame_rate(44100)

        self.current_audio = audio
        self.audio_start_offset = start_time
        self.play_start_time = time.time()
        self.current_audio_key = os.path.relpath(file_path, self.base_path).replace("\\", "/")
        self.current_file_name = os.path.basename(file_path)

        self.play_obj = sa.play_buffer(
            audio.raw_data,
            num_channels=audio.channels,
            bytes_per_sample=audio.sample_width,
            sample_rate=audio.frame_rate
        )

    def _is_playing_done(self):
        return self.play_obj and not self.play_obj.is_playing()

    def _estimate_rpm_from_playback(self):
        if not self.play_start_time or not self.current_audio_key:
            return 4000
        elapsed = time.time() - self.play_start_time + self.audio_start_offset
        timestamps = self.timestamp_data.get(self.current_audio_key, {})
        sorted_rpms = sorted(timestamps.keys())
        for i in range(1, len(sorted_rpms)):
            prev_rpm = sorted_rpms[i - 1]
            next_rpm = sorted_rpms[i]
            prev_ts = timestamps[prev_rpm]
            next_ts = timestamps[next_rpm]
            if prev_ts <= elapsed < next_ts:
                ratio = (elapsed - prev_ts) / (next_ts - prev_ts)
                estimated_rpm = int(prev_rpm + (next_rpm - prev_rpm) * ratio)
                return estimated_rpm
        return sorted_rpms[-1]

    def toggle_engine(self, gear : int):
        current_time = time.time()
        self.gear = gear # Enable specifying a gear to start at

        if not self.engine_on:
            # Starting engine
            self.engine_on = True
            self.engine_transitioning = True
            self.last_toggle_time = current_time

            gear_label = "Neutral" if self.gear == 0 else "First"
            self.play_audio(self._get_audio_path(gear_label, "Start.wav"))

        else:
            # Stopping engine
            self.engine_on = False
            self.engine_transitioning = True
            self.last_toggle_time = current_time

            gear_label = "Neutral" if self.gear == 0 else "First"
            self.play_audio(self._get_audio_path(gear_label, "Stop.wav"))

    def update(self, power: float, gear: int, shifting=False):
        self.gear = gear

        # Handle startup/shutdown transition
        if self.engine_transitioning:
            if self._is_playing_done():
                self.engine_transitioning = False
                if self.engine_on:
                    gear_label = "Neutral" if self.gear == 0 else "First"
                    self.play_audio(self._get_audio_path(gear_label, "Idle.wav"), loop=True)
                else:
                    self.stop()
            return

        # Skip all logic if engine is off
        if not self.engine_on:
            return

        speed, throttle_mode = self._get_speed_from_power(power)
        direction = "accel" if not shifting else "decel"

        # Idle logic
        if power < 0.05:
            if gear == 0 and self.current_file_name != "Idle.wav":
                self.play_audio(self._get_audio_path("Neutral", "Idle.wav"), loop=True)
                return
            elif gear == 1 and self.current_file_name != "Idle.wav":
                self.play_audio(self._get_audio_path("First", "Idle.wav"), loop=True)
                return

        # Neutral rev logic
        if gear == 0 and power > 0.05:
            if power > 0.5:
                if self.rev_mode != "rev_full":
                    self.play_audio(self._get_audio_path("Neutral", "Rev Full.wav"))
                    self.rev_mode = "rev_full"
                elif self.rev_mode == "rev_full" and self._is_playing_done():
                    self.play_audio(self._get_audio_path("Neutral", "Full.wav"), loop=True)
                    self.rev_mode = "rev_loop"
                return
            else:
                if self.rev_mode != "rev_small":
                    self.play_audio(self._get_audio_path("Neutral", "Rev Small.wav"))
                    self.rev_mode = "rev_small"
                return
        else:
            self.rev_mode = None

        # Acceleration/deceleration shifting logic
        if shifting:
            last_rpm = self._estimate_rpm_from_playback()
            if gear > self.gear:
                target_rpm = max(4000, last_rpm - 1000)
            else:
                target_rpm = min(18000, last_rpm + 1000)
            target_rpm = (target_rpm // 1000) * 1000
            new_path = self._get_audio_path(f"throttle_{throttle_mode}", direction, f"gear_{gear}.wav")
            key = os.path.relpath(new_path, self.base_path).replace("\\", "/")

            # changed code: default to highest rpm timestamp if target_rpm not found
            timestamps = self.timestamp_data.get(key, {})
            if timestamps:
                if target_rpm in timestamps:
                    start_time = timestamps[target_rpm]
                else:
                    max_rpm = max(timestamps.keys())
                    start_time = timestamps[max_rpm]
            else:
                start_time = 0.0

            self.play_audio(new_path, start_time, speed)
        else:
            if gear != self.gear or throttle_mode != self.throttle_mode:
                new_path = self._get_audio_path(f"throttle_{throttle_mode}", "accel", f"gear_{gear}.wav")
                self.play_audio(new_path, 0.0, speed)

        self.power = power
        self.throttle_mode = throttle_mode

    def stop(self):
        if self.play_obj:
            self.play_obj.stop()
            self.play_obj = None