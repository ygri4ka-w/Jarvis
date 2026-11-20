"""GUI-thread voice routing with a fresh capture session at each mode boundary."""
from time import monotonic
from PySide6.QtCore import QObject, QTimer, Signal
from jarvis_commands.router import CommandGate
from jarvis_commands.actions import ActionRunner
from .languages import language_profile
from .worker import accepts_language


class VoiceController(QObject):
    changed = Signal()
    stopped = Signal()
    stop_requested = Signal()
    shutdown_requested = Signal()
    close_requested = Signal()
    activity = Signal(str)
    level = Signal(float)
    test_result = Signal(str, str)

    def __init__(self, panel, state, worker_factory, device_provider, parent=None, runner=None, command_store=None):
        super().__init__(parent)
        self.panel, self.state = panel, state
        self.worker_factory, self.device_provider = worker_factory, device_provider
        self.runner = runner or ActionRunner()
        self.command_store = command_store
        self.worker = None
        self.active = False
        self.failed = False
        self.language = 'ru'
        self.device = None
        self.wake_required = True
        self.test_mode = False
        self._resume_after_test = False
        self._restart_pending = False
        self._mode = 'idle'
        self._activity_until = 0.0
        self.gate = self._new_gate()
        self.last_wave = 0
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.poll)
        panel.retry_button.clicked.connect(self.start)
        panel.refresh_button.clicked.connect(self.refresh_devices)
        self.refresh_devices()

    def _new_gate(self, test=False):
        routes = self.command_store.routes(self.language) if self.command_store else None
        return CommandGate(routes, self.language, wake_required=False if test else self.wake_required)

    @property
    def waiting_text(self):
        if self.test_mode:
            return 'Тест мікрофона — дії не виконуються'
        if not self.wake_required:
            return 'Очікує команду'
        return 'Очікує «Jarvis»' if self.language == 'en' else 'Очікує «Джарвис»'

    def _activity(self, mode):
        if self._mode != mode:
            self._mode = mode
            self.activity.emit(mode)

    def reload_commands(self):
        self.gate = self._new_gate(test=self.test_mode)

    def set_language(self, code):
        language_profile(code)
        if self.language == code:
            return
        self.language = code
        self.reload_commands()
        if self.active or self._restart_pending:
            self._restart()

    def set_device(self, device):
        current = self.device
        self.device = device
        index = self.panel.device_combo.findData(device)
        if index < 0:
            self.panel.device_combo.addItem(f'Мікрофон {device} (недоступний)', device)
            index = self.panel.device_combo.count() - 1
        self.panel.device_combo.setCurrentIndex(index)
        if current != device and (self.active or self._restart_pending):
            self._restart()

    def set_wake_required(self, enabled):
        enabled = bool(enabled)
        if enabled == self.wake_required:
            return
        self.wake_required = enabled
        self.reload_commands()
        if self.active or self._restart_pending:
            self._restart()

    def set_test_mode(self, enabled):
        enabled = bool(enabled)
        if enabled == self.test_mode:
            return
        if enabled:
            self._resume_after_test = self.active or self._restart_pending
        self.test_mode = enabled
        resume = enabled or (self._resume_after_test and self.state.running)
        if not enabled:
            self._resume_after_test = False
        # Deactivate immediately, before requesting asynchronous worker shutdown.
        # Old queued signals fail current(); new mode starts only with a new stream.
        self._stop_capture(restart=resume)

    def _restart(self):
        self._stop_capture(restart=True)

    def refresh_devices(self):
        if self.worker is not None:
            return
        selected = self.panel.device_combo.currentData()
        self.panel.device_combo.clear()
        self.panel.device_combo.addItem('Типовий мікрофон Windows', None)
        try:
            for index, name in self.device_provider():
                self.panel.device_combo.addItem(name, index)
            found = self.panel.device_combo.findData(selected)
            if found >= 0:
                self.panel.device_combo.setCurrentIndex(found)
        except Exception:
            self.panel.status.setText('Не вдалося отримати список мікрофонів. Перевірте підключення та натисніть «Оновити».')

    def start(self):
        if not (self.state.running or self.test_mode) or self.worker is not None:
            return
        self._restart_pending = False
        self.active, self.failed = True, False
        self.reload_commands()
        self.state.microphone = 'Підключення…'
        self.state.voice = 'Завантаження моделі…'
        self.panel.status.setText(self.state.voice)
        self.panel.set_busy(True, True)
        self.panel.clear_wave()
        self.level.emit(0.0)
        self._activity('processing')
        kwargs = dict(device=self.panel.device_combo.currentData(), parent=self)
        self.device = kwargs['device']
        if accepts_language(self.worker_factory):
            kwargs['language'] = self.language
        try:
            self.worker = self.worker_factory(**kwargs)
            self.worker.status.connect(self.on_status)
            self.worker.recognized.connect(self.on_text)
            self.worker.partial.connect(self.on_partial)
            self.worker.error.connect(self.on_error)
            self.worker.finished.connect(self.on_finished)
            self.worker.start()
        except Exception as exc:
            self.active, self.failed = False, True
            self.worker = None
            self.state.microphone = self.state.voice = 'Помилка'
            self.panel.status.setText(f'Не вдалося запустити голосовий модуль: {exc}')
            self.panel.set_busy(False, self.state.running or self.test_mode)
            self._activity('error')
            self.changed.emit()
            return
        self.timer.start()
        self.changed.emit()

    def current(self):
        return self.active and not self.failed and self.sender() is self.worker

    def on_status(self, text):
        if not self.current():
            return
        if text.startswith('Очікує'):
            first_connection = self.state.microphone != 'Слухає'
            self.state.microphone = 'Слухає'
            if first_connection:
                self.state._add_event('Мікрофон підключено')
            text = self.waiting_text
            self._activity('listening')
        else:
            self._activity('processing')
        self.state.voice = text
        self.panel.status.setText(text)
        self.changed.emit()

    def on_partial(self, text):
        if self.current() and text:
            self.panel.transcript.setText(text)

    def on_text(self, text, captured_at):
        if not self.current() or not (self.state.running or self.test_mode):
            return
        self.panel.transcript.setText(text)
        self._activity('processing')
        if self.test_mode:
            # Each test utterance independently reports its match; never run it.
            decision = self._new_gate(test=True).accept(text, captured_at)
            self.test_result.emit(text, decision.command or '')
            self._activity('listening')
            self.changed.emit()
            return
        decision = self.gate.accept(text, captured_at)
        if decision.status == 'armed':
            self.gate.deadline = monotonic() + 5
        self.state.voice = 'Слухаю команду…' if decision.status == 'armed' else self.waiting_text
        self.panel.status.setText(self.state.voice)
        if decision.command:
            self._activity('executing')
            if decision.command.startswith('custom:'):
                item = self.command_store.get(decision.command.removeprefix('custom:')) if self.command_store else None
                if item is None:
                    self._activity('listening')
                    return
                if item.action_type == 'exe':
                    result = self.runner.execute_custom(item.target)
                else:
                    result = self.runner.execute_custom(item.target, action_type=item.action_type)
                phrase = item.phrase
            else:
                result = self.runner.execute(decision.command)
                phrase = next((key for key, value in language_profile(self.language)['commands'].items()
                               if value == decision.command), text)
            self.state.register_command(phrase)
            self.state._add_event(result.message)
            self.panel.result.setText(result.message)
            if not result.ok:
                self._activity('error')
            self._activity_until = monotonic() + .5
            if result.stop:
                self.stop_requested.emit()
            if result.shutdown:
                self.shutdown_requested.emit()
            if getattr(result, 'close', False):
                self.close_requested.emit()
        else:
            self._activity('listening')
            if decision.status == 'unknown':
                self.panel.result.setText('Команду не впізнано. Повторіть звернення та одну з доступних команд.')
                self.state._add_event('Голосову команду не впізнано')
        self.changed.emit()

    def poll(self):
        if not self.active or self.failed or self.worker is None:
            return
        now = monotonic()
        values = self.worker.take_wave()
        if values is not None:
            self.panel.show_wave(values)
            self.level.emit(float(min(1, max(values, default=0))))
            self.last_wave = now
        elif now - self.last_wave > .25:
            self.panel.clear_wave()
            self.level.emit(0.0)
        if self._activity_until and now >= self._activity_until:
            self._activity_until = 0
            self._activity('listening')
        if self.state.voice == 'Слухаю команду…' and not self.gate.armed(now):
            self.state.voice = self.waiting_text
            self.panel.status.setText(self.state.voice)
            self.changed.emit()

    def on_error(self, message):
        if not self.current():
            return
        self.failed = True
        self.state.microphone = self.state.voice = 'Помилка'
        self.panel.status.setText(message)
        self.panel.clear_wave()
        self.level.emit(0.0)
        self._activity('error')
        self.state._add_event(f'Помилка голосового модуля: {message}')
        self.changed.emit()

    def _stop_capture(self, restart=False):
        self.active = False
        self._restart_pending = bool(restart)
        self.timer.stop()
        self._activity_until = 0
        self.reload_commands()
        self.panel.clear_wave()
        self.level.emit(0.0)
        self.panel.set_busy(self.worker is not None, False)
        self.state.microphone = 'Зупинення…' if self.worker is not None else 'Вимкнений'
        self.state.voice = 'Вимкнений'
        self.panel.status.setText('Зупинення мікрофона…' if self.worker else 'Мікрофон вимкнено')
        self._activity('stopped')
        if self.worker is not None:
            self.worker.stop()
        elif self._restart_pending:
            self.start()
        self.changed.emit()

    def stop(self):
        self.test_mode = False
        self._resume_after_test = False
        self._stop_capture()

    def on_finished(self):
        if self.sender() is not self.worker:
            return
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.timer.stop()
        self.panel.clear_wave()
        self.level.emit(0.0)
        self.panel.set_busy(False, self.state.running or self.test_mode)
        if not self.failed:
            self.state.microphone = self.state.voice = 'Вимкнений'
            self.panel.status.setText('Мікрофон вимкнено')
        self.active = False
        if self._restart_pending and (self.state.running or self.test_mode):
            self.start()
            return
        self._restart_pending = False
        if not self.failed:
            self._activity('stopped')
        self.changed.emit()
        self.stopped.emit()
