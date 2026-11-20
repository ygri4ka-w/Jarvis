from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class Waveform(QWidget):
    """Paint a mirrored PCM peak envelope, with a fixed display gain."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = [0.0] * 80
        self.setMinimumHeight(130)
        self.setAccessibleName('Звукова хвиля мікрофона')

    def set_levels(self, values):
        self.values = [max(0.0, min(1.0, float(v))) for v in values] or [0.0] * 80
        self.update()

    def clear(self):
        self.set_levels([0.0] * 80)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QPen(QColor('#462330'), 1))
        painter.setBrush(QColor('#141016'))
        painter.drawRoundedRect(rect, 12, 12)
        mid = self.height() / 2
        left, width = 18, max(1, self.width() - 36)
        painter.setPen(QPen(QColor('#462330'), 1))
        painter.drawLine(left, int(mid), left + width, int(mid))
        path = QPainterPath()
        height = max(1, self.height() * .36)
        for sign in (-1, 1):
            for i, value in enumerate(self.values):
                x = left + i * width / max(1, len(self.values) - 1)
                y = mid + sign * min(1, value * 3) * height
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255, 40, 75, 35), 7))
        painter.drawPath(path)
        painter.setPen(QPen(QColor('#ff3757'), 1.8))
        painter.drawPath(path)

