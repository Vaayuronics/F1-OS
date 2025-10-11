"""Qt worker threads for hardware and audio handling.

These workers replace the multiprocessing architecture that previously
consumed a significant amount of CPU time on the Raspberry Pi. They run
inside the Qt event loop so we can communicate via signals without the
serialization overhead of ``multiprocessing.Manager`` objects.
"""

from __future__ import annotations

import time
from typing import Dict, Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot

from devices.testerial import JSONSerialReader
from devices.light_manager import LightManager
import engine.soundsys as sound

MAX_RPM = 14000
MAX_THROTTLE_DEG = 135

def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))

class HardwareWorker(QObject):
    """Poll hardware and broadcast UI/audio updates."""

    ui_update = Signal(dict)
    sound_update = Signal(dict)
    status = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        poll_interval_s: float = 0.05,
        pico_port: str = "/dev/pico",
        arduino_port: str = "/dev/arduino",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._poll_interval_ms = int(poll_interval_s * 1000)
        self._pico_port = pico_port
        self._arduino_port = arduino_port

        self._pico: Optional[JSONSerialReader] = None
        self._arduino: Optional[JSONSerialReader] = None
        self._lights: Optional[LightManager] = None

        self._timer = QTimer(self)
        self._timer.setInterval(self._poll_interval_ms)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._poll)

        self._running = False

        self._gear = 0
        self._prev_rpm = 0.0
        self._prev_time = time.time()

        self._ui_state: Dict[str, float | int | str | bool] = {
            "Shift Emulation": False,
            "Headlights": False,
            "Hazards": False,
            "Auto Turn Signal": False,
            "DRS": False,
            "Started": False,
            "Engine Mute": False,
            "Music Mute": False,
            "Porche": False,
            "Pause": False,
            "RPM": 0.0,
            "Speed": 0.0,
            "Throttle": 0.0,
            "Engine Tune": 0.0,
            "Regen Brake": 0.0,
            "Engine Volume": 0,
            "Music Volume": 0,
            "Mode Switch": False,
            "Alert Title": "",
            "Alert Message": "",
            "Battery": 100,
        }
        self._sound_state: Dict[str, float | int | bool | None] = {
            "Accel": None,
            "Idle": True,
            "Play Speed": 1.0,
            "Engine Volume": 0,
            "Music Volume": 0,
            "Start": False,
            "Launch": False,
            "Horn": False,
            "Porche": False,
            "Change Track": False,
            "Pause": False,
        }

        self._last_ui_payload: Dict[str, float | int | str | bool] = {}
        self._last_sound_payload: Dict[str, float | int | bool | None] = {}

    @Slot()
    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self.status.emit("Hardware worker starting")

        try:
            self._pico = JSONSerialReader(self._pico_port)
            self._arduino = JSONSerialReader(self._arduino_port)
            self._lights = LightManager(
                [16, 6, 5, 7, 24, 23, 22, 27, 17],
                [
                    "Green 1",
                    "Green 2",
                    "Green 3",
                    "Green 4",
                    "Blue 1",
                    "Blue 2",
                    "Yellow",
                    "Orange",
                    "Red",
                ],
            )
            self._run_boot_animation()
        except Exception as exc:  # pragma: no cover - hardware may be absent in dev
            self.error.emit(f"Hardware init failed: {exc}")
            self._running = False
            return

        self._timer.start()

    @Slot()
    def stop(self) -> None:
        if not self._running:
            return

        self._running = False
        self._timer.stop()
        self.status.emit("Hardware worker stopping")
        self._cleanup()

    def _cleanup(self) -> None:
        if self._lights:
            try:
                self._lights.turn_off_all()
                self._lights.cleanup()
            except Exception as exc:  # pragma: no cover - best effort
                self.error.emit(f"Lights cleanup failed: {exc}")
        if self._pico:
            try:
                self._pico.ser.close()
            except Exception as exc:  # pragma: no cover - best effort
                self.error.emit(f"Pico cleanup failed: {exc}")
        if self._arduino:
            try:
                self._arduino.ser.close()
            except Exception as exc:  # pragma: no cover - best effort
                self.error.emit(f"Arduino cleanup failed: {exc}")

    def _run_boot_animation(self) -> None:
        if not self._lights:
            return
        time.sleep(1.0)
        for index in range(len(self._lights)):
            self._lights.turn_on(index)
            time.sleep(0.2)
        for _ in range(3):
            self._lights.toggle_all()
            time.sleep(0.2)
        self._lights.turn_off_all()

    def _poll(self) -> None:
        if not self._running:
            return

        try:
            pico_data = self._poll_pico()
            arduino_data = self._poll_arduino()
            self._process_inputs(pico_data, arduino_data)
        except Exception as exc:  # pragma: no cover - defensive
            self.error.emit(f"Hardware poll failed: {exc}")

    def _poll_pico(self) -> Optional[dict]:
        if not self._pico:
            return None
        return self._pico.poll()

    def _poll_arduino(self) -> Optional[dict]:
        if not self._arduino:
            return None
        return self._arduino.poll()

    def _process_inputs(self, pico_data: Optional[dict], arduino_data: Optional[dict]) -> None:
        consumables: list[str] = []

        if pico_data:
            consumables.extend(self._handle_pico_buttons(pico_data.get("Buttons", {})))
            consumables.extend(self._handle_pico_knobs(pico_data.get("Knobs", {})))

        if arduino_data and {"Throttle", "Speed", "Brake"}.issubset(arduino_data):
            accel, idle, play_speed, rpm = self._calculate_speed_rpm(
                arduino_data.get("Throttle", 0.0),
                arduino_data.get("Speed", 0.0),
                self._gear,
                self._prev_rpm,
                self._prev_time,
            )
            self._sound_state["Accel"] = accel
            self._sound_state["Idle"] = idle
            self._sound_state["Play Speed"] = play_speed
            self._ui_state["RPM"] = rpm
            self._ui_state["Speed"] = arduino_data.get("Speed", 0.0)
            self._ui_state["Throttle"] = _clamp(
                arduino_data.get("Throttle", 0.0) / MAX_THROTTLE_DEG,
                0.0,
                1.0,
            )
            self._prev_rpm = rpm
            self._prev_time = time.time()
            self._update_rpm_lights(rpm)

        if consumables:
            self._consume_press_states(consumables)

        self._emit_payloads()

    def _handle_pico_buttons(self, buttons: dict) -> list[str]:
        if not buttons:
            return []

        pressed_buttons = {
            name
            for name, payload in buttons.items()
            if payload.get("Press State") or payload.get("Pressed")
        }
        consumable_buttons = {
            name for name, payload in buttons.items() if payload.get("Press State")
        }

        def toggle_flag(key: str) -> bool:
            new_state = not bool(self._ui_state.get(key, False))
            self._ui_state[key] = new_state
            return new_state

        if "Shift Emulation Toggle" in pressed_buttons:
            new_state = toggle_flag("Shift Emulation")
            self._set_alert(
                f"Shift Emulation {'ON' if new_state else 'OFF'}",
                "Shift emulation mode has been toggled.",
            )

        if "Headlights" in pressed_buttons:
            new_state = toggle_flag("Headlights")
            self._ui_state["Hazards"] = False if new_state else self._ui_state["Hazards"]
            if self._lights:
                (self._lights.turn_on_all() if new_state else self._lights.turn_off_all())
            self._set_alert(
                f"Headlights {'ON' if new_state else 'OFF'}",
                "Headlights and backlights are toggled.",
            )

        if "Hazards" in pressed_buttons:
            new_state = toggle_flag("Hazards")
            if self._lights:
                (self._lights.toggle_all() if new_state else self._lights.turn_off_all())
            self._set_alert(
                f"Hazards {'ON' if new_state else 'OFF'}",
                "All lights are flashing.",
            )

        if "Change Engine" in pressed_buttons:
            new_state = toggle_flag("Porche")
            self._sound_state["Porche"] = new_state
            self._set_alert(
                "Engine Changed",
                f"Engine mode changed to {'Porche' if new_state else 'F1 v10'}.",
            )

        if "Change Music" in pressed_buttons:
            self._sound_state["Change Track"] = True

        if "DRS" in pressed_buttons:
            new_state = toggle_flag("DRS")
            self._set_alert(
                "DRS Changed",
                f"Drag Reduction System is now {'ACTIVE' if new_state else 'INACTIVE'}.",
            )

        start_pressed = "Start" in pressed_buttons
        start_btn = buttons.get("Start", {})
        if start_pressed and not self._ui_state["Started"]:
            self._ui_state["Started"] = True
            self._sound_state["Start"] = True
            self._set_alert("Car Started", "Car has been started.")
            if self._arduino:
                try:
                    self._arduino.send({"command": "tare"})
                except Exception as exc:  # pragma: no cover - best effort
                    self.error.emit(f"Failed to send tare command: {exc}")

        if start_btn.get("Down") and self._ui_state["Started"]:
            self._sound_state["Launch"] = True
        else:
            self._sound_state["Launch"] = False

        stop_pressed = "Stop" in pressed_buttons
        stop_btn = buttons.get("Stop", {})
        if stop_pressed:
            self._ui_state["Started"] = False
            self._sound_state["Start"] = False
            self._set_alert("Car Stopped", "Car has been turned off.")

        if "Play/Pause" in pressed_buttons:
            new_state = toggle_flag("Pause")
            self._sound_state["Pause"] = new_state

        if "Auto Turn Signal Toggle" in pressed_buttons:
            new_state = toggle_flag("Auto Turn Signal")
            self._set_alert(
                "Auto Turn Signal Changed",
                f"Auto turn signal is now {'ACTIVE' if new_state else 'INACTIVE'}.",
            )

        self._sound_state["Horn"] = bool(buttons.get("Horn", {}).get("Down"))

        return list(consumable_buttons)

    def _handle_pico_knobs(self, knobs: dict) -> list[str]:
        if not knobs:
            return []

        engine_knob = knobs.get("Engine Vol")
        pressed_knobs = {
            name
            for name, payload in knobs.items()
            if payload.get("Press State") or payload.get("Pressed")
        }
        consumable_knobs = {
            name for name, payload in knobs.items() if payload.get("Press State")
        }

        if engine_knob:
            if "Engine Vol" in pressed_knobs:
                new_state = not bool(self._ui_state.get("Engine Mute"))
                self._ui_state["Engine Mute"] = new_state
            if self._ui_state["Engine Mute"]:
                volume = 0
            else:
                volume = int(_clamp(engine_knob.get("Count", 0), 0, 100))
            self._ui_state["Engine Volume"] = volume
            self._sound_state["Engine Volume"] = volume

        music_knob = knobs.get("Music Vol")
        if music_knob:
            if "Music Vol" in pressed_knobs:
                new_state = not bool(self._ui_state.get("Music Mute"))
                self._ui_state["Music Mute"] = new_state
            if self._ui_state["Music Mute"]:
                volume = 0
            else:
                volume = int(_clamp(music_knob.get("Count", 0), 0, 100))
            self._ui_state["Music Volume"] = volume
            self._sound_state["Music Volume"] = volume

        tune_knob = knobs.get("Engine Tune")
        if tune_knob:
            if "Engine Tune" in pressed_knobs:
                self._ui_state["Mode Switch"] = True
            tune_value = _clamp(tune_knob.get("Count", 0) / 100.0, 0.0, 1.0)
            self._ui_state["Engine Tune"] = tune_value

        return list(consumable_knobs)

    def _calculate_speed_rpm(
        self,
        throttle_deg: float,
        speed_mph: float,
        gear: int,
        prev_rpm: float,
        prev_time: float,
    ) -> tuple[Optional[bool], bool, float, float]:
        accel = False
        play_speed = 1.0
        rpm = 0.0
        idle = False

        if gear == 0:
            rpm = throttle_deg * 103.7
        else:
            rpm = (speed_mph * 60 * gear * 10) + (throttle_deg * 50)

        if rpm <= 2000:
            idle = True

        rpm_change = rpm - prev_rpm
        if rpm_change >= 300:
            accel = True
        elif rpm_change <= -300:
            accel = False
        else:
            accel = None

        # Prevent play speed from diverging when device reports odd numbers
        play_speed = _clamp(((throttle_deg / MAX_THROTTLE_DEG) + 0.1), 0.2, 2.5)

        return accel, idle, play_speed, rpm

    def _update_rpm_lights(self, rpm: float) -> None:
        if not self._lights:
            return
        lights_count = len(self._lights)
        if lights_count == 0:
            return
        rpm_per_light = max((MAX_RPM - 100) / lights_count, 1)
        for index in range(lights_count):
            if rpm >= index * rpm_per_light:
                self._lights.turn_on(index)
            else:
                self._lights.turn_off(index)
        if rpm > MAX_RPM:
            self._lights.toggle(lights_count - 1)

    def _emit_payloads(self) -> None:
        ui_payload = dict(self._ui_state)
        sound_payload = dict(self._sound_state)

        # Clear one-shot flags so they only fire once per event
        ui_payload["Mode Switch"] = self._ui_state["Mode Switch"]
        self._ui_state["Mode Switch"] = False

        if ui_payload.get("Alert Title"):
            # Alert is one-shot as well
            self._ui_state["Alert Title"] = ""
            self._ui_state["Alert Message"] = ""

        if sound_payload.get("Start"):
            self._sound_state["Start"] = False
        if sound_payload.get("Change Track"):
            self._sound_state["Change Track"] = False

        if ui_payload != self._last_ui_payload:
            self.ui_update.emit(ui_payload)
            self._last_ui_payload = ui_payload

        if sound_payload != self._last_sound_payload:
            self.sound_update.emit(sound_payload)
            self._last_sound_payload = sound_payload

    def _set_alert(self, title: str, message: str) -> None:
        self._ui_state["Alert Title"] = title
        self._ui_state["Alert Message"] = message

    def _consume_press_states(self, names: list[str]) -> None:
        if not names or not self._pico:
            return
        try:
            self._pico.send({"command": "consume states", "buttons": sorted(set(names))})
        except Exception as exc:  # pragma: no cover - best effort
            self.error.emit(f"Failed to consume state for {names}: {exc}")

