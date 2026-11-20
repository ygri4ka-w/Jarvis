"""Ukrainian desktop shell. Device ownership and stopping remain explicit."""
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QPushButton, QVBoxLayout, QWidget, QStackedWidget, QMessageBox, QScrollArea
from PySide6.QtGui import QShortcut, QKeySequence
from .state import AssistantState
from .ui_spec import NAV_ITEMS
from .animated_core import AnimatedCore
from .camera_panel import CameraPanel
from .voice_panel import VoicePanel
from .command_manager import CommandManager
from .settings_panel import SettingsPanel
from .theme import APP_STYLESHEET
from .icons import navigation_icon
from jarvis_camera.worker import CameraWorker
from jarvis_voice.worker import VoiceWorker
from jarvis_voice.audio import input_devices
from jarvis_voice.controller import VoiceController
from jarvis_voice.languages import language_profiles
from jarvis_commands.store import CommandStore
from jarvis_commands.power import request_shutdown
from jarvis_settings import SettingsStore
from jarvis_gestures import GestureProcessor


class JarvisWindow(QMainWindow):
    def __init__(self, capture_factory=None, voice_worker_factory=None, device_provider=None,
                 command_store=None, settings_store=None, gesture_processor_factory=None):
        super().__init__()
        self.state = AssistantState()
        self.command_store = command_store if command_store is not None else CommandStore()
        self.settings = settings_store if settings_store is not None else SettingsStore()
        self.capture_factory = capture_factory
        self.gesture_factory = gesture_processor_factory or GestureProcessor
        self.gesture_processor = None
        self.camera_worker = None
        self._closing = self._camera_failed = self._shutdown_prompt = False
        self._camera_requested = False
        self.nav_buttons, self.status_cards = [], {}
        self.setWindowTitle('JARVIS — Особистий асистент')
        self.setStyleSheet(APP_STYLESHEET)
        self.resize(1280, 820)
        self.setMinimumSize(1040, 720)
        self._build_ui()
        self.frame_timer = QTimer(self)
        self.frame_timer.setInterval(40)
        self.frame_timer.timeout.connect(self._poll_frame)
        self.voice = VoiceController(self.voice_panel, self.state, voice_worker_factory or VoiceWorker,
                                     device_provider or input_devices, self, command_store=self.command_store)
        self.voice.changed.connect(self._refresh)
        self.voice.stopped.connect(self._workers_finished)
        self.voice.stop_requested.connect(self._stop_assistant)
        self.voice.shutdown_requested.connect(self.shutdown_by_voice)
        self.voice.close_requested.connect(self.close)
        self.voice.activity.connect(self.core.set_state)
        self.voice.level.connect(self.core.set_level)
        self.voice.test_result.connect(self.command_manager.show_test_result)
        self.voice.set_language(self.settings.get('language', 'ru'))
        self.voice.set_wake_required(self.settings.get('wake_required', True))
        device = self.settings.get('microphone')
        found = self.voice_panel.device_combo.findData(device)
        if found >= 0:
            self.voice_panel.device_combo.setCurrentIndex(found)
        self.voice.set_device(device)
        self.camera_panel.device_index.setValue(self.settings.get('camera', 0))
        self.camera_panel.tracking_check.setChecked(self.settings.get('tracking_enabled', False))
        # OS input is an explicit opt-in each session, irrespective of persisted preference.
        self.camera_panel.control_check.setChecked(False)
        self.camera_panel.control_check.setEnabled(self.camera_panel.tracking_check.isChecked())
        self.core.set_animations(self.settings.get('animations', True))
        self.camera_panel.retry_button.clicked.connect(self._start_camera)
        self.camera_panel.toggle_button.clicked.connect(self._toggle_camera)
        self.camera_panel.tracking_check.toggled.connect(self._gesture_options)
        self.camera_panel.control_check.toggled.connect(self._gesture_options)
        self.settings_panel.changed.connect(self._setting_changed)
        self.command_manager.commands_changed.connect(self.commands_changed)
        self.command_manager.launch_requested.connect(self.test_custom_command)
        self.command_manager.test_requested.connect(self.voice.set_test_mode)
        self.command_manager.idle.connect(self._workers_finished)
        self.voice_panel.add_command_button.clicked.connect(self.command_manager.add)
        self.voice_panel.manage_commands_button.clicked.connect(lambda: self._show_page(1))
        self.voice_panel.shutdown_button.clicked.connect(self.confirm_shutdown)
        self.escape_shortcut = QShortcut(QKeySequence('Escape'), self)
        self.escape_shortcut.activated.connect(self._emergency_stop)
        self._update_language()
        self.state._add_event('JARVIS готовий до роботи')
        self._refresh()

    def _build_ui(self):
        root = QFrame()
        root.setObjectName('rootFrame')
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(190)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 30, 20, 24)
        brand = QLabel('JARVIS')
        brand.setObjectName('brand')
        side.addWidget(brand)
        sub = QLabel('ОСОБИСТИЙ АСИСТЕНТ')
        sub.setObjectName('brandSub')
        side.addWidget(sub)
        side.addSpacing(44)
        for index, item in enumerate(NAV_ITEMS):
            button = QPushButton('  ' + item.label)
            button.setIcon(navigation_icon(index, index == 0))
            button.setIconSize(QSize(18, 18))
            button.setObjectName('navButton')
            button.setProperty('active', index == 0)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page=index: self._show_page(page))
            self.nav_buttons.append(button)
            side.addWidget(button)
        side.addStretch()
        footer = QLabel('●  ЛОКАЛЬНА СИСТЕМА\n\nГолос · зір · керування')
        footer.setObjectName('brandSub')
        side.addWidget(footer)
        row.addWidget(sidebar)
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(28, 28, 28, 20)
        outer.setSpacing(16)
        header = QHBoxLayout()
        headings = QVBoxLayout()
        self.page_title = QLabel('Центр керування')
        self.page_title.setObjectName('pageTitle')
        headings.addWidget(self.page_title)
        self.page_subtitle = QLabel('Ваш голос. Ваші команди. Ваш простір.')
        self.page_subtitle.setObjectName('pageSubtitle')
        headings.addWidget(self.page_subtitle)
        header.addLayout(headings, 1)
        self.system_label = QLabel('●  ОЧІКУВАННЯ')
        self.system_label.setObjectName('commandLabel')
        header.addWidget(self.system_label)
        outer.addLayout(header)
        self.pages = QStackedWidget()
        self.home_page = QWidget()
        home = QHBoxLayout(self.home_page)
        home.setContentsMargins(0, 0, 0, 0)
        home.setSpacing(20)
        left = QVBoxLayout()
        left.setSpacing(12)
        self.core = AnimatedCore()
        left.addWidget(self.core, 1)
        self.voice_panel = VoicePanel()
        left.addWidget(self.voice_panel)
        home.addLayout(left, 3)
        right = QVBoxLayout()
        self.device_summary = QLabel('Мікрофон вимкнено\nКамера вимкнена')
        self.device_summary.setWordWrap(True)
        self.device_summary.setObjectName('pageSubtitle')
        right.addWidget(self.device_summary)
        right.addWidget(self._build_log_panel(), 1)
        last = QFrame()
        last.setObjectName('commandPanel')
        last_layout = QVBoxLayout(last)
        label = QLabel('ОСТАННЯ КОМАНДА')
        label.setObjectName('commandLabel')
        last_layout.addWidget(label)
        self.command_text = QLabel('—')
        self.command_text.setWordWrap(True)
        self.command_text.setObjectName('commandText')
        last_layout.addWidget(self.command_text)
        self.command_quote = QLabel('Результати зберігаються у журналі подій')
        self.command_quote.setObjectName('pageSubtitle')
        self.command_quote.setWordWrap(True)
        last_layout.addWidget(self.command_quote)
        right.addWidget(last)
        home.addLayout(right, 2)
        self.pages.addWidget(self.home_page)
        self.command_manager = CommandManager(self.command_store)
        self.pages.addWidget(self.command_manager)
        self.camera_panel = CameraPanel()
        self.pages.addWidget(self.camera_panel)
        self.settings_panel = SettingsPanel(self.settings, self.voice_panel, self.camera_panel)
        self.pages.addWidget(self.settings_panel)
        outer.addWidget(self.pages, 1)
        controls = QHBoxLayout()
        self.toggle_button = QPushButton('Запустити асистента')
        self.toggle_button.setObjectName('primaryButton')
        self.toggle_button.clicked.connect(self._toggle_assistant)
        controls.addWidget(self.toggle_button, 1)
        self.mic_button = QPushButton('Увімкнути мікрофон')
        self.mic_button.clicked.connect(self._toggle_microphone)
        controls.addWidget(self.mic_button)
        outer.addLayout(controls)
        row.addWidget(content, 1)
        self.statusBar().showMessage('Офлайн · Дані залишаються на цьому комп’ютері')

    def _build_log_panel(self):
        panel = QFrame()
        panel.setObjectName('logPanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 10)
        header = QHBoxLayout()
        title = QLabel('Журнал подій')
        title.setObjectName('sectionTitle')
        header.addWidget(title)
        header.addStretch()
        clear = QPushButton('Очистити')
        clear.setObjectName('clearButton')
        clear.clicked.connect(self._clear_events)
        header.addWidget(clear)
        layout.addLayout(header)
        self.event_list = QListWidget()
        self.event_list.setObjectName('eventList')
        self.event_list.setWordWrap(True)
        self.event_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.event_list)
        return panel

    def _show_page(self, index):
        if index != 1:
            self.command_manager.end_test()
        self.pages.setCurrentIndex(index)
        titles = ('Центр керування', 'Команди', 'Камера та жести', 'Налаштування')
        subtitles = ('Ваш голос. Ваші команди. Ваш простір.', 'Керуйте діями та перевіряйте голосові фрази.',
                     'Відео й відстеження руки обробляються локально.', 'Мова, пристрої та поведінка асистента.')
        self.page_title.setText(titles[index])
        self.page_subtitle.setText(subtitles[index])
        for i, button in enumerate(self.nav_buttons):
            button.setProperty('active', i == index)
            button.setIcon(navigation_icon(i, i == index))
            button.style().unpolish(button)
            button.style().polish(button)

    def _save_setting(self, key, value):
        try:
            self.settings.set(key, value)
            return True
        except (ValueError, OSError) as exc:
            self.settings_panel.message.setText(f'Не вдалося зберегти налаштування: {exc}')
            return False

    def _setting_changed(self, key, value):
        self._save_setting(key, value)
        if key == 'language':
            self.command_manager.end_test()
            self.voice.set_language(value)
            self._update_language()
        elif key == 'microphone':
            self.voice.set_device(value)
        elif key == 'wake_required':
            self.voice.set_wake_required(value)
        elif key == 'animations':
            self.core.set_animations(value)
        elif key == 'smoothing' and self.gesture_processor:
            self.gesture_processor.set_smoothing(value)
        elif key == 'sensitivity' and self.gesture_processor:
            self.gesture_processor.set_sensitivity(value)

    def _update_language(self):
        language = self.voice.language
        self.command_manager.set_language(language)
        self.voice_panel.transcript.setText('Скажіть: «Jarvis, what time is it»' if language == 'en' else 'Скажіть: «Джарвис, который час»')
        from jarvis_voice.recognition import model_path
        path = model_path(language=language)
        ready = (path / 'am' / 'final.mdl').is_file()
        self.settings_panel.model_status.setText(('Готова · ' if ready else 'Не знайдено · ') + language_profiles()[language]['model'])
        self.statusBar().showMessage('Офлайн · Голос: ' + language_profiles()[language]['label'] + ' · Інтерфейс: українська')

    def commands_changed(self):
        self.voice.reload_commands()
        self.command_manager.refresh()
        self.state._add_event('Список команд оновлено')
        self._refresh()

    def test_custom_command(self, item_id):
        item = self.command_store.get(item_id)
        if item:
            result = self.voice.runner.execute_custom(item.target, action_type=item.action_type)
            self.command_manager.message.setText(result.message)
            self.state._add_event(result.message)
            self._refresh()

    def _toggle_assistant(self):
        if self.state.running:
            self._stop_assistant()
        else:
            self.command_manager.end_test()
            self.state.start()
            self._start_camera()
            self.voice.start()
        self._refresh()

    def _toggle_microphone(self):
        was_active = self.voice.active or self.voice.test_mode
        self.command_manager.end_test()
        if was_active:
            self.voice.stop()
        elif self.voice.worker is None and not self._closing:
            if not self.state.running:
                self.state.start()
                self.state.camera = 'Готова'
            self.voice.start()
        self._refresh()

    def _toggle_camera(self):
        if self._camera_requested:
            self._stop_camera()
        elif self.camera_worker is None:
            if not self.state.running:
                self.state.start()
            self._start_camera()
        self._refresh()

    def _stop_assistant(self):
        self.command_manager.end_test()
        self.state.stop()
        self._stop_camera()
        self.voice.stop()
        self._workers_finished()
        self._refresh()

    def _workers_finished(self):
        busy = self.camera_worker is not None or self.voice.worker is not None or self.command_manager.editor_busy()
        self.toggle_button.setEnabled(not self._closing and (self.state.running or not busy))
        self.mic_button.setEnabled(not self._closing and (self.voice.active or self.voice.worker is None))
        if self._closing and not busy:
            QTimer.singleShot(0, self.close)

    def _start_camera(self):
        if not self.state.running or self.camera_worker is not None or self._closing:
            return
        self._camera_failed = False
        self._camera_requested = True
        self.state.camera = 'Підключення…'
        self.camera_panel.show_message('Підключення до камери…')
        self.camera_panel.device_index.setEnabled(False)
        self.camera_panel.retry_button.setEnabled(False)
        self.gesture_processor = self.gesture_factory()
        self.gesture_processor.set_smoothing(self.settings.get('smoothing', .25))
        if hasattr(self.gesture_processor, 'set_sensitivity'):
            self.gesture_processor.set_sensitivity(self.settings.get('sensitivity', 1.0))
        self.gesture_processor.set_enabled(self.camera_panel.tracking_check.isChecked(), self.camera_panel.control_check.isChecked())
        kwargs = {} if self.capture_factory is None else {'capture_factory': self.capture_factory}
        worker = CameraWorker(self.camera_panel.device_index.value(), processor=self.gesture_processor.process, parent=self, **kwargs)
        self.camera_worker = worker
        worker.error.connect(self._camera_error)
        worker.finished.connect(self._camera_finished)
        worker.start()
        self.frame_timer.start()
        self._refresh()

    def _gesture_options(self):
        tracking = self.camera_panel.tracking_check.isChecked()
        if not tracking and self.camera_panel.control_check.isChecked():
            self.camera_panel.control_check.setChecked(False)
        self.camera_panel.control_check.setEnabled(tracking and not self._closing)
        control = tracking and self.camera_panel.control_check.isChecked()
        self._save_setting('tracking_enabled', tracking)
        self._save_setting('gesture_enabled', control)
        if self.gesture_processor:
            self.gesture_processor.set_enabled(tracking, control)
        if not tracking:
            self.state.gestures = 'Не підключені'
        self.camera_panel.gesture_status.setText(('Відстеження увімкнено' if tracking else 'Відстеження вимкнено') + (' · керування дозволено' if control else ' · керування вимкнено'))

    def _emergency_stop(self):
        self.camera_panel.control_check.setChecked(False)
        if self.gesture_processor:
            self.gesture_processor.set_enabled(self.camera_panel.tracking_check.isChecked(), False)
        self.camera_panel.gesture_status.setText('Керування зупинено клавішею Esc')

    def _poll_frame(self):
        if self.camera_worker is None or not self._camera_requested or self._camera_failed:
            return
        frame = self.camera_worker.take_frame()
        if frame is not None:
            self.camera_panel.show_frame(frame)
            if self.state.camera != 'Активна':
                self.state.camera = 'Активна'
                self.state._add_event('Камеру підключено: відеопотік активний')
                self._refresh()
        if self.gesture_processor and self.camera_panel.tracking_check.isChecked():
            status = self.gesture_processor.snapshot()
            if (status.get('emergency_stopped') or status.get('error')) and self.camera_panel.control_check.isChecked():
                # The processor has already disarmed. Do not reset its error/ESC
                # evidence by treating this status update as a new user opt-in.
                self.camera_panel.control_check.blockSignals(True)
                self.camera_panel.control_check.setChecked(False)
                self.camera_panel.control_check.blockSignals(False)
                self._save_setting('gesture_enabled', False)
            self.state.gestures = status.get('gesture') or 'Руку не знайдено'
            message = status.get('error') or self.state.gestures
            if status.get('emergency_stopped'):
                message = 'Esc: керування зупинено. ' + message
            self.camera_panel.gesture_status.setText(message + (' · керування дозволено' if status.get('control') else ' · керування вимкнено'))

    def _camera_error(self, message):
        if not self._camera_requested or self._closing:
            return
        self._camera_failed = True
        self.state.camera = 'Помилка'
        self.camera_panel.show_message(message)
        self.state._add_event(f'Помилка камери: {message}')
        self._refresh()

    def _stop_camera(self):
        self._camera_requested = False
        self.frame_timer.stop()
        self.camera_panel.control_check.setChecked(False)
        if self.gesture_processor:
            self.gesture_processor.set_enabled(False, False)
        self.camera_panel.show_message('Камеру вимкнено.')
        self.camera_panel.retry_button.setEnabled(False)
        if self.camera_worker is not None:
            self.state.camera = 'Зупинення…'
            self.camera_worker.stop()
            self.toggle_button.setEnabled(False)
            self.camera_panel.show_message('Зупинення камери… Очікуємо відповіді пристрою.')
        else:
            self.state.camera = 'Готова'

    def _camera_finished(self):
        worker, self.camera_worker = self.camera_worker, None
        self.frame_timer.stop()
        if self.gesture_processor:
            self.gesture_processor.close()
            self.gesture_processor = None
        if worker is not None:
            worker.deleteLater()
        self.camera_panel.control_check.setChecked(False)
        self.camera_panel.device_index.setEnabled(True)
        self.camera_panel.retry_button.setEnabled(self.state.running and not self._closing)
        if not self._camera_requested:
            self.state.camera = 'Готова'
            self.camera_panel.show_message('Камеру вимкнено.')
        self._camera_requested = False
        self._refresh()
        self._workers_finished()

    def shutdown_by_voice(self):
        if not self.state.running or self._closing:
            return
        result = request_shutdown(True)
        self.state._add_event(result.message)
        self.voice_panel.result.setText(result.message)
        self._refresh()

    def confirm_shutdown(self):
        if self._shutdown_prompt or self._closing:
            return
        self._shutdown_prompt = True
        try:
            prompt = QMessageBox(self)
            prompt.setWindowTitle('Вимкнути комп’ютер?')
            prompt.setText('Збережіть відкриті документи перед вимкненням комп’ютера.')
            yes = prompt.addButton('Вимкнути', QMessageBox.AcceptRole)
            cancel = prompt.addButton('Скасувати', QMessageBox.RejectRole)
            prompt.setDefaultButton(cancel)
            prompt.exec()
            result = request_shutdown(prompt.clickedButton() is yes)
            self.state._add_event(result.message)
            self.voice_panel.result.setText(result.message)
            self._refresh()
        finally:
            self._shutdown_prompt = False

    def closeEvent(self, event):
        self._closing = True
        self.command_manager.request_close()
        self.camera_panel.control_check.setChecked(False)
        self.core.timer.stop()
        if self.camera_worker is not None or self.voice.worker is not None or self.command_manager.editor_busy():
            self._stop_assistant()
            event.ignore()
        else:
            event.accept()

    def _clear_events(self):
        self.state.events.clear()
        self._refresh_events()

    def _refresh(self):
        self.command_text.setText(self.state.last_command)
        self.toggle_button.setProperty('running', self.state.running)
        self.toggle_button.setText('Зупинити асистента' if self.state.running else 'Запустити асистента')
        self.system_label.setText('●  СИСТЕМА АКТИВНА' if self.state.running else '●  ОЧІКУВАННЯ')
        if hasattr(self, 'voice'):
            self.mic_button.setText('Вимкнути мікрофон' if self.voice.active else 'Увімкнути мікрофон')
            self.mic_button.setEnabled(not self._closing and (self.voice.active or self.voice.worker is None))
            self.toggle_button.setEnabled(not self._closing and (self.state.running or
                (self.camera_worker is None and self.voice.worker is None)))
        self.camera_panel.toggle_button.setText('Вимкнути камеру' if self._camera_requested else 'Увімкнути камеру')
        self.camera_panel.toggle_button.setEnabled(not self._closing and (self._camera_requested or self.camera_worker is None))
        self.device_summary.setText(f'МІКРОФОН   {self.state.microphone}\nКАМЕРА       {self.state.camera}')
        self.toggle_button.style().unpolish(self.toggle_button)
        self.toggle_button.style().polish(self.toggle_button)
        self._refresh_events()

    def _refresh_events(self):
        self.event_list.clear()
        for event in reversed(self.state.events[-200:]):
            item = QListWidgetItem(f'{event.time}   {event.message}')
            item.setToolTip(event.message)
            self.event_list.addItem(item)
