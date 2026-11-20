from jarvis_ui.ui_spec import NAV_ITEMS, STATUS_CARDS


def test_sidebar_contains_functional_modern_sections():
    assert [item.label for item in NAV_ITEMS] == ['Головна', 'Команди', 'Камера', 'Налаштування']


def test_dashboard_contains_four_required_status_cards():
    assert [card.key for card in STATUS_CARDS] == ['camera', 'microphone', 'gestures', 'voice']
