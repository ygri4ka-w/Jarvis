"""Small drawn navigation icons, independent of installed symbol fonts."""
import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def navigation_icon(index, active=False):
    pixmap = QPixmap(44, 44)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(2, 2)
    painter.setPen(QPen(QColor('#ff5a70' if active else '#a18b96'), 1.3))
    painter.setBrush(Qt.NoBrush)
    if index == 0:
        path = QPainterPath(QPointF(3, 10))
        for x, y in ((11, 3), (19, 10), (17, 10), (17, 19), (13, 19), (13, 13), (9, 13), (9, 19), (5, 19), (5, 10)):
            path.lineTo(x, y)
        painter.drawPath(path)
    elif index == 1:
        for y in (5, 11, 17):
            painter.drawEllipse(QPointF(4, y), .7, .7)
            painter.drawLine(QPointF(8, y), QPointF(19, y))
    elif index == 2:
        painter.drawRoundedRect(QRectF(2.5, 6, 17, 13), 2, 2)
        painter.drawEllipse(QPointF(11, 12.5), 4, 4)
        painter.drawLine(QPointF(7, 3.5), QPointF(15, 3.5))
    else:
        painter.drawEllipse(QPointF(11, 11), 6, 6)
        painter.drawEllipse(QPointF(11, 11), 2.2, 2.2)
        for i in range(8):
            angle = i * math.pi / 4
            painter.drawLine(QPointF(11+math.cos(angle)*6, 11+math.sin(angle)*6),
                             QPointF(11+math.cos(angle)*9, 11+math.sin(angle)*9))
    painter.end()
    return QIcon(pixmap)
