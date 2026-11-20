from test_camera_ui import app, until
from test_voice_ui import FakeVoice
from test_camera import FakeDevice


def test_core_reacts_to_amplitude_and_stops_hidden_timers(app):
    from jarvis_ui import animated_core
    core = animated_core.AnimatedCore()
    core.resize(380, 380)
    core.set_state('listening')
    core.set_animations(False)
    core.set_level(0)
    quiet = core.grab().toImage()
    core.set_level(.8)
    assert core.grab().toImage() != quiet
    core.show()
    core.set_animations(True)
    assert core.timer.isActive()
    core.hide()
    assert not core.timer.isActive()
    core.set_animations(False)
    core.show()
    assert not core.timer.isActive()
    core.close()


def test_modern_pages_and_microphone_independent_of_camera(app, tmp_path):
    from jarvis_ui.window import JarvisWindow
    from jarvis_settings import SettingsStore
    settings = SettingsStore(tmp_path / 'settings.json')
    window = JarvisWindow(voice_worker_factory=FakeVoice, device_provider=lambda: [],
                          capture_factory=lambda index: FakeDevice(), settings_store=settings)
    try:
        window.nav_buttons[1].click()
        assert window.pages.currentWidget() is window.command_manager
        window.nav_buttons[2].click()
        assert window.pages.currentWidget() is window.camera_panel
        window.nav_buttons[3].click()
        assert window.pages.currentWidget() is window.settings_panel
        window.mic_button.click()
        assert window.voice.worker is not None
        assert window.camera_worker is None
        window.mic_button.click()
        assert window.voice.worker.stopped
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: window.camera_worker is None)


def test_settings_restore_without_arming_gestures(app, tmp_path):
    from jarvis_ui.window import JarvisWindow
    from jarvis_settings import SettingsStore
    path = tmp_path / 'settings.json'
    settings = SettingsStore(path)
    settings.set('gesture_enabled', True)
    settings.set('language', 'en')
    window = JarvisWindow(voice_worker_factory=FakeVoice, device_provider=lambda: [], settings_store=settings)
    try:
        assert window.voice.language == 'en'
        assert not window.camera_panel.control_check.isChecked()
        window.settings_panel.animations.setChecked(False)
        window.settings_panel.wake_required.setChecked(False)
        assert SettingsStore(path).get('animations') is False
        assert SettingsStore(path).get('wake_required') is False
        assert not window.core.timer.isActive()
    finally:
        window.close()


def test_editor_saves_language_url_and_all_aliases(app, tmp_path):
    from jarvis_commands.store import CommandStore
    from jarvis_ui.command_editor import CommandEditor
    store = CommandStore(tmp_path / 'commands.json')
    dialog = CommandEditor(store, checker=lambda phrase: [])
    dialog.language.setCurrentIndex(dialog.language.findData('en'))
    dialog.action_type.setCurrentIndex(dialog.action_type.findData('url'))
    dialog.phrase.setText('open my notes')
    dialog.aliases.setPlainText('show my notes\nlaunch notes')
    dialog.exe.setText('https://example.com/notes')
    dialog.save_button.click()
    until(app, lambda: dialog.worker is None)
    assert store.items[0].language == 'en'
    assert store.items[0].phrases == ('open my notes', 'show my notes', 'launch notes')
    assert store.items[0].action_type == 'url'


def test_microphone_test_cancels_live_routing_and_late_results(app, tmp_path):
    from jarvis_ui.window import JarvisWindow
    from jarvis_commands.store import CommandStore
    window = JarvisWindow(voice_worker_factory=FakeVoice, device_provider=lambda: [],
                          command_store=CommandStore(tmp_path / 'commands.json'))
    window.show()
    try:
        window.mic_button.click()
        old = window.voice.worker
        window.nav_buttons[1].click()
        window.command_manager.test_button.click()
        assert window.voice.test_mode
        old.finished.emit()
        worker = window.voice.worker
        worker.recognized.emit('джарвис который час', 10)
        assert window.state.last_command == '—'
        assert 'который час' in window.command_manager.test_transcript.text()
        window.nav_buttons[0].click()
        assert not window.voice.test_mode
        worker.recognized.emit('джарвис открой браузер', 20)
        assert window.state.last_command == '—'
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: not window.isVisible())


def test_window_close_waits_for_dictionary_check_and_does_not_save(app, tmp_path):
    import threading
    from jarvis_ui.window import JarvisWindow
    from jarvis_ui.command_editor import CommandEditor
    from jarvis_commands.store import CommandStore
    from test_custom_commands import executable
    resume = threading.Event()
    store = CommandStore(tmp_path / 'commands.json')
    window = JarvisWindow(voice_worker_factory=FakeVoice, device_provider=lambda: [], command_store=store)
    editor = CommandEditor(store, parent=window.command_manager,
                           checker=lambda phrase: (resume.wait(2), [])[1])
    window.command_manager.editor = editor
    editor.phrase.setText('открой игру')
    editor.exe.setText(executable(tmp_path))
    window.show()
    try:
        editor.save()
        window.close()
        assert window.isVisible(), 'Window must retain ownership until dictionary worker stops'
        resume.set()
        until(app, lambda: editor.worker is None)
        until(app, lambda: not window.isVisible())
        assert not store.items
    finally:
        resume.set()
        until(app, lambda: editor.worker is None)
        window.close()


def test_tracking_and_control_opt_in_and_worker_owns_processor_close(app):
    import threading
    from jarvis_ui.window import JarvisWindow
    entered, resume = threading.Event(), threading.Event()
    class SlowDevice(FakeDevice):
        def read(self):
            entered.set()
            resume.wait(2)
            return super().read()
    class Processor:
        def __init__(self):
            self.tracking = self.control = self.closed = False
        def set_enabled(self, tracking, control):
            self.tracking, self.control = tracking, control
        def set_smoothing(self, value):
            pass
        def set_sensitivity(self, value):
            self.sensitivity = value
        def process(self, frame):
            return frame
        def snapshot(self):
            return dict(gesture='Долоня', tracking=self.tracking, control=self.control,
                        error='', landmarks=[], emergency_stopped=False)
        def close(self):
            self.closed = True
    processor = Processor()
    window = JarvisWindow(voice_worker_factory=FakeVoice, device_provider=lambda: [],
                          capture_factory=lambda index: SlowDevice(), gesture_processor_factory=lambda: processor)
    window.show()
    try:
        window.camera_panel.tracking_check.setChecked(True)
        window.camera_panel.toggle_button.click()
        until(app, entered.is_set)
        assert processor.tracking and not processor.control
        window.settings_panel.sensitivity.setValue(125)
        assert processor.sensitivity == 1.25
        assert window.settings.get('sensitivity') == 1.25
        window.camera_panel.control_check.setChecked(True)
        assert processor.control
        window.close()
        assert not processor.control
        assert not processor.closed
        resume.set()
        until(app, lambda: not window.isVisible())
        assert processor.closed
    finally:
        resume.set()
        window.close()
        until(app, lambda: window.camera_worker is None)


def test_microphone_off_during_test_does_not_resume_live_capture(app):
    from jarvis_ui.window import JarvisWindow
    window = JarvisWindow(voice_worker_factory=FakeVoice, device_provider=lambda: [])
    try:
        window.mic_button.click()
        old = window.voice.worker
        window.command_manager.test_button.click()
        old.finished.emit()
        test_worker = window.voice.worker
        window.mic_button.click()
        test_worker.finished.emit()
        assert not window.voice.test_mode
        assert window.voice.worker is None
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
