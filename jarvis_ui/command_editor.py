from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox, QPlainTextEdit, QFormLayout
from jarvis_voice.vocabulary import unknown_words


class VocabularyCheck(QThread):
    def __init__(self, phrase, checker, parent=None):
        super().__init__(parent)
        self.phrase, self.checker = phrase, checker
        self.unknown, self.problem = [], ''

    def run(self):
        try:
            self.unknown = self.checker(self.phrase)
        except Exception as exc:
            self.problem = f'Не вдалося перевірити словник. {exc}'


class CommandEditor(QDialog):
    def __init__(self, store, item=None, parent=None, checker=None):
        super().__init__(parent)
        self.store, self.item, self.checker = store, item, checker
        self.worker, self._closing, self._unchecked = None, False, False
        self.setWindowTitle('Змінити команду' if item else 'Нова команда')
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setSpacing(13)
        form = QFormLayout()
        self.language = QComboBox()
        self.language.addItem('Російська', 'ru')
        self.language.addItem('Англійська', 'en')
        self.language.setCurrentIndex(max(0, self.language.findData(item.language if item else 'ru')))
        form.addRow('Мова фраз', self.language)
        self.action_type = QComboBox()
        self.action_type.addItem('Запуск програми (.exe)', 'exe')
        self.action_type.addItem('Відкрити вебадресу', 'url')
        self.action_type.setCurrentIndex(max(0, self.action_type.findData(item.action_type if item else 'exe')))
        form.addRow('Дія', self.action_type)
        layout.addLayout(form)
        layout.addWidget(QLabel('Основна фраза — без звернення'))
        self.phrase = QLineEdit(item.phrase if item else '')
        self.phrase.setPlaceholderText('открой игру / open my game')
        layout.addWidget(self.phrase)
        layout.addWidget(QLabel('Інші варіанти фрази — кожен із нового рядка'))
        self.aliases = QPlainTextEdit()
        self.aliases.setMaximumHeight(100)
        if item:
            self.aliases.setPlainText('\n'.join(item.phrases[1:]))
        layout.addWidget(self.aliases)
        layout.addWidget(QLabel('Повний шлях до програми або адреса https://'))
        row = QHBoxLayout()
        self.exe = QLineEdit(item.target if item else '')
        row.addWidget(self.exe, 1)
        self.browse = QPushButton('Обрати файл')
        self.browse.clicked.connect(self.choose_file)
        row.addWidget(self.browse)
        layout.addLayout(row)
        self.message = QLabel('Перевіримо фрази у словнику обраної офлайн-моделі перед збереженням.')
        self.message.setWordWrap(True)
        self.message.setMinimumHeight(60)
        layout.addWidget(self.message)
        buttons = QHBoxLayout()
        self.cancel_button = QPushButton('Скасувати')
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        self.save_button = QPushButton('Зберегти')
        self.save_button.setObjectName('primaryButton')
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        self.phrase.textChanged.connect(self.reset_warning)
        self.aliases.textChanged.connect(self.reset_warning)
        self.exe.textChanged.connect(self.reset_warning)
        self.language.currentIndexChanged.connect(self.reset_warning)
        self.action_type.currentIndexChanged.connect(self.reset_warning)

    def reset_warning(self):
        self._unchecked = False
        self.save_button.setText('Зберегти')
        self.browse.setEnabled(self.action_type.currentData() == 'exe')

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Оберіть програму', '', 'Програми (*.exe)')
        if path:
            self.exe.setText(path)

    def set_busy(self, busy):
        for widget in (self.phrase, self.aliases, self.language, self.action_type, self.exe, self.browse, self.save_button):
            widget.setEnabled(not busy)
        if not busy:
            self.browse.setEnabled(self.action_type.currentData() == 'exe')

    def phrases(self):
        return [self.phrase.text()] + [line.strip() for line in self.aliases.toPlainText().splitlines() if line.strip()]

    def save(self):
        if self.worker:
            return
        try:
            language = self.language.currentData()
            phrases = [self.store.validate_phrase(phrase, self.item.id if self.item else None, language=language) for phrase in self.phrases()]
            if len(set(phrases)) != len(phrases):
                raise ValueError('Варіанти фрази не повинні повторюватися.')
            target = self.exe.text().strip()
            if self.action_type.currentData() == 'exe':
                path = Path(target)
                if not path.is_absolute() or path.suffix.lower() != '.exe' or not path.is_file():
                    raise ValueError('Оберіть наявний файл .exe за повним шляхом.')
            elif urlparse(target).scheme not in ('http', 'https') or not urlparse(target).netloc:
                raise ValueError('Введіть коректну адресу http:// або https://.')
            if self._unchecked:
                self.persist()
                return
            self.set_busy(True)
            self.message.setText('Перевіряю слова у моделі Vosk…')
            checker = self.checker or (lambda phrase: unknown_words(phrase, language=language))
            self.worker = VocabularyCheck(' '.join(phrases), checker, self)
            self.worker.finished.connect(self.checked)
            self.worker.start()
        except (ValueError, OSError) as exc:
            self.message.setText(str(exc))

    def checked(self):
        worker, self.worker = self.worker, None
        unknown, problem = worker.unknown, worker.problem
        worker.deleteLater()
        if self._closing:
            super().reject()
            return
        self.set_busy(False)
        if unknown or problem:
            self._unchecked = True
            self.message.setText(problem or ('Vosk не знає слова: ' + ', '.join(unknown) + '. Замініть їх. Можна зберегти для ручного запуску; голосове розпізнавання не гарантовано.'))
            self.save_button.setText('Зберегти попри попередження')
        else:
            self.persist()

    def persist(self):
        try:
            self.store.save(self.phrase.text(), self.exe.text(), self.item.id if self.item else None,
                            language=self.language.currentData(), phrases=self.phrases(),
                            action_type=self.action_type.currentData(), target=self.exe.text())
        except (ValueError, OSError) as exc:
            self.message.setText(f'Не вдалося зберегти: {exc}')
            return
        self.accept()

    def reject(self):
        if self.worker:
            self._closing = True
            self.message.setText('Завершую перевірку…')
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker:
            self.reject()
            event.ignore()
        else:
            event.accept()
