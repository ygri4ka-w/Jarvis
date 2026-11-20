from jarvis_ui.state import AssistantState


def test_initial_state_is_stopped_and_ready():
    state = AssistantState()

    assert state.running is False
    assert state.camera == "Готова"
    assert state.microphone == "Не підключений"
    assert state.gestures == "Не підключені"
    assert state.voice == "Не підключений"


def test_start_changes_runtime_statuses_and_adds_log():
    state = AssistantState()

    state.start()

    assert state.running is True
    assert state.camera == "Підключення…"
    assert state.microphone == "Не підключений"
    assert state.gestures == "Не підключені"
    assert state.voice == "Не підключений"
    assert state.events[-1].message == "Асистента запущено"


def test_stop_returns_to_ready_state_and_adds_log():
    state = AssistantState()
    state.start()

    state.stop()

    assert state.running is False
    assert state.camera == "Готова"
    assert state.microphone == "Не підключений"
    assert state.gestures == "Не підключені"
    assert state.voice == "Не підключений"
    assert state.events[-1].message == "Асистента зупинено"


def test_register_command_updates_last_command_and_event_log():
    state = AssistantState()

    state.register_command("Відкрий браузер")

    assert state.last_command == "Відкрий браузер"
    assert state.events[-1].message == "Команда: Відкрий браузер"

