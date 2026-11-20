import json
import pytest


def test_settings_persist_validated_preferences(tmp_path):
    from jarvis_settings import SettingsStore
    path = tmp_path / 'settings.json'
    store = SettingsStore(path)
    assert store.get('language') == 'ru'
    assert store.get('gesture_enabled') is False
    store.set('language', 'en')
    store.set('microphone', 7)
    store.set('smoothing', .5)
    loaded = SettingsStore(path)
    assert loaded.get('language') == 'en'
    assert loaded.get('microphone') == 7
    assert loaded.get('smoothing') == .5
    with pytest.raises(ValueError):
        store.set('language', 'xx')
    with pytest.raises(ValueError):
        store.set('smoothing', 2)
    assert SettingsStore(path).get('language') == 'en'


def test_corrupt_settings_not_overwritten(tmp_path):
    from jarvis_settings import SettingsStore
    path = tmp_path / 'settings.json'
    path.write_text('{broken', encoding='utf-8')
    store = SettingsStore(path)
    assert store.error
    assert store.get('language') == 'ru'
    with pytest.raises(ValueError):
        store.set('language', 'en')
    assert path.read_text() == '{broken'


def test_failed_atomic_settings_write_preserves_memory(tmp_path, monkeypatch):
    from jarvis_settings import SettingsStore
    store = SettingsStore(tmp_path / 'settings.json')
    store.set('language', 'en')
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr('jarvis_settings.store.os.replace', fail)
    with pytest.raises(OSError):
        store.set('language', 'ru')
    assert store.get('language') == 'en'
