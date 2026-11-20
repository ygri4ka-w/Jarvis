# JARVIS Variant 1 UI Design

## Scope
Создать первый запускаемый desktop-каркас JARVIS для Windows по утверждённому «Варианту 1 — Панель управления». Камера, MediaPipe и распознавание речи пока не подключаются.

## Architecture
`AssistantState` хранит runtime-состояние. `JarvisWindow` отвечает за компоновку и связывает кнопки с состоянием. `StatusCard` — переиспользуемая UI-компонента. `ui_spec.py` хранит декларативный состав бокового меню и карточек. `theme.py` хранит QSS-тему.

## UI
Слева вертикальное меню. В центре четыре статусные карточки 2×2 и панель последней команды. Справа журнал событий. Снизу основная кнопка запуска/остановки и кнопка настроек.

## Constraints
- Windows 10/11 target.
- Python 3.10+.
- PySide6/Qt Widgets.
- Ukrainian UI copy.
- Dark cyan Jarvis visual language.
- Offline-first architecture.
- No camera/voice implementation in this milestone.
