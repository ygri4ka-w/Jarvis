"""Thread-safe bridge from camera frames to opt-in gesture actions."""
from threading import Event, Lock, RLock, Thread, current_thread
from time import monotonic

from .engine import GestureEngine
from .tracker import MediaPipeTracker
from .windows_input import WindowsInput


CONNECTIONS = ((0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
               (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),
               (15,16),(13,17),(0,17),(17,18),(18,19),(19,20))


class GestureProcessor:
    def __init__(self, *, adapter=None, tracker_factory=None, model_path=None,
                 clock=monotonic, start_monitor=True):
        self._adapter = adapter if adapter is not None else WindowsInput()
        self._factory = tracker_factory or (lambda: MediaPipeTracker(model_path))
        self._clock = clock
        self._monitor_enabled = start_monitor
        self._lock = RLock()
        self._process_lock = Lock()
        self._stop = Event()
        self._monitor = None
        self._tracker = None
        self._engine = GestureEngine()
        self._tracking_enabled = False
        self._failed = False
        self._generation = 0
        self._state = dict(gesture='Відстеження вимкнено', tracking=False,
                           control=False, error='', landmarks=[], emergency_stopped=False)

    def set_enabled(self, tracking, control):
        with self._lock:
            self._generation += 1
            self._tracking_enabled = bool(tracking)
            self._state['control'] = bool(tracking and control)
            self._state['tracking'] = False
            self._state['landmarks'] = []
            self._state['error'] = ''
            self._failed = False
            self._engine.reset()
            self._state['gesture'] = 'Покажіть відкриту долоню' if tracking else 'Відстеження вимкнено'
            if control and tracking:
                self._state['emergency_stopped'] = False
                if self._monitor_enabled and (self._monitor is None or not self._monitor.is_alive()):
                    self._stop = Event()
                    self._monitor = Thread(target=self._watch_escape, name='JarvisGestureEscape', daemon=True)
                    self._monitor.start()

    def set_smoothing(self, value):
        with self._lock:
            self._engine.set_smoothing(value)

    def set_sensitivity(self, value):
        with self._lock:
            self._engine.set_sensitivity(value)
            self._generation += 1
            if self._tracking_enabled:
                self._state['gesture'] = 'Покажіть відкриту долоню'

    def snapshot(self):
        with self._lock:
            return {**self._state, 'landmarks': list(self._state['landmarks'])}

    def _emergency(self):
        self._state.update(control=False, emergency_stopped=True,
                           gesture='Керування зупинено клавішею Esc')
        self._generation += 1
        self._engine.reset()

    def _fail(self, exc):
        self._failed = True
        self._state.update(control=False, tracking=False, landmarks=[],
                           error=f'Помилка відстеження рук: {exc}', gesture='Відстеження недоступне')
        self._generation += 1
        self._engine.reset()

    def _watch_escape(self):
        while not self._stop.wait(.035):
            with self._lock:
                if not self._state['control']:
                    continue
                try:
                    if self._adapter.escape_pressed():
                        self._emergency()
                except Exception as exc:
                    self._fail(exc)

    def process(self, bgr):
        # Detection is synchronous on the camera worker. There is no frame queue.
        with self._process_lock:
            with self._lock:
                if not self._tracking_enabled or self._failed:
                    return bgr
                generation = self._generation
            try:
                if self._tracker is None:
                    self._tracker = self._factory()
                points, identity = self._tracker.detect(bgr)
                with self._lock:
                    if generation != self._generation:
                        return bgr
                    if self._state['control'] and self._adapter.escape_pressed():
                        self._emergency()
                        return bgr
                    result = self._engine.update(points, self._clock(), identity)
                    self._state.update(gesture=result.gesture, tracking=bool(points),
                                       landmarks=list(points or []), error='')
                    if self._state['control']:
                        for action, *args in result.actions:
                            getattr(self._adapter, action)(*args)
                if points:
                    self._annotate(bgr, points)
                return bgr
            except Exception as exc:
                with self._lock:
                    self._fail(exc)
                return bgr

    @staticmethod
    def _annotate(bgr, points):
        import cv2
        height, width = bgr.shape[:2]
        pixels = [(round(p[0]*(width-1)), round(p[1]*(height-1))) for p in points]
        for start, end in CONNECTIONS:
            cv2.line(bgr, pixels[start], pixels[end], (65,65,220), 2, cv2.LINE_AA)
        for point in pixels:
            cv2.circle(bgr, point, 3, (180,180,255), -1, cv2.LINE_AA)

    def close(self):
        with self._lock:
            self._generation += 1
            self._tracking_enabled = False
            self._state.update(control=False, tracking=False, landmarks=[], gesture='Відстеження вимкнено')
            self._engine.reset()
            self._stop.set()
            monitor = self._monitor
        if monitor is not None and monitor is not current_thread():
            monitor.join(timeout=1.)
        with self._process_lock:
            tracker, self._tracker = self._tracker, None
            if tracker is not None:
                try:
                    tracker.close()
                except Exception as exc:
                    with self._lock:
                        self._state['error'] = f'Не вдалося звільнити відстеження: {exc}'
