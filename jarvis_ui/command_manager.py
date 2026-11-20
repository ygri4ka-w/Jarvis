from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QTabWidget
from .command_editor import CommandEditor
from jarvis_voice.languages import language_profiles

ACTION_LABELS = {'browser': 'Відкрити браузер', 'open_browser': 'Відкрити браузер', 'youtube': 'Відкрити YouTube',
                 'calculator': 'Калькулятор', 'notepad': 'Блокнот', 'time': 'Поточний час',
                 'stop': 'Зупинити асистента', 'stop_assistant': 'Зупинити асистента',
                 'close_application': 'Закрити JARVIS', 'shutdown': 'Вимкнути комп’ютер'}


class CommandManager(QWidget):
    commands_changed = Signal()
    launch_requested = Signal(str)
    test_requested = Signal(bool)
    idle = Signal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store, self.testing, self.language = store, False, 'ru'
        self.editor = None
        self._waiting_for_editor = False
        self.setWindowTitle('Команди JARVIS')
        self.resize(720, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel('Одна дія. Кілька фраз. Ваша мова.')
        hint.setObjectName('sectionTitle')
        layout.addWidget(hint)
        self.tabs = QTabWidget()
        self.list = QListWidget()
        self.builtins = QListWidget()
        self.tabs.addTab(self.list, 'Власні команди')
        self.tabs.addTab(self.builtins, 'Вбудовані команди')
        layout.addWidget(self.tabs, 1)
        row = QHBoxLayout()
        self.edit_buttons = []
        for text, callback in [('Додати', self.add), ('Змінити', self.edit), ('Видалити', self.remove), ('Запустити дію', self.test_launch)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.edit_buttons.append(button)
        self.tabs.currentChanged.connect(lambda index: [button.setEnabled(index == 0) for button in self.edit_buttons[1:]])
        layout.addLayout(row)
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        test_row = QHBoxLayout()
        self.test_button = QPushButton('Перевірити мікрофоном')
        self.test_button.clicked.connect(self.toggle_test)
        test_row.addWidget(self.test_button)
        self.test_transcript = QLabel('Почуйте фразу й перевірте збіг без виконання дії.')
        self.test_transcript.setWordWrap(True)
        test_row.addWidget(self.test_transcript, 1)
        layout.addLayout(test_row)
        self.refresh()

    def set_language(self, language):
        self.language = language
        self.refresh()

    def refresh(self):
        self.list.clear()
        for command in self.store.items:
            language = 'АНГ' if command.language == 'en' else 'РОС'
            item = QListWidgetItem(f'{language}  ·  {" / ".join(command.phrases)}\n{command.target}')
            item.setData(Qt.UserRole, command.id)
            item.setToolTip(command.target)
            self.list.addItem(item)
        self.builtins.clear()
        commands = language_profiles()[self.language]['commands']
        groups = {}
        for phrase, action in commands.items():
            groups.setdefault(action, []).append(phrase)
        for action, phrases in groups.items():
            self.builtins.addItem(f'{ACTION_LABELS.get(action, action)}\n' + ' · '.join(phrases))
        self.message.setText(self.store.error or ('Додайте EXE або вебадресу та фрази для запуску.' if not self.store.items else '«Запустити дію» виконує обрану команду одразу.'))

    def selected(self):
        item = self.list.currentItem()
        return self.store.get(item.data(Qt.UserRole)) if item else None

    def add(self):
        self.open_editor()

    def edit(self):
        item = self.selected()
        if item:
            self.open_editor(item)

    def open_editor(self, item=None):
        self.end_test()
        self.editor = CommandEditor(self.store, item, self)
        try:
            if self.editor.exec() == QDialog.Accepted:
                self.refresh()
                self.commands_changed.emit()
        finally:
            self.editor.deleteLater()
            self.editor = None
            self._waiting_for_editor = False

    def editor_busy(self):
        return self.editor is not None and self.editor.worker is not None

    def request_close(self):
        self.end_test()
        if self.editor is not None:
            if self.editor_busy() and not self._waiting_for_editor:
                self._waiting_for_editor = True
                self.editor.finished.connect(lambda result: self.idle.emit())
            self.editor.reject()

    def remove(self):
        item = self.selected()
        if item:
            try:
                self.store.delete(item.id)
                self.refresh()
                self.commands_changed.emit()
            except (ValueError, OSError) as exc:
                self.message.setText(f'Не вдалося видалити: {exc}')

    def test_launch(self):
        item = self.selected()
        if item:
            self.launch_requested.emit(item.id)

    def toggle_test(self):
        self.testing = not self.testing
        self.test_button.setText('Завершити перевірку' if self.testing else 'Перевірити мікрофоном')
        if self.testing:
            self.test_transcript.setText('Слухаю тестову фразу. Дії не виконуються.')
        self.test_requested.emit(self.testing)

    def end_test(self):
        if self.testing:
            self.toggle_test()

    def show_test_result(self, text, action):
        label = ACTION_LABELS.get(action, action)
        if action.startswith('custom:'):
            command = self.store.get(action.removeprefix('custom:'))
            label = command.phrase if command else 'Власна команда'
        self.test_transcript.setText(f'«{text}»\n' + ('Знайдено: ' + label if action else 'Збігу немає. Спробуйте іншу фразу.'))

    def hideEvent(self, event):
        self.end_test()
        super().hideEvent(event)
