from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Event:
    time: str
    message: str


@dataclass
class AssistantState:
    running: bool = False
    camera: str = "Готова"
    microphone: str = "Не підключений"
    gestures: str = "Не підключені"
    voice: str = "Не підключений"
    last_command: str = "—"
    events: list[Event] = field(default_factory=list)

    def _add_event(self, message: str) -> None:
        self.events.append(Event(datetime.now().strftime("%H:%M"), message))

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.camera = "Підключення…"
        self._add_event("Асистента запущено")

    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        self.camera = "Готова"
        self._add_event("Асистента зупинено")

    def register_command(self, command: str) -> None:
        command = command.strip()
        if not command:
            return
        self.last_command = command
        self._add_event(f"Команда: {command}")
