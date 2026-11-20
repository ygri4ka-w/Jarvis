import json
import pytest


def executable(tmp_path, name='My App.exe'):
    path = tmp_path / name
    path.write_bytes(b'fake exe; never executed')
    return str(path)


def test_store_crud_persistence_and_live_routing(tmp_path):
    from jarvis_commands.store import CommandStore
    from jarvis_commands.router import CommandGate
    store = CommandStore(tmp_path / 'commands.json')
    item = store.save('Открой мою программу!', executable(tmp_path))
    restored = CommandStore(store.path)
    assert restored.items == store.items
    gate = CommandGate(store.routes())
    assert gate.accept('джарвис открой мою программу', 1).command == 'custom:' + item.id
    updated = store.save('запусти программу', item.exe, item.id)
    assert updated.id == item.id
    gate.commands = store.routes()
    assert gate.accept('джарвис открой мою программу', 4).command is None
    assert gate.accept('джарвис запусти программу', 5).command == 'custom:' + item.id
    store.delete(item.id)
    assert CommandStore(store.path).items == []


@pytest.mark.parametrize('phrase', ['', '!!!', 'открой браузер', 'Джарвис открой игру'])
def test_rejects_empty_reserved_and_wake_prefixed_phrases(tmp_path, phrase):
    from jarvis_commands.store import CommandStore
    with pytest.raises(ValueError):
        CommandStore(tmp_path / 'commands.json').save(phrase, executable(tmp_path))


def test_duplicate_and_invalid_executable_are_rejected(tmp_path):
    from jarvis_commands.store import CommandStore
    store = CommandStore(tmp_path / 'commands.json')
    exe = executable(tmp_path)
    store.save('открой игру', exe)
    with pytest.raises(ValueError):
        store.save('ОТКРОЙ ИГРУ!', exe)
    with pytest.raises(ValueError):
        store.save('открой музыку', str(tmp_path / 'missing.exe'))
    with pytest.raises(ValueError):
        store.save('открой музыку', executable(tmp_path, 'not-executable.txt'))


def test_corrupt_config_preserved_and_failed_save_keeps_memory(tmp_path, monkeypatch):
    from jarvis_commands.store import CommandStore
    path = tmp_path / 'commands.json'
    path.write_text('{broken', encoding='utf-8')
    store = CommandStore(path)
    assert store.error
    with pytest.raises(ValueError):
        store.save('открой игру', executable(tmp_path))
    assert path.read_text() == '{broken'
    path.unlink()
    store = CommandStore(path)
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr('jarvis_commands.store.os.replace', fail)
    with pytest.raises(OSError):
        store.save('открой игру', executable(tmp_path))
    assert store.items == []


def test_custom_launch_uses_single_path_and_working_directory(tmp_path):
    from jarvis_commands.actions import ActionRunner
    calls = []
    path = executable(tmp_path)
    runner = ActionRunner(launch=lambda args, **kwargs: calls.append((args, kwargs)))
    assert runner.execute_custom(path).ok
    assert calls == [([path], {'cwd': str(tmp_path)})]
    (tmp_path / 'My App.exe').unlink()
    assert not runner.execute_custom(path).ok
    assert len(calls) == 1
