"""Validated commands with atomic writes and a lossless legacy backup."""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
from uuid import uuid4
from jarvis_voice.languages import language_profile
from .router import normalize_phrase


def default_path():
    return Path(os.environ.get('APPDATA', str(Path.home()))) / 'JARVIS' / 'commands.json'


def validate_url(value):
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError('Введіть повну адресу сайту http:// або https:// без пробілів.')
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme.lower() in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password
        _ = parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Введіть повну адресу сайту http:// або https://.')
    return value


@dataclass(frozen=True)
class CustomCommand:
    id: str
    language: str
    phrases: tuple[str, ...]
    action_type: str
    target: str

    @property
    def phrase(self):
        return self.phrases[0]

    @property
    def exe(self):
        return self.target


class CommandStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_path()
        self.items = []
        self.error = ''
        try:
            if self.path.exists():
                original = self.path.read_bytes()
                data = json.loads(original.decode('utf-8'))
                if not isinstance(data, dict) or data.get('version') not in (1, 2) or not isinstance(data.get('commands'), list):
                    raise ValueError('Invalid schema')
                for entry in data['commands']:
                    if data['version'] == 1:
                        if set(entry) != {'id', 'phrase', 'exe'}:
                            raise ValueError('Invalid legacy fields')
                        entry = dict(id=entry['id'], language='ru', phrases=[entry['phrase']], action_type='exe', target=entry['exe'])
                    item = self._load_item(entry)
                    if any(old.id == item.id for old in self.items):
                        raise ValueError('Duplicate id')
                    self.items.append(item)
                if data['version'] == 1:
                    self._backup(original)
                    self._write(self.items)
        except (ValueError, TypeError, OSError, AttributeError, KeyError):
            self.items = []
            self.error = f'Не вдалося прочитати команди: {self.path}. Файл не змінено; виправте або перейменуйте його та перезапустіть JARVIS.'

    def _load_item(self, entry):
        if not isinstance(entry, dict) or set(entry) != {'id', 'language', 'phrases', 'action_type', 'target'}:
            raise ValueError('Invalid fields')
        if not isinstance(entry['id'], str) or not entry['id'] or not isinstance(entry['target'], str) or not entry['target']:
            raise ValueError('Invalid fields')
        language_profile(entry['language'])
        # Grandfather stored phrases that became reserved in a newer release.
        # They retain the user's action; only newly added phrases are reserved.
        phrases = self._phrases(entry['phrases'], language=entry['language'], allow_reserved=True)
        if entry['action_type'] not in ('exe', 'url'):
            raise ValueError('Invalid action')
        if entry['action_type'] == 'url':
            validate_url(entry['target'])
        # Existing executables may have moved: retain them for user repair.
        return CustomCommand(entry['id'], entry['language'], phrases, entry['action_type'], entry['target'])

    def _backup(self, original):
        base = self.path.with_suffix(self.path.suffix + '.v1.bak')
        backup = base
        index = 1
        while backup.exists():
            if backup.read_bytes() == original:
                return
            backup = base.with_name(base.name + f'.{index}')
            index += 1
        with backup.open('xb') as output:
            output.write(original)
            output.flush()
            os.fsync(output.fileno())

    def validate_phrase(self, phrase, item_id=None, language='ru', *, _allow_reserved=False):
        profile = language_profile(language)
        if not isinstance(phrase, str):
            raise ValueError('Фраза має бути текстом.')
        phrase = normalize_phrase(phrase)
        if not phrase or len(phrase) > 120:
            raise ValueError('Введіть фразу до 120 символів обраною мовою.')
        if phrase.split()[0] in profile['wake_words']:
            raise ValueError('Введіть фразу без звернення Jarvis / «Джарвис».')
        previous = self.get(item_id) if item_id is not None else None
        grandfathered = previous is not None and previous.language == language and phrase in previous.phrases
        if phrase in profile['commands'] and not (_allow_reserved or grandfathered):
            raise ValueError('Цю фразу вже використовує вбудована команда.')
        if any(item.language == language and phrase in item.phrases and item.id != item_id for item in self.items):
            raise ValueError('Команда з такою фразою вже існує.')
        return phrase

    def _phrases(self, phrases, item_id=None, language='ru', allow_reserved=False):
        if not isinstance(phrases, (list, tuple)) or not phrases:
            raise ValueError('Додайте принаймні одну фразу.')
        normalized = tuple(self.validate_phrase(value, item_id, language, _allow_reserved=allow_reserved) for value in phrases)
        if len(set(normalized)) != len(normalized):
            raise ValueError('Список містить повторювані фрази.')
        return normalized

    def save(self, phrase, exe, item_id=None, *, language='ru', phrases=None, action_type='exe', target=None):
        if self.error:
            raise ValueError(self.error)
        language_profile(language)
        phrases = self._phrases([phrase] if phrases is None else phrases, item_id, language)
        target = exe if target is None else target
        if action_type == 'exe':
            path = Path(target).expanduser()
            if not path.is_absolute() or path.suffix.lower() != '.exe' or not path.is_file():
                raise ValueError('Оберіть наявний файл програми .exe за повним шляхом.')
            target = str(path.resolve())
        elif action_type == 'url':
            target = validate_url(target)
        else:
            raise ValueError('Оберіть тип дії: програма EXE або сайт URL.')
        if item_id is not None and self.get(item_id) is None:
            raise ValueError('Команду вже видалено.')
        item = CustomCommand(item_id or uuid4().hex, language, phrases, action_type, target)
        items = [item if old.id == item.id else old for old in self.items]
        if item_id is None:
            items.append(item)
        self._write(items)
        return item

    def delete(self, item_id):
        if self.error:
            raise ValueError(self.error)
        self._write([item for item in self.items if item.id != item_id])

    def get(self, item_id):
        return next((item for item in self.items if item.id == item_id), None)

    def routes(self, language='ru'):
        return {**language_profile(language)['commands'],
                **{phrase: 'custom:' + item.id for item in self.items if item.language == language for phrase in item.phrases}}

    def _write(self, items):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='commands-', suffix='.tmp', delete=False) as output:
                temp = Path(output.name)
                json.dump({'version': 2, 'commands': [asdict(item) for item in items]}, output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, self.path)
            self.items = list(items)
        finally:
            if temp is not None and temp.exists():
                temp.unlink()
