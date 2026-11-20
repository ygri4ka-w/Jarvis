"""Existing camera tests must never start a physical microphone."""
import pytest
from PySide6.QtCore import QObject, Signal, QTimer


class SilentVoice(QObject):
    recognized = Signal(str, float)
    partial = Signal(str)
    status = Signal(str)
    error = Signal(str)
    finished = Signal()
    def __init__(self, device=None, parent=None):
        super().__init__(parent)
    def start(self):
        pass
    def stop(self):
        QTimer.singleShot(0, self.finished.emit)
    def take_wave(self):
        return None


@pytest.fixture(autouse=True)
def isolate_microphone(monkeypatch, tmp_path):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    import jarvis_ui.window as window
    monkeypatch.setattr(window, 'VoiceWorker', SilentVoice)
    monkeypatch.setattr(window, 'input_devices', lambda: [])

