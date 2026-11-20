from pathlib import Path
import sys
import json
from .languages import language_profile

MODEL_NAME = 'vosk-model-small-ru-0.22'


def model_path(language='ru'):
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    return root / 'models' / language_profile(language)['model']


def load_recognizer(rate, path=None, language='ru'):
    profile = language_profile(language)
    path = Path(path) if path is not None else model_path(language)
    if not (path / 'am' / 'final.mdl').is_file():
        raise RuntimeError(f'Не знайдено мовну модель ({profile["label"]}): {path}. Запустіть setup_models.py.')
    from vosk import Model, KaldiRecognizer
    try:
        model = Model(str(path))
        return VoskRecognizer(KaldiRecognizer(model, rate), rate)
    except Exception as exc:
        raise RuntimeError('Не вдалося завантажити мовну модель. Перевірте папку models.') from exc


class VoskRecognizer:
    """Streaming Vosk adapter with audio capture time for the wake gate."""
    def __init__(self, decoder, rate):
        self.decoder, self.rate = decoder, rate
        decoder.SetWords(True)
        self.input_timestamp = self.result_started_at = 0.0
        self._origin = None
        self._result = '{"text": ""}'

    def AcceptWaveform(self, pcm):
        if self._origin is None:
            self._origin = self.input_timestamp
        final = self.decoder.AcceptWaveform(pcm)
        if final:
            self._result = self.decoder.Result()
            result = json.loads(self._result)
            words = result.get('result') or []
            self.result_started_at = self._origin + words[0]['start'] if words else self.input_timestamp
        return final

    def Result(self):
        return self._result

    def PartialResult(self):
        return self.decoder.PartialResult()
