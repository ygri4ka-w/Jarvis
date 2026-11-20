from datetime import datetime
import pytest


@pytest.mark.parametrize('phrase,expected', [
    ('Джарвіс, открой калькулятор!', 'calculator'),
    ('джарвіс открой блокнот', 'notepad'),
    ('джарвіс открой браузер', 'browser'),
    ('джарвіс который час', 'time'),
    ('джарвіс останови ассистента', 'stop'),
    ('Jarvis, который час?', 'time'),
    ('Джарвис, открой блокнот', 'notepad'),
    ('Джарвісе, который час', 'time'),
    ('открой калькулятор', None),
    ('не відкривай калькулятор', None),
    ('джарвіс не открой калькулятор', None),
    ('хтось сказав джарвіс открой браузер', None),
    ('джарвіс открой браузер і блокнот', None),
])
def test_exact_wake_gated_commands(phrase, expected):
    from jarvis_commands.router import CommandGate
    assert CommandGate().accept(phrase, 10).command == expected


def test_wake_timeout_single_use_and_duplicate_filter():
    from jarvis_commands.router import CommandGate
    gate = CommandGate()
    assert gate.accept('джарвіс', 0).status == 'armed'
    assert gate.accept('который час', 4).command == 'time'
    assert gate.accept('открой браузер', 4.1).command is None
    assert gate.accept('джарвіс который час', 4.2).command is None
    gate.accept('джарвіс', 8)
    assert gate.accept('открой браузер', 13.1).command is None
    assert gate.accept('джарвіс который час', 14).command == 'time'


def test_action_dispatch_uses_fixed_arguments_and_reports_failure():
    from jarvis_commands.actions import ActionRunner
    calls = []
    runner = ActionRunner(launch=lambda args: calls.append(args), browse=lambda url: False,
                          now=lambda: datetime(2026, 9, 10, 12, 34))
    assert runner.execute('calculator').ok
    assert runner.execute('notepad').ok
    assert calls == [['calc.exe'], ['notepad.exe']]
    assert '12:34' in runner.execute('time').message
    assert not runner.execute('browser').ok
    assert not runner.execute('calc.exe & malicious').ok
    assert runner.execute('stop').stop


def test_launch_error_becomes_result():
    from jarvis_commands.actions import ActionRunner
    def fail(args):
        raise OSError('missing')
    assert not ActionRunner(launch=fail).execute('notepad').ok

