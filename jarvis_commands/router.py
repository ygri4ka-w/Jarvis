from dataclasses import dataclass
import re
from jarvis_voice.languages import language_profile

COMMANDS = language_profile('ru')['commands']
WAKE_WORDS = set(language_profile('ru')['wake_words'])


def normalize_phrase(text):
    return ' '.join(re.findall(r"[\w’']+", text.casefold().replace('ё', 'е')))


@dataclass(frozen=True)
class Decision:
    command: str | None = None
    status: str = 'idle'


class CommandGate:
    """Accept final utterances only, with one command per wake activation."""
    def __init__(self, commands=None, language='ru', wake_required=True):
        profile = language_profile(language)
        self.language, self.wake_required = language, wake_required
        self.wake_words = set(profile['wake_words'])
        self.commands = dict(profile['commands'] if commands is None else commands)
        self.deadline = 0.0
        self.last_command = None
        self.last_time = float('-inf')

    def armed(self, now):
        return self.deadline > now

    def accept(self, text: str, now: float) -> Decision:
        words = normalize_phrase(text).split()
        if not words:
            return Decision(status='armed' if self.armed(now) else 'idle')
        if words[0] in self.wake_words:
            words = words[1:]
            if not words:
                self.deadline = now + 5
                return Decision(status='armed')
        elif self.wake_required and not self.armed(now):
            self.deadline = 0
            return Decision()
        self.deadline = 0
        command = self.commands.get(' '.join(words))
        if command is None:
            return Decision(status='unknown')
        if command == self.last_command and now - self.last_time < 2:
            return Decision(status='duplicate')
        self.last_command, self.last_time = command, now
        return Decision(command, 'command')

