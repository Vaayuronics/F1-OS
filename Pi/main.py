import sys
import signal
import os
import platform
from PySide6.QtCore import QCoreApplication, QThread
import ui.dashboard as dash

def _print_startup_info() -> None:
    print(f"[Main] Python {platform.python_version()} on {platform.platform()}")
    print(f"[Main] PID {os.getpid()} starting F1-OS dashboard")


def _install_signal_handlers(app: QCoreApplication) -> None:
    def _handle_signal(signum, frame):
        print("\n[Main] Interrupt received. Closing application...")
        app.quit()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


def boot() -> None:
    from workers import AudioWorker, HardwareWorker
    _print_startup_info()

    dashboard = dash.F1Dashboard("ui/dashboard_settings.ini")

    hardware_thread = QThread()
    audio_thread = QThread()

    hardware_worker = HardwareWorker()
    audio_worker = AudioWorker()

    hardware_worker.moveToThread(hardware_thread)
    audio_worker.moveToThread(audio_thread)

    hardware_thread.started.connect(hardware_worker.start)
    audio_thread.started.connect(audio_worker.start)

    hardware_thread.finished.connect(hardware_worker.deleteLater)
    audio_thread.finished.connect(audio_worker.deleteLater)

    hardware_worker.ui_update.connect(dashboard.update_from_data)
    hardware_worker.sound_update.connect(audio_worker.apply_state)

    hardware_worker.status.connect(lambda msg: print(f"[Hardware] {msg}"))
    hardware_worker.error.connect(lambda msg: print(f"[Hardware] ERROR: {msg}"))
    audio_worker.status.connect(lambda msg: print(f"[Audio] {msg}"))
    audio_worker.error.connect(lambda msg: print(f"[Audio] ERROR: {msg}"))

    dashboard.app.aboutToQuit.connect(hardware_worker.stop)
    dashboard.app.aboutToQuit.connect(audio_worker.stop)
    dashboard.app.aboutToQuit.connect(hardware_thread.quit)
    dashboard.app.aboutToQuit.connect(audio_thread.quit)

    hardware_thread.start()
    audio_thread.start()

    _install_signal_handlers(dashboard.app)

    try:
        exit_code = dashboard.run()
    finally:
        hardware_thread.wait()
        audio_thread.wait()

    sys.exit(exit_code)

def ui_test() -> None:
    _print_startup_info()
    dashboard = dash.F1Dashboard("ui/dashboard_settings.ini")
    _install_signal_handlers(dashboard.app)
    dashboard.enable_fullscreen()
    exit_code = dashboard.run()
    sys.exit(exit_code)

if __name__ == "__main__":
    boot()
    #ui_test()