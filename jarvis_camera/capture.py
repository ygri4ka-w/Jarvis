"""Synchronous OpenCV adapter. Use only from the owning capture thread."""
from collections.abc import Callable
from typing import Protocol

import cv2
import numpy as np


class Device(Protocol):
    def isOpened(self) -> bool: ...
    def read(self) -> tuple[bool, np.ndarray | None]: ...
    def release(self) -> None: ...


DeviceFactory = Callable[[int], Device]


class CameraError(RuntimeError):
    """Camera failures suitable for display in the Ukrainian interface."""


class Capture:
    def __init__(self, index: int = 0, factory: DeviceFactory = cv2.VideoCapture):
        self.index = index
        self.factory = factory
        self.device: Device | None = None

    def open(self) -> None:
        if self.device is not None:
            return
        try:
            self.device = self.factory(self.index)
            if not self.device.isOpened():
                raise CameraError(
                    f'Не вдалося відкрити камеру №{self.index}. '
                    'Перевірте підключення, номер камери, дозволи Windows '
                    'та чи не використовує її інша програма.'
                )
        except Exception as exc:
            self.close()
            if isinstance(exc, CameraError):
                raise
            raise CameraError(f'Не вдалося відкрити камеру №{self.index}.') from exc

    def read(self) -> np.ndarray:
        if self.device is None:
            raise CameraError('Камеру не відкрито.')
        try:
            ok, frame = self.device.read()
            if not ok or frame is None or frame.size == 0:
                raise CameraError('Відеопотік втрачено. Перевірте камеру та повторіть підключення.')
            if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
                raise CameraError('Камера повернула непідтримуваний формат зображення.')
            return frame
        except CameraError:
            raise
        except Exception as exc:
            raise CameraError('Помилка читання відео. Перевірте камеру та повторіть підключення.') from exc

    def close(self) -> None:
        device, self.device = self.device, None
        if device is not None:
            device.release()
