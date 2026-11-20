"""Background capture with a bounded, latest-frame mailbox."""
from collections.abc import Callable
from threading import Event, Lock
from unicodedata import mirrored

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from .capture import CameraError, Capture, DeviceFactory

FrameProcessor = Callable[[np.ndarray], np.ndarray]


class CameraWorker(QThread):
    error = Signal(str)

    def __init__(self, index=0, capture_factory: DeviceFactory = cv2.VideoCapture,
                 processor: FrameProcessor | None = None, parent=None):
        super().__init__(parent)
        self.index = index
        self.capture_factory = capture_factory
        self.processor = processor
        self._stop = Event()
        self._lock = Lock()
        self._latest: np.ndarray | None = None

    def stop(self) -> None:
        # Event also remembers cancellation before QThread.run begins.
        self._stop.set()

    def take_frame(self) -> np.ndarray | None:
        with self._lock:
            frame, self._latest = self._latest, None
        return frame

    def run(self) -> None:
        capture = Capture(self.index, self.capture_factory)
        failure = None
        try:
            if self._stop.is_set():
                return
            capture.open()
            while not self._stop.is_set():
                frame = capture.read()
                if self._stop.is_set():
                    break
                if self.processor is not None:
                    frame = self.processor(frame)
                mirrored = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(mirrored, cv2.COLOR_BGR2RGB)
                with self._lock:
                    self._latest = rgb
                # Bound CPU use for sources that return immediately.
                self._stop.wait(1 / 30)
        except Exception as exc:
            failure = str(exc) if isinstance(exc, CameraError) else 'Помилка обробки відео.'
        finally:
            try:
                capture.close()
            except Exception:
                failure = failure or 'Не вдалося коректно звільнити камеру.'
            if failure and not self._stop.is_set():
                with self._lock:
                    self._latest = None
                self.error.emit(failure)

