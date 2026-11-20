from test_camera_ui import app, until


def test_shutdown_keeps_wake_requirement():
    from jarvis_commands.router import CommandGate
    gate = CommandGate()
    assert gate.accept('Джарвис, выключи компьютер!', 1).command == 'shutdown'
    assert gate.accept('Джарвис, выключи компьютер', 1.1).command is None
    for phrase in ('выключи компьютер', 'джарвис не выключи компьютер', 'он сказал выключи компьютер', 'открой браузер'):
        assert CommandGate().accept(phrase, 1).command is None


def test_voice_shutdown_has_no_dialog_and_ignores_stopped_assistant(app, monkeypatch):
    from test_voice_ui import make_window
    from jarvis_commands.actions import ActionResult
    import jarvis_ui.window as module
    calls = []
    monkeypatch.setattr(module, 'request_shutdown', lambda confirmed: calls.append(confirmed) or ActionResult(True, 'Test only'))
    def unexpected(*args):
        raise AssertionError('Voice shutdown must not display confirmation')
    monkeypatch.setattr(module.QMessageBox, 'exec', unexpected)
    window = make_window()
    try:
        window.toggle_button.click()
        window.voice.worker.recognized.emit('джарвис выключи компьютер', 10)
        assert calls == [True]
        window._stop_assistant()
        window.voice.worker.recognized.emit('джарвис выключи компьютер', 20)
        assert calls == [True]
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: window.camera_worker is None)
