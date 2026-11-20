import json
import math
import os
from pathlib import Path
import tempfile

DEFAULTS = dict(language='ru', microphone=None, camera=0, wake_required=True,
                animations=True, tracking_enabled=False, gesture_enabled=False,
                smoothing=.25, sensitivity=1.0, mirror=True)


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(os.environ.get('APPDATA', str(Path.home()))) / 'JARVIS' / 'settings.json'
        self.values = dict(DEFAULTS)
        self.error = ''
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('settings'), dict):
                    raise ValueError('Invalid settings schema')
                for key, value in data['settings'].items():
                    self._validate(key, value)
                self.values.update(data['settings'])
        except (ValueError, TypeError, OSError):
            self.error = f'Не вдалося прочитати налаштування: {self.path}. Файл не змінено; виправте або перейменуйте його.'

    def get(self, key, default=None):
        return self.values.get(key, default)

    @staticmethod
    def _validate(key, value):
        if key not in DEFAULTS:
            raise ValueError(f'Невідоме налаштування: {key}')
        valid = True
        if key == 'language':
            valid = value in ('ru', 'en')
        elif key in ('microphone', 'camera'):
            valid = (value is None and key == 'microphone') or (type(value) is int and value >= 0)
        elif key in ('smoothing', 'sensitivity'):
            valid = type(value) in (int, float) and math.isfinite(value) and (
                0 < value <= 1 if key == 'smoothing' else .25 <= value <= 2)
        else:
            valid = type(value) is bool
        if not valid:
            raise ValueError(f'Некоректне значення налаштування: {key}')

    def set(self, key, value):
        if self.error:
            raise ValueError(self.error)
        self._validate(key, value)
        values = {**self.values, key: value}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='settings-', suffix='.tmp', delete=False) as output:
                temp = Path(output.name)
                json.dump({'version': 1, 'settings': values}, output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, self.path)
            self.values = values
        finally:
            if temp is not None and temp.exists():
                temp.unlink()
