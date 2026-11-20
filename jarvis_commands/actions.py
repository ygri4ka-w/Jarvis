from dataclasses import dataclass
from datetime import datetime
import subprocess
from pathlib import Path


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    stop: bool = False
    shutdown: bool = False
    close: bool = False


def open_browser(url):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    return QDesktopServices.openUrl(QUrl(url))


class ActionRunner:
    def __init__(self, launch=subprocess.Popen, browse=open_browser, now=datetime.now):
        self.launch, self.browse, self.now = launch, browse, now

    def execute_custom(self, executable, action_type='exe'):
        if action_type == 'url':
            from .store import validate_url
            try:
                url = validate_url(executable)
                opened = bool(self.browse(url))
                return ActionResult(opened, 'Надіслано запит на відкриття сайту' if opened else 'Не вдалося відкрити сайт')
            except (ValueError, OSError, RuntimeError):
                return ActionResult(False, 'Не вдалося відкрити сайт. Перевірте адресу.')
        if action_type != 'exe':
            return ActionResult(False, 'Невідомий тип власної команди')
        path = Path(executable)
        if not path.is_absolute() or path.suffix.lower() != '.exe' or not path.is_file():
            return ActionResult(False, 'Файл програми не знайдено. Змініть шлях у власній команді.')
        try:
            self.launch([str(path)], cwd=str(path.parent))
            return ActionResult(True, f'Надіслано запит на запуск: {path.name}')
        except (OSError, RuntimeError):
            return ActionResult(False, 'Не вдалося запустити програму. Перевірте файл і права доступу.')

    def execute(self, command: str) -> ActionResult:
        try:
            if command == 'close_application':
                return ActionResult(True, 'Завершення JARVIS', close=True)
            if command == 'youtube':
                if not self.browse('https://www.youtube.com'):
                    return ActionResult(False, 'Не вдалося відкрити YouTube')
                return ActionResult(True, 'Надіслано запит на відкриття YouTube')
            if command == 'shutdown':
                return ActionResult(True, 'Отримано голосову команду вимкнення комп’ютера', shutdown=True)
            if command == 'calculator':
                self.launch(['calc.exe'])
                return ActionResult(True, 'Надіслано запит на відкриття калькулятора')
            if command == 'notepad':
                self.launch(['notepad.exe'])
                return ActionResult(True, 'Надіслано запит на відкриття блокнота')
            if command == 'browser':
                if not self.browse('https://www.google.com'):
                    return ActionResult(False, 'Не вдалося відкрити браузер')
                return ActionResult(True, 'Надіслано запит на відкриття браузера')
            if command == 'time':
                return ActionResult(True, f'Зараз {self.now():%H:%M}')
            if command == 'stop':
                return ActionResult(True, 'Асистента зупинено голосовою командою', stop=True)
        except (OSError, RuntimeError):
            return ActionResult(False, 'Не вдалося виконати команду. Перевірте наявність програми.')
        return ActionResult(False, 'Невідома команда')
