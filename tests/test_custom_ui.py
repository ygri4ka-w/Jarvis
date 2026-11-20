from test_camera_ui import app, until
from test_voice_ui import FakeVoice
from test_camera import FakeDevice
from test_custom_commands import executable


def test_editor_checks_vocabulary_saves_and_warns_for_unknown_words(app, tmp_path):
    from jarvis_commands.store import CommandStore
    from jarvis_ui.command_editor import CommandEditor
    store = CommandStore(tmp_path / 'commands.json')
    dialog = CommandEditor(store, checker=lambda phrase: [])
    dialog.phrase.setText('открой игру')
    dialog.exe.setText(executable(tmp_path))
    dialog.save_button.click()
    until(app, lambda: dialog.worker is None)
    assert store.items[0].phrase == 'открой игру'
    warning = CommandEditor(store, checker=lambda phrase: ['неизвестное'])
    warning.phrase.setText('открой неизвестное')
    warning.exe.setText(executable(tmp_path))
    warning.save_button.click()
    until(app, lambda: warning.worker is None)
    assert len(store.items) == 1
    assert 'неизвестное' in warning.message.text()
    warning.reject()


def test_custom_command_works_immediately_and_delete_removes_route(app, tmp_path):
    from jarvis_commands.store import CommandStore
    from jarvis_ui.window import JarvisWindow
    from jarvis_commands.actions import ActionRunner
    store = CommandStore(tmp_path / 'commands.json')
    window = JarvisWindow(capture_factory=lambda index: FakeDevice(), voice_worker_factory=FakeVoice,
                         device_provider=lambda: [], command_store=store)
    calls = []
    window.voice.runner = ActionRunner(launch=lambda args, **kw: calls.append(args))
    try:
        window.toggle_button.click()
        item = store.save('открой игру', executable(tmp_path))
        window.commands_changed()
        window.voice.worker.recognized.emit('джарвис открой игру', 10)
        assert calls == [[item.exe]]
        assert window.state.last_command == 'открой игру'
        store.delete(item.id)
        window.commands_changed()
        window.voice.worker.recognized.emit('джарвис открой игру', 20)
        assert len(calls) == 1
    finally:
        window.close()
        if window.voice.worker:
            window.voice.worker.finished.emit()
        until(app, lambda: window.camera_worker is None)


def test_cancel_while_vocabulary_loading_does_not_save(app, tmp_path):
    import threading
    from jarvis_commands.store import CommandStore
    from jarvis_ui.command_editor import CommandEditor
    resume = threading.Event()
    def checker(phrase):
        resume.wait(2)
        return []
    store = CommandStore(tmp_path / 'commands.json')
    dialog = CommandEditor(store, checker=checker)
    dialog.phrase.setText('открой игру')
    dialog.exe.setText(executable(tmp_path))
    dialog.save_button.click()
    dialog.reject()
    resume.set()
    until(app, lambda: dialog.worker is None)
    assert store.items == []


def test_manager_edit_delete_and_manual_launch(app, tmp_path):
    from jarvis_commands.store import CommandStore
    from jarvis_ui.command_manager import CommandManager
    store = CommandStore(tmp_path / 'commands.json')
    item = store.save('открой игру', executable(tmp_path))
    manager = CommandManager(store)
    ids = []
    manager.launch_requested.connect(ids.append)
    manager.list.setCurrentRow(0)
    manager.test_launch()
    assert ids == [item.id]
    manager.remove()
    assert manager.list.count() == 0
    assert not CommandStore(store.path).items


def test_custom_dialog_visuals(app, tmp_path):
    from jarvis_commands.store import CommandStore
    from jarvis_ui.command_manager import CommandManager
    from jarvis_ui.command_editor import CommandEditor
    from jarvis_ui.theme import APP_STYLESHEET
    app.setStyleSheet(APP_STYLESHEET)
    store = CommandStore(tmp_path / 'commands.json')
    store.save('открой игру', executable(tmp_path))
    manager = CommandManager(store)
    manager.show()
    app.processEvents()
    assert manager.grab().save(str(tmp_path / 'my-commands.png'))
    editor = CommandEditor(store, checker=lambda phrase: [])
    editor.phrase.setText('открой музыку')
    editor.exe.setText('D:\\Programs\\Music Player\\player.exe')
    editor.show()
    app.processEvents()
    assert editor.grab().save(str(tmp_path / 'add-command.png'))
    editor.close()
    manager.close()
