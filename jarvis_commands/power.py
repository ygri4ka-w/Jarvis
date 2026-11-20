import subprocess
from .actions import ActionResult


def request_shutdown(confirmed, run=subprocess.run):
    if not confirmed:
        return ActionResult(False, 'Вимкнення скасовано')
    try:
        # /t > 0 implies /f on Windows. Use zero and never force-close apps.
        run(['shutdown.exe', '/s', '/t', '0'], check=True, capture_output=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return ActionResult(True, 'Запит на вимкнення надіслано Windows')
    except (OSError, subprocess.SubprocessError):
        return ActionResult(False, 'Windows не вдалося вимкнути. Перевірте права доступу.')
