"""Bounded, event-driven assistant visualization. No synthetic microphone data."""
import math
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


class AnimatedCore(QWidget):
    LABELS = {'idle': 'ОЧІКУВАННЯ', 'listening': 'СЛУХАЮ', 'processing': 'ОБРОБКА',
              'executing': 'ВИКОНАННЯ', 'error': 'ПОМИЛКА', 'stopped': 'ВИМКНЕНО'}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode, self.label, self.level = 'idle', '', 0.0
        self.animations, self.phase = True, 0.0
        self.setMinimumSize(260, 260)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)

    def set_state(self, mode, label=''):
        self.mode = mode if mode in self.LABELS else 'idle'
        self.label = label
        self.update()

    def set_level(self, value):
        self.level = max(0.0, min(1.0, float(value)))
        self.update()

    def set_animations(self, enabled):
        self.animations = bool(enabled)
        self._sync_timer()
        self.update()

    def _sync_timer(self):
        if self.animations and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self):
        self.phase = (self.phase + .025) % (2 * math.pi)
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        radius = min(self.width(), self.height()) * .38
        phase = self.phase if self.animations else 0
        energy = self.level if self.mode == 'listening' else 0
        pulse = math.sin(phase) * .012 if self.mode == 'idle' else 0
        color = QColor('#ff344e' if self.mode != 'error' else '#ff936b')
        glow = QRadialGradient(QPointF(cx, cy), radius * 1.3)
        glow.setColorAt(0, QColor(130, 12, 29, 50 + int(energy * 70)))
        glow.setColorAt(.65, QColor(115, 8, 24, 26))
        glow.setColorAt(1, QColor(10, 10, 13, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), radius * 1.3, radius * 1.3)
        p.setBrush(Qt.NoBrush)
        for scale, width, alpha in ((1.05, 1, 45), (.96, 1, 90), (.84, 2, 210), (.72, 1, 80), (.64, 2, 150)):
            r = radius * (scale + pulse + energy * .035)
            c = QColor(color)
            c.setAlpha(alpha)
            p.setPen(QPen(c, width + energy))
            rect = QRectF(cx-r, cy-r, 2*r, 2*r)
            if scale in (.84, .64):
                offset = phase * 180 / math.pi if self.mode == 'processing' else phase * 12
                for angle in (0, 120, 240):
                    p.drawArc(rect, int((angle + offset) * 16), 90 * 16)
            else:
                p.drawEllipse(rect)
        for i in range(72):
            angle = i * math.pi / 36
            amplitude = energy * (0.25 + .75 * abs(math.sin(angle * 3)))
            outer = radius * (1.09 + amplitude * .17)
            inner = radius * 1.075
            p.setPen(QPen(QColor('#e52b43') if i % 6 == 0 else QColor('#55202a'), 2 if i % 6 == 0 else 1))
            p.drawLine(QPointF(cx + math.cos(angle)*inner, cy + math.sin(angle)*inner),
                       QPointF(cx + math.cos(angle)*outer, cy + math.sin(angle)*outer))
        p.setPen(QColor('#fff3f5'))
        font = QFont('Segoe UI', max(17, int(radius * .18)), QFont.DemiBold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 5)
        p.setFont(font)
        p.drawText(QRectF(0, cy-29, self.width(), 40), Qt.AlignCenter, 'JARVIS')
        p.setFont(QFont('Segoe UI', 8))
        p.setPen(color)
        p.drawText(QRectF(0, cy+19, self.width(), 25), Qt.AlignCenter, self.label or self.LABELS[self.mode])
        if self.mode == 'executing':
            p.setPen(QPen(color, 4))
            p.drawEllipse(QPointF(cx, cy), radius*.57, radius*.57)
        p.end()
