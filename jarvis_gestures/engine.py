"""Pure landmark geometry and temporal state; never performs desktop actions."""
from dataclasses import dataclass, field
from math import hypot, isfinite


@dataclass
class GestureResult:
    gesture: str
    actions: list = field(default_factory=list)


class GestureEngine:
    """One active hand. Native camera coordinates are mirrored here exactly once.

    A stable open palm arms control after startup, loss, ambiguity or hand change.
    Distances are relative to palm size. Actions are mutually exclusive per frame.
    """
    def __init__(self, smoothing=.25, sensitivity=1.):
        self.set_smoothing(smoothing)
        self.set_sensitivity(sensitivity)

    def set_smoothing(self, value):
        value = float(value)
        if not isfinite(value):
            raise ValueError('Згладжування має бути скінченним числом.')
        self.smoothing = max(.05, min(1., value))

    def set_sensitivity(self, value):
        """Higher values accept wider pinches and reduce scroll travel per notch.

        Changing geometry cannot inherit an armed pose from earlier thresholds.
        """
        value = float(value)
        if not isfinite(value):
            raise ValueError('Чутливість має бути скінченним числом.')
        self.sensitivity = max(.25, min(2., value))
        self.reset()

    def reset(self):
        self._hand = None
        self._armed = False
        self._candidate = None
        self._since = 0.
        self._pinch_latched = False
        self._release_since = None
        self._click_at = -float('inf')
        self._volume_at = -float('inf')
        self._pointer = None
        self._scroll_y = None
        self._wrist = None

    @staticmethod
    def _distance(a, b):
        return hypot(a[0]-b[0], a[1]-b[1])

    def update(self, landmarks, now, hand_id='hand'):
        try:
            points = [(float(p[0]), float(p[1])) for p in landmarks]
            valid = len(points) == 21 and all(isfinite(v) for p in points for v in p)
        except (TypeError, ValueError, IndexError):
            valid = False
        if not valid:
            self.reset()
            return GestureResult('Руку не знайдено')
        if self._hand != hand_id or (self._wrist is not None and self._distance(self._wrist, points[0]) > .45):
            self.reset()
            self._hand = hand_id
        self._wrist = points[0]
        scale = self._distance(points[0], points[9])
        if scale < .025:
            self.reset()
            return GestureResult('Рука надто далеко')
        left = self._distance(points[4], points[8]) / scale
        right = self._distance(points[4], points[12]) / scale
        pinch_close, pinch_release = .24*self.sensitivity, .38*self.sensitivity
        if left > pinch_release and right > pinch_release:
            if self._release_since is None:
                self._release_since = now
            if now - self._release_since >= .10:
                self._pinch_latched = False
        else:
            self._release_since = None
        raised = [self._distance(points[0], points[t]) >
                  self._distance(points[0], points[t-2]) * 1.15
                  for t in (8, 12, 16, 20)]
        if left < pinch_close and right < pinch_close:
            pose = 'ambiguous'
            self._armed = False
            self._pinch_latched = True
        elif left < pinch_close:
            pose = 'left'
        elif right < pinch_close:
            pose = 'right'
        elif all(raised):
            pose = 'neutral'
        elif not any(raised) and abs(points[4][0]-points[3][0]) < scale*.6 and abs(points[4][1]-points[3][1]) > scale*.7:
            pose = 'volume_up' if points[4][1] < points[3][1] else 'volume_down'
        elif raised == [True, True, False, False]:
            pose = 'scroll'
        elif raised == [True, False, False, False]:
            pose = 'pointer'
        else:
            pose = 'unknown'
        labels = {'ambiguous': 'Неоднозначний щипок', 'left': 'Лівий клік',
                  'right': 'Правий клік', 'neutral': 'Відкрита долоня',
                  'pointer': 'Курсор', 'scroll': 'Прокрутка',
                  'volume_up': 'Гучність +', 'volume_down': 'Гучність −',
                  'unknown': 'Жест не розпізнано'}
        result = GestureResult(labels[pose])
        if pose != self._candidate:
            self._candidate, self._since = pose, now
            self._scroll_y = None
        if pose != 'pointer':
            self._pointer = None
        if now - self._since < .10:
            return result
        if pose == 'neutral' and left > pinch_release and right > pinch_release:
            self._armed = True
        if not self._armed:
            result.gesture += ' · покажіть відкриту долоню'
            return result
        if pose in ('left', 'right'):
            if not self._pinch_latched:
                self._pinch_latched = True
                if now - self._click_at >= .4:
                    result.actions.append(('click', pose))
                    self._click_at = now
        elif pose == 'pointer':
            x = max(0., min(1., (1.-points[8][0]-.1)/.8))
            y = max(0., min(1., (points[8][1]-.1)/.8))
            if self._pointer is not None:
                x, y = (old + self.smoothing*(new-old) for old, new in zip(self._pointer, (x,y)))
            self._pointer = (x,y)
            result.actions.append(('move', x, y))
        elif pose == 'scroll':
            y = (points[8][1]+points[12][1]) / 2
            if self._scroll_y is None:
                self._scroll_y = y
            scroll_step = .035 / self.sensitivity
            steps = int((self._scroll_y-y) / scroll_step)
            if steps:
                steps = max(-4, min(4, steps))
                self._scroll_y -= steps*scroll_step
                result.actions.append(('scroll', steps))
        elif pose in ('volume_up', 'volume_down') and now-self._volume_at >= .25:
            result.actions.append(('volume', 1 if pose == 'volume_up' else -1))
            self._volume_at = now
        return result
