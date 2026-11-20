import sys

from PySide6.QtWidgets import QApplication

from jarvis_ui.theme import APP_STYLESHEET
from jarvis_ui.window import JarvisWindow


def main() -> int:
    sys.excepthook = _record_exception
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    app.setStyleSheet(APP_STYLESHEET)

    window = JarvisWindow()
    window.show()
    return app.exec()


def _record_exception(kind, value, trace):
    import os
    from pathlib import Path
    import traceback
    log = Path(os.environ.get('APPDATA', str(Path.home()))) / 'JARVIS' / 'crash.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a', encoding='utf-8') as output:
        traceback.print_exception(kind, value, trace, file=output)
    sys.__excepthook__(kind, value, trace)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        _record_exception(*sys.exc_info())
        raise
