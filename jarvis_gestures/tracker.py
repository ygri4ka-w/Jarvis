"""MediaPipe Tasks wrapper. Model and imports are loaded only on capture thread."""
from pathlib import Path
import sys


def task_model_path():
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    external = root / 'models' / 'hand_landmarker.task'
    if external.exists() or not getattr(sys, '_MEIPASS', None):
        return external
    return Path(sys._MEIPASS) / 'models' / 'hand_landmarker.task'


class MediaPipeTracker:
    def __init__(self, model_path=None):
        path = Path(model_path) if model_path is not None else task_model_path()
        if not path.is_file():
            raise RuntimeError('Не знайдено модель models/hand_landmarker.task. Запустіть встановлення моделей.')
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        self._mp = mp
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.VIDEO, num_hands=1,
            min_hand_detection_confidence=.6, min_hand_presence_confidence=.6,
            min_tracking_confidence=.6)
        self._detector = vision.HandLandmarker.create_from_options(options)
        self._timestamp = -1

    def detect(self, bgr):
        import cv2
        from time import monotonic
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        self._timestamp = max(self._timestamp+1, int(monotonic()*1000))
        result = self._detector.detect_for_video(image, self._timestamp)
        if not result.hand_landmarks:
            return None, None
        points = [(p.x, p.y, p.z) for p in result.hand_landmarks[0]]
        label = result.handedness[0][0].category_name if result.handedness else 'hand'
        return points, label

    def close(self):
        self._detector.close()
