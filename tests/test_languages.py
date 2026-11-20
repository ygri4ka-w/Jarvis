import pytest


@pytest.mark.parametrize('language,text,action', [
    ('ru', 'джарвис открой ютуб', 'youtube'),
    ('en', 'Jarvis open YouTube', 'youtube'),
    ('en', 'jarvis open calculator', 'calculator'),
    ('ru', 'джарвис закрой приложение', 'close_application'),
    ('en', 'jarvis close application', 'close_application'),
    ('en', 'jarvis shut down computer', 'shutdown'),
])
def test_language_specific_routes(language, text, action):
    from jarvis_commands.router import CommandGate
    assert CommandGate(language=language).accept(text, 10).command == action


def test_english_wake_gate_single_command_and_optional_activation():
    from jarvis_commands.router import CommandGate
    gate = CommandGate(language='en')
    assert gate.accept('open browser', 1).command is None
    assert gate.accept('jarvis', 2).status == 'armed'
    assert gate.accept('open browser', 3).command == 'browser'
    assert gate.accept('open calculator', 4).command is None
    assert gate.accept('jarvis открой браузер', 5).command is None
    assert CommandGate(language='en', wake_required=False).accept('open browser', 1).command == 'browser'
    with pytest.raises(ValueError):
        CommandGate(language='xx')


def test_language_model_paths():
    from jarvis_voice.recognition import model_path
    assert model_path('en').name == 'vosk-model-small-en-us-0.15'
    assert model_path('ru').name == 'vosk-model-small-ru-0.22'


def test_youtube_close_and_custom_url_never_launch_shell():
    from jarvis_commands.actions import ActionRunner
    opened = []
    runner = ActionRunner(launch=lambda *args, **kwargs: pytest.fail('Unexpected executable launch'),
                          browse=lambda url: opened.append(url) or True)
    assert runner.execute('youtube').ok
    assert runner.execute('close_application').close
    assert runner.execute_custom('https://example.com/a?q=b', action_type='url').ok
    assert not runner.execute_custom('javascript:alert(1)', action_type='url').ok
    assert opened == ['https://www.youtube.com', 'https://example.com/a?q=b']
