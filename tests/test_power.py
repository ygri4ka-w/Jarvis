from test_camera_ui import app
def test_shutdown_requires_explicit_confirmation():
    from jarvis_commands.power import request_shutdown
    calls = []
    assert not request_shutdown(False, run=lambda *args, **kw: calls.append(args)).ok
    assert calls == []
    result = request_shutdown(True, run=lambda args, **kwargs: calls.append((args, kwargs)))
    assert result.ok
    assert calls[0][0] == ['shutdown.exe', '/s', '/t', '0']
    assert '/f' not in calls[0][0]


def test_voice_shutdown_dispatch_only_requests_confirmation():
    from jarvis_commands.router import CommandGate
    from jarvis_commands.actions import ActionRunner
    calls = []
    decision = CommandGate().accept('джарвис выключи компьютер', 1)
    assert decision.command == 'shutdown'
    result = ActionRunner(launch=lambda args: calls.append(args)).execute(decision.command)
    assert result.shutdown
    assert calls == []


def test_shutdown_dialog_cancel_and_confirm_use_only_mock(app, monkeypatch):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from jarvis_commands.actions import ActionResult
    import jarvis_ui.window as module
    from test_voice_ui import make_window
    confirmations = []
    def fake_shutdown(confirmed):
        confirmations.append(confirmed)
        return ActionResult(confirmed, 'Test only')
    monkeypatch.setattr(module, 'request_shutdown', fake_shutdown)
    window = make_window()
    for caption in ('Скасувати', 'Вимкнути'):
        def choose(caption=caption):
            prompt = QApplication.activeModalWidget()
            next(button for button in prompt.buttons() if button.text() == caption).click()
        QTimer.singleShot(0, choose)
        window.confirm_shutdown()
    assert confirmations == [False, True]
    window.close()

