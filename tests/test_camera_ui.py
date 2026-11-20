import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import time
import threading
import pytest
from PySide6.QtWidgets import QApplication
from test_camera import FakeDevice


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    # The offscreen Qt plugin does not discover Windows fonts automatically.
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase
    font = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'segoeui.ttf'
    if application.platformName() == 'offscreen' and font.exists():
        assert QFontDatabase.addApplicationFont(str(font)) >= 0
    return application


def until(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    app.processEvents()
    assert predicate()


def test_window_stream_stop_restart_and_close(app):
    from jarvis_ui.window import JarvisWindow
    devices = []
    def factory(index):
        device = FakeDevice()
        devices.append(device)
        return device
    window = JarvisWindow(capture_factory=factory)
    window.show()
    try:
        window.nav_buttons[2].click()
        assert window.pages.currentWidget() is window.camera_panel
        window.toggle_button.click()
        assert window.state.camera != 'Активна'
        until(app, lambda: window.state.camera == 'Активна')
        assert window.camera_panel.preview.pixmap() is not None
        assert not window.camera_panel.preview.pixmap().isNull()
        assert window.state.gestures == 'Не підключені'
        window.toggle_button.click()
        until(app, lambda: window.camera_worker is None)
        assert devices[0].releases == 1
        assert window.camera_panel.preview.pixmap().isNull()
        window.toggle_button.click()
        until(app, lambda: window.state.camera == 'Активна')
        window.close()
        until(app, lambda: not window.isVisible())
        assert devices[1].releases == 1
    finally:
        window.close()
        until(app, lambda: window.camera_worker is None)


def test_open_failure_then_manual_retry(app):
    from jarvis_ui.window import JarvisWindow
    devices = [FakeDevice(opened=False), FakeDevice()]
    remaining = iter(devices)
    window = JarvisWindow(capture_factory=lambda index: next(remaining))
    try:
        window.toggle_button.click()
        until(app, lambda: window.camera_worker is None)
        assert window.state.camera == 'Помилка'
        assert window.state.running
        assert 'Не вдалося' in window.camera_panel.preview.text()
        assert window.camera_panel.retry_button.isEnabled()
        window.camera_panel.retry_button.click()
        until(app, lambda: window.state.camera == 'Активна')
    finally:
        window.close()
        until(app, lambda: window.camera_worker is None)
    assert all(device.releases == 1 for device in devices)


def test_lost_stream_clears_image_and_logs_once(app):
    from jarvis_ui.window import JarvisWindow
    device = FakeDevice(fail_after=5)
    window = JarvisWindow(capture_factory=lambda index: device)
    try:
        window.toggle_button.click()
        until(app, lambda: window.state.camera == 'Активна')
        until(app, lambda: window.camera_worker is None)
        assert window.state.camera == 'Помилка'
        assert window.camera_panel.preview.pixmap().isNull()
        assert sum('Помилка камери:' in e.message for e in window.state.events) == 1
    finally:
        window.close()


def test_close_waits_responsively_for_slow_device(app):
    from jarvis_ui.window import JarvisWindow
    entered = threading.Event()
    resume = threading.Event()
    class SlowDevice(FakeDevice):
        def read(self):
            entered.set()
            resume.wait(3)
            return super().read()
    device = SlowDevice()
    window = JarvisWindow(capture_factory=lambda index: device)
    window.show()
    try:
        window.toggle_button.click()
        until(app, entered.is_set)
        window.close()
        assert window.isVisible()
        assert not window.toggle_button.isEnabled()
        assert device.releases == 0
        app.processEvents()
    finally:
        resume.set()
        until(app, lambda: window.camera_worker is None)
        until(app, lambda: not window.isVisible())
    assert device.releases == 1
    assert not any('відеопотік активний' in event.message for event in window.state.events)


def test_preview_proportions_colors_and_visual_capture(app, tmp_path):
    from jarvis_ui.window import JarvisWindow
    from jarvis_ui.theme import APP_STYLESHEET
    app.setStyleSheet(APP_STYLESHEET)
    window = JarvisWindow(capture_factory=lambda index: FakeDevice())
    window.show()
    try:
        window.nav_buttons[2].click()
        window.toggle_button.click()
        until(app, lambda: window.state.camera == 'Активна')
        pixmap = window.camera_panel.preview.pixmap()
        assert abs(pixmap.width() / pixmap.height() - 4 / 3) < .02
        color = pixmap.toImage().pixelColor(pixmap.width() // 2, pixmap.height() // 2)
        assert (color.red(), color.green(), color.blue()) == (30, 20, 10)
        assert window.grab().save(str(tmp_path / 'camera-preview.png'))
        window.nav_buttons[0].click()
        app.processEvents()
        assert window.grab().save(str(tmp_path / 'dashboard.png'))
    finally:
        window.close()
        until(app, lambda: window.camera_worker is None)

