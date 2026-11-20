import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import numpy as np
from PySide6.QtCore import QObject, Signal
from test_camera_ui import app, until
from test_camera import FakeDevice


class FakeVoice(QObject):
    recognized = Signal(str, float)
    partial = Signal(str)
    status = Signal(str)
    error = Signal(str)
    finished = Signal()
    def __init__(self, device=None, parent=None):
        super().__init__(parent)
        self.wave = None
        self.stopped = False
    def start(self):
        self.status.emit('Очікує «Джарвіс»')
    def stop(self):
        self.stopped = True
    def take_wave(self):
        wave, self.wave = self.wave, None
        return wave


def make_window():
    from jarvis_ui.window import JarvisWindow
    return JarvisWindow(capture_factory=lambda index: FakeDevice(),
                        voice_worker_factory=FakeVoice, device_provider=lambda: [(7, 'Test microphone')])


def test_voice_navigation_wave_time_command_and_joint_close(app):
    window = make_window()
    window.show()
    worker = None
    try:
        window.nav_buttons[0].click()
        assert window.pages.currentWidget() is window.home_page
        window.toggle_button.click()
        worker = window.voice.worker
        worker.wave = [.1, .4, .2] * 26
        window.voice.poll()
        assert max(window.voice_panel.waveform.values) == .4
        worker.recognized.emit('который час', __import__('time').monotonic())
        assert window.state.last_command == '—'
        worker.recognized.emit('джарвіс который час', __import__('time').monotonic())
        assert 'Зараз' in window.voice_panel.result.text()
        window.close()
        assert window.isVisible()
        assert worker.stopped
        worker.finished.emit()
        until(app, lambda: not window.isVisible())
        assert max(window.voice_panel.waveform.values) == 0
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: window.camera_worker is None)


def test_voice_error_does_not_stop_camera_and_retry_discards_old_signals(app):
    window = make_window()
    try:
        window.toggle_button.click()
        until(app, lambda: window.state.camera == 'Активна')
        old = window.voice.worker
        old.error.emit('Мікрофон відключено')
        old.finished.emit()
        assert window.state.camera == 'Активна'
        assert window.state.microphone == 'Помилка'
        window.voice_panel.retry_button.click()
        current = window.voice.worker
        assert current is not old
        old.recognized.emit('джарвіс останови ассистента', __import__('time').monotonic())
        assert window.state.running
        current.recognized.emit('джарвіс останови ассистента', __import__('time').monotonic())
        assert not window.state.running
        current.recognized.emit('джарвіс который час', __import__('time').monotonic())
        assert window.state.last_command == 'останови ассистента'
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: window.camera_worker is None)


def test_waveform_changes_render_with_pcm_and_resets(app, tmp_path):
    from jarvis_ui.waveform import Waveform
    from jarvis_voice.audio import waveform
    widget = Waveform()
    widget.resize(600, 180)
    silent = widget.grab().toImage()
    pcm = (np.sin(np.arange(3200) / 10) * np.linspace(0, 20000, 3200)).astype('<i2').tobytes()
    widget.set_levels(waveform(pcm))
    loud = widget.grab().toImage()
    assert silent != loud
    widget.clear()
    assert widget.grab().toImage() == silent


def test_voice_visual_preview(app, tmp_path):
    from jarvis_ui.theme import APP_STYLESHEET
    app.setStyleSheet(APP_STYLESHEET)
    window = make_window()
    window.show()
    try:
        window.nav_buttons[0].click()
        window.toggle_button.click()
        from jarvis_voice.audio import waveform
        pcm = (np.sin(np.arange(3200) / 5) * (1000 + 9000 * np.sin(np.arange(3200) / 450)**2)).astype('<i2').tobytes()
        window.voice.worker.wave = waveform(pcm)
        window.voice.poll()
        window.voice.worker.recognized.emit('джарвіс который час', __import__('time').monotonic())
        app.processEvents()
        assert window.grab().save(str(tmp_path / 'voice-preview.png'))
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: window.camera_worker is None)


def test_real_worker_signals_reach_ui_without_running_actions_from_partial(app):
    from jarvis_ui.window import JarvisWindow
    from jarvis_voice.worker import VoiceWorker
    from test_voice import FakeStream, FakeRecognizer
    def factory(device=None, parent=None):
        return VoiceWorker(device=device, parent=parent,
                           source_factory=lambda device, inbox: (FakeStream(inbox.callback), 16000),
                           recognizer_factory=lambda rate: FakeRecognizer())
    window = JarvisWindow(capture_factory=lambda index: FakeDevice(),
                         voice_worker_factory=factory, device_provider=lambda: [])
    try:
        window.toggle_button.click()
        until(app, lambda: 'Зараз' in window.voice_panel.result.text())
        assert window.state.microphone == 'Слухає'
        assert window.state.last_command == 'который час'
    finally:
        window.close()
        until(app, lambda: window.camera_worker is None and window.voice.worker is None)


def test_command_deadline_uses_speech_start_not_delayed_transcription(app, monkeypatch):
    import jarvis_voice.controller as controller
    now = [10.0]
    monkeypatch.setattr(controller, 'monotonic', lambda: now[0])
    window = make_window()
    try:
        window.toggle_button.click()
        worker = window.voice.worker
        worker.recognized.emit('джарвіс', 1.0)
        assert window.voice.gate.deadline == 15
        now[0] = 25
        worker.recognized.emit('который час', 14.0)
        assert window.state.last_command == 'который час'
        worker.recognized.emit('джарвіс', 20.0)
        now[0] = 40
        worker.recognized.emit('открой браузер', 31.0)
        assert window.state.last_command == 'который час'
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: window.camera_worker is None)



