import json


class Decoder:
    def SetWords(self, enabled):
        self.words = enabled
    def AcceptWaveform(self, data):
        return True
    def Result(self):
        return json.dumps({'text': 'джарвис который час',
                           'result': [{'word': 'джарвис', 'start': .2, 'end': .6, 'conf': 1}]})
    def PartialResult(self):
        return '{"partial": "джарвис"}'


def test_vosk_adapter_returns_text_and_original_audio_time():
    from jarvis_voice.recognition import VoskRecognizer
    raw = Decoder()
    recognizer = VoskRecognizer(raw, 16000)
    recognizer.input_timestamp = 100.0
    assert recognizer.AcceptWaveform(bytes(1600 * 2))
    assert raw.words
    assert json.loads(recognizer.Result())['text'] == 'джарвис который час'
    assert abs(recognizer.result_started_at - 100.2) < .001
    assert json.loads(recognizer.PartialResult())['partial'] == 'джарвис'


def test_russian_commands_require_wake_and_ukrainian_no_longer_dispatches():
    from jarvis_commands.router import CommandGate
    assert CommandGate().accept('Джарвис, открой калькулятор', 1).command == 'calculator'
    assert CommandGate().accept('Джарвис, который час', 1).command == 'time'
    assert CommandGate().accept('Джарвис, останови ассистента', 1).command == 'stop'
    assert CommandGate().accept('открой калькулятор', 1).command is None
    assert CommandGate().accept('джарвіс відкрий калькулятор', 1).command is None