class AudioWorker(QObject):
    """Handle audio playback on a dedicated Qt thread."""

    error = Signal(str)
    status = Signal(str)

    def __init__(self, tick_interval_s: float = 0.05, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tick_interval_ms = int(tick_interval_s * 1000)
        self._timer = QTimer(self)
        self._timer.setInterval(self._tick_interval_ms)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._process_audio)

        self._state_defaults: Dict[str, float | int | bool | None] = {
            "Accel": None,
            "Idle": True,
            "Play Speed": 1.0,
            "Engine Volume": 100,
            "Music Volume": 100,
            "Start": False,
            "Launch": False,
            "Horn": False,
            "Porche": False,
            "Change Track": False,
            "Pause": False,
        }
        self._state: Dict[str, float | int | bool | None] = dict(self._state_defaults)
        self._running = False

    @Slot()
    def start(self) -> None:
        if self._running:
            return
        try:
            sound.load_tracks()
            sound.play_startup_sound()
        except Exception as exc:  # pragma: no cover - audio assets missing in dev
            self.error.emit(f"Audio init warning: {exc}")
        self._running = True
        self.status.emit("Audio worker starting")
        self._timer.start()

    @Slot()
    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._timer.stop()
        self.status.emit("Audio worker stopping")

    @Slot(dict)
    def apply_state(self, payload: dict) -> None:
        # Payload arrives on this thread thanks to queued signal delivery
        if not payload:
            return
        # Merge into baseline so timer keeps working when fields are omitted
        self._state.update(payload)

    def _process_audio(self) -> None:
        print("audio tick")
        if not self._running or self._state is None:
            print("audio tick skipped")
            return
        state = dict(self._state)
        print("audio chunk triggered")
        if state.pop("Start", False):
            try:
                sound.play_f1_start()
                sound.reset_curtime()
            except Exception as exc:  # pragma: no cover - best effort
                self.error.emit(f"Failed to play start sound: {exc}")

        if state.pop("Change Track", False):
            try:
                sound.change_track(sound.current_track() + 1)
            except Exception as exc:  # pragma: no cover - best effort
                self.error.emit(f"Failed to change track: {exc}")

        if state.get("Horn"):
            try:
                sound.play_horn()
            except Exception as exc:  # pragma: no cover - best effort
                self.error.emit(f"Failed to play horn: {exc}")

        if "Porche" in state:
            try:
                sound.set_porche_mode(bool(state["Porche"]))
            except Exception as exc:  # pragma: no cover - best effort
                self.error.emit(f"Failed to set engine mode: {exc}")

        try:
            sound.play_engine(
                state.get("Accel"),
                state.get("Play Speed", 1.0),
                int(state.get("Engine Volume", 0)),
                bool(state.get("Idle", False)),
            )
        except Exception as exc:  # pragma: no cover - best effort
            self.error.emit(f"Engine audio tick failed: {exc}")

    #TODO: Music playback left disabled as in original code (commented out)
