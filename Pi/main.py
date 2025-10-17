import sys
import signal
import os
import platform
from PySide6.QtCore import QCoreApplication, QThread, QMetaObject, Qt
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
    #IMPORT HERE SO THAT IF UI TEST IS RUN, THESE ARE NOT IMPORTED
    from workers import AudioWorker, HardwareWorker

    _print_startup_info()

    dashboard = dash.F1Dashboard("ui/dashboard_settings.ini")
    dashboard.enable_fullscreen()

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

    # Ensure workers are stopped on their own threads BEFORE we quit those threads.
    # Use BlockingQueuedConnection so the call is executed in the worker thread
    # and the main thread waits for completion. This avoids losing queued stop
    # events if thread.quit() is triggered first.
    def _stop_worker_and_quit_thread(worker, thread, name="worker"):
        def _handler():
            try:
                print(f"[Main] aboutToQuit: stopping {name}...")
                # Invoke stop on the worker on its thread and block until done
                QMetaObject.invokeMethod(worker, "stop", Qt.BlockingQueuedConnection)
            except Exception as exc:
                print(f"[Main] Failed to stop {name}: {exc}")
            try:
                print(f"[Main] aboutToQuit: quitting {name} thread...")
                thread.quit()
                # Wait a short time for clean shutdown; will block the main thread
                thread.wait(2000)
            except Exception as exc:
                print(f"[Main] Failed to quit {name} thread: {exc}")
        return _handler

    dashboard.app.aboutToQuit.connect(_stop_worker_and_quit_thread(hardware_worker, hardware_thread, "hardware"))
    dashboard.app.aboutToQuit.connect(_stop_worker_and_quit_thread(audio_worker, audio_thread, "audio"))

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
    # ui_test()