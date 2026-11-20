from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QProgressBar
from .waveform import Waveform


class VoicePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        label = QLabel('ГОЛОСОВИЙ КАНАЛ')
        label.setObjectName('commandLabel')
        layout.addWidget(label)
        self.device_combo = QComboBox(self)
        self.device_combo.setMinimumContentsLength(15)
        self.device_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.refresh_button = QPushButton('Оновити пристрої', self)
        self.status = QLabel('Мікрофон вимкнено')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.waveform = Waveform()
        self.waveform.setFixedHeight(44)
        layout.addWidget(self.waveform)
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setValue(0)
        self.level.setTextVisible(False)
        self.level.setFixedHeight(4)
        layout.addWidget(self.level)
        self.transcript = QLabel('Скажіть: «Джарвис, который час»')
        self.transcript.setWordWrap(True)
        self.transcript.setObjectName('commandText')
        layout.addWidget(self.transcript)
        self.result = QLabel('Результат команди з’явиться тут')
        self.result.setWordWrap(True)
        layout.addWidget(self.result)
        self.retry_button = QPushButton('Повторити підключення мікрофона')
        self.retry_button.setEnabled(False)
        layout.addWidget(self.retry_button)
        # Retained public controls, placed on the commands/settings pages by the window.
        self.add_command_button = QPushButton('Додати команду', self)
        self.manage_commands_button = QPushButton('Мої команди', self)
        self.shutdown_button = QPushButton('Вимкнути ПК', self)
        for button in (self.add_command_button, self.manage_commands_button, self.shutdown_button):
            button.hide()

    def set_busy(self, busy, running):
        self.device_combo.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.retry_button.setEnabled(not busy and running)

    def show_wave(self, values):
        self.waveform.set_levels(values)
        self.level.setValue(round(min(1, max(values, default=0) * 3) * 100))

    def clear_wave(self):
        self.waveform.clear()
        self.level.setValue(0)
