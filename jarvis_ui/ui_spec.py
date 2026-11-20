from dataclasses import dataclass

@dataclass(frozen=True)
class NavItem:
    icon: str
    label: str

@dataclass(frozen=True)
class StatusCardSpec:
    key: str
    icon: str
    title: str
    description: str

NAV_ITEMS = (NavItem('⌂', 'Головна'), NavItem('≡', 'Команди'), NavItem('◉', 'Камера'), NavItem('⚙', 'Налаштування'))
STATUS_CARDS = (
    StatusCardSpec('camera', '◉', 'Камера', 'Локальний відеопотік'),
    StatusCardSpec('microphone', '◖', 'Мікрофон', 'Реальний рівень звуку'),
    StatusCardSpec('gestures', '◇', 'Жести', 'Відстеження руки'),
    StatusCardSpec('voice', '≋', 'Голос', 'Офлайн: російська / англійська'),
)
