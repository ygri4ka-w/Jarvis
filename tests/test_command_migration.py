import json
import pytest
from test_custom_commands import executable


def test_v1_migration_preserves_ids_missing_exes_and_exact_backup(tmp_path):
    from jarvis_commands.store import CommandStore
    path = tmp_path / 'commands.json'
    original = json.dumps({'version': 1, 'commands': [
        {'id': 'existing', 'phrase': 'Открой игру', 'exe': str(tmp_path / 'missing.exe')}]}).encode()
    path.write_bytes(original)
    store = CommandStore(path)
    assert not store.error
    item = store.get('existing')
    assert item.language == 'ru'
    assert tuple(item.phrases) == ('открой игру',)
    assert item.action_type == 'exe'
    assert item.exe == str(tmp_path / 'missing.exe')
    assert path.with_suffix('.json.v1.bak').read_bytes() == original
    assert json.loads(path.read_text(encoding='utf-8'))['version'] == 2
    assert CommandStore(path).items == store.items


def test_aliases_routes_languages_edit_and_duplicates(tmp_path):
    from jarvis_commands.store import CommandStore
    store = CommandStore(tmp_path / 'commands.json')
    item = store.save('my app', executable(tmp_path), language='en', phrases=['My app', 'start game'])
    assert store.routes('en')['start game'] == 'custom:' + item.id
    assert 'my app' not in store.routes('ru')
    with pytest.raises(ValueError):
        store.save('start game', item.exe, language='en')
    with pytest.raises(ValueError):
        store.save('other', item.exe, language='en', phrases=['other', 'open calculator'])
    store.save('start game', item.exe, language='ru')
    updated = store.save('my app', '', item.id, language='en', phrases=['my app', 'my site'],
                         action_type='url', target='https://example.com')
    assert updated.id == item.id
    assert 'start game' not in store.routes('en')
    assert CommandStore(store.path).get(item.id).target == 'https://example.com'


@pytest.mark.parametrize('url', ['javascript:alert(1)', 'file:///C:/Windows', 'https://', 'https://a b.com'])
def test_invalid_urls_rejected(tmp_path, url):
    from jarvis_commands.store import CommandStore
    with pytest.raises(ValueError):
        CommandStore(tmp_path / 'commands.json').save('site', '', language='en', action_type='url', target=url)


def test_corrupt_migration_preserves_source_without_partial_items(tmp_path):
    from jarvis_commands.store import CommandStore
    path = tmp_path / 'commands.json'
    original = json.dumps({'version': 1, 'commands': [
        {'id': 'one', 'phrase': 'открой игру', 'exe': 'missing.exe'},
        {'id': 'two', 'phrase': 'открой игру', 'exe': 'another.exe'}]})
    path.write_text(original, encoding='utf-8')
    store = CommandStore(path)
    assert store.error
    assert store.items == []
    assert path.read_text(encoding='utf-8') == original


def test_legacy_phrase_collision_keeps_custom_action_and_new_reserved_phrases_rejected(tmp_path):
    from jarvis_commands.store import CommandStore
    path = tmp_path / 'commands.json'
    exe = executable(tmp_path)
    original = json.dumps({'version': 1, 'commands': [
        {'id': 'old-youtube', 'phrase': 'открой ютуб', 'exe': exe}]}).encode()
    path.write_bytes(original)
    store = CommandStore(path)
    assert not store.error
    assert store.routes()['открой ютуб'] == 'custom:old-youtube'
    assert path.with_suffix('.json.v1.bak').read_bytes() == original
    restored = CommandStore(path)
    assert restored.routes()['открой ютуб'] == 'custom:old-youtube'
    restored.save('открой ютуб', exe, 'old-youtube')
    with pytest.raises(ValueError):
        restored.save('закрой приложение', exe)
    restored.delete('old-youtube')
    assert restored.routes()['открой ютуб'] == 'youtube'
