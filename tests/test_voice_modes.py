from time import monotonic
from PySide6.QtCore import QObject, Signal
from test_camera_ui import app


class ModeWorker(QObject):
    recognized = Signal(str, float)
    partial = Signal(str)
    status = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, device=None, language='ru', parent=None):
        super().__init__(parent)
        self.device, self.language = device, language
        self.stopped = False
        self.wave = None

    def start(self):
        self.status.emit('Очікує звернення')

    def stop(self):
        self.stopped = True

    def take_wave(self):
        wave, self.wave = self.wave, None
        return wave


def controller(running=True):
    from jarvis_voice.controller import VoiceController
    from jarvis_ui.voice_panel import VoicePanel
    from jarvis_ui.state import AssistantState
    from jarvis_commands.actions import ActionRunner
    actions = []
    voice = VoiceController(VoicePanel(), AssistantState(running=running), ModeWorker, lambda: [(7, 'Test')],
                            runner=ActionRunner(browse=lambda url: actions.append(url) or True))
    return voice, actions


def finish(voice):
    voice.stop()
    if voice.worker:
        voice.worker.finished.emit()


def test_microphone_test_isolated_from_old_normal_and_late_test_results(app):
    voice, actions = controller()
    results = []
    voice.test_result.connect(lambda text, action: results.append((text, action)))
    try:
        voice.start()
        normal = voice.worker
        voice.set_test_mode(True)
        assert normal.stopped
        normal.recognized.emit('джарвис открой браузер', monotonic())
        normal.finished.emit()
        test = voice.worker
        assert test is not normal
        test.partial.emit('джарвис открой браузер')
        assert not results
        test.recognized.emit('открой браузер', monotonic())
        assert results == [('открой браузер', 'browser')]
        assert not actions
        voice.set_test_mode(False)
        test.recognized.emit('джарвис открой браузер', monotonic())
        test.finished.emit()
        assert voice.worker is not test
        normal.recognized.emit('джарвис открой браузер', monotonic())
        test.recognized.emit('джарвис открой браузер', monotonic())
        assert not actions
        voice.worker.recognized.emit('джарвис открой браузер', monotonic())
        assert actions == ['https://www.google.com']
    finally:
        finish(voice)


def test_test_mode_works_while_assistant_stopped_and_does_not_start_normal(app):
    voice, actions = controller(False)
    results = []
    voice.test_result.connect(lambda *args: results.append(args))
    try:
        voice.set_language('en')
        voice.set_test_mode(True)
        assert voice.worker.language == 'en'
        voice.worker.recognized.emit('shut down computer', monotonic())
        assert results == [('shut down computer', 'shutdown')]
        voice.set_test_mode(False)
        voice.worker.finished.emit()
        assert voice.worker is None
        assert not actions
    finally:
        finish(voice)


def test_language_device_switch_and_stop_cancel_pending_restart(app):
    voice, actions = controller()
    try:
        voice.start()
        old = voice.worker
        voice.set_language('en')
        voice.set_device(7)
        old.recognized.emit('джарвис открой браузер', monotonic())
        old.finished.emit()
        assert voice.worker.language == 'en'
        assert voice.worker.device == 7
        voice.worker.recognized.emit('jarvis open browser', monotonic())
        assert actions == ['https://www.google.com']
        voice.set_language('ru')
        voice.stop()
        voice.worker.finished.emit()
        assert voice.worker is None
    finally:
        finish(voice)


def test_activity_and_amplitude_are_real_capture_events(app):
    voice, _ = controller()
    modes, levels, closed = [], [], []
    voice.activity.connect(modes.append)
    voice.level.connect(levels.append)
    voice.close_requested.connect(lambda: closed.append(True))
    try:
        voice.start()
        voice.worker.wave = [.1, .6, .2]
        voice.poll()
        assert levels[-1] == .6
        voice.worker.recognized.emit('джарвис закрой приложение', monotonic())
        assert closed == [True]
        assert 'processing' in modes and 'executing' in modes
        voice.worker.error.emit('Мікрофон втрачено')
        assert modes[-1] == 'error'
    finally:
        finish(voice)


def test_device_change_from_combo_invalidates_active_worker(app):
    voice, actions = controller()
    try:
        voice.start()
        old = voice.worker
        voice.panel.device_combo.setCurrentIndex(voice.panel.device_combo.findData(7))
        voice.set_device(7)
        assert old.stopped
        old.recognized.emit('джарвис открой браузер', monotonic())
        assert not actions
        old.finished.emit()
        assert voice.worker.device == 7
    finally:
        finish(voice)


def test_worker_passes_selected_language_to_recognizer(app):
    from jarvis_voice.worker import VoiceWorker
    from test_voice import FakeStream, FakeRecognizer
    import threading
    loaded = threading.Event()
    languages = []
    def recognizer(rate, language='ru'):
        languages.append(language)
        loaded.set()
        return FakeRecognizer()
    worker = VoiceWorker(language='en', source_factory=lambda device, inbox: (FakeStream(inbox.callback), 16000),
                         recognizer_factory=recognizer)
    try:
        worker.start()
        assert loaded.wait(2)
    finally:
        worker.stop()
        assert worker.wait(2000)
    assert languages == ['en']
