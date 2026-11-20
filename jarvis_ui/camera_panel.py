"""Camera preview and opt-in hand control; inference stays on the capture thread."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget, QSizePolicy, QCheckBox


class CameraPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = QImage()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.device_index = QSpinBox(self)
        self.device_index.setRange(0, 99)
        self.device_index.setToolTip('0 — перша камера. Номер можна змінити перед запуском.')
        self.toggle_button = QPushButton('Увімкнути камеру')
        controls.addWidget(self.toggle_button)
        self.retry_button = QPushButton('Повторити підключення')
        self.retry_button.setEnabled(False)
        controls.addWidget(self.retry_button)
        controls.addStretch()
        layout.addLayout(controls)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setWordWrap(True)
        self.preview.setMinimumSize(240, 180)
        self.preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.preview.setStyleSheet('background:#101014; color:#9d7a88; border:1px solid #462330; border-radius:12px; padding:8px;')
        layout.addWidget(self.preview, 1)
        self.tracking_check = QCheckBox('Відстежувати руку')
        self.control_check = QCheckBox('Дозволити керування Windows')
        self.control_check.setEnabled(False)
        row = QHBoxLayout()
        row.addWidget(self.tracking_check)
        row.addWidget(self.control_check)
        row.addStretch()
        layout.addLayout(row)
        self.gesture_status = QLabel('Відстеження вимкнено · керування вимкнено')
        self.gesture_status.setWordWrap(True)
        layout.addWidget(self.gesture_status)
        hint = QLabel('Вказівний — курсор · щипок — клік · два пальці — прокрутка\nВеликий палець — гучність · Esc — негайно вимкнути керування')
        hint.setObjectName('pageSubtitle')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.show_message('Камеру вимкнено\nУвімкніть відео для перегляду та відстеження руки.')

    def show_frame(self, rgb):
        height, width, _ = rgb.shape
        self._image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format_RGB888).copy()
        self._render()

    def show_message(self, text):
        self._image = QImage()
        self.preview.setPixmap(QPixmap())
        self.preview.setText(text)

    def _render(self):
        if not self._image.isNull():
            self.preview.setPixmap(QPixmap.fromImage(self._image).scaled(
                self.preview.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()
