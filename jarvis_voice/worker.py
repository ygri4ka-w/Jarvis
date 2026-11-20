import json
from queue import Empty
from threading import Event
from time import monotonic
from PySide6.QtCore import QThread, Signal
from .audio import AudioInbox, microphone_source
from .recognition import load_recognizer
from .languages import language_profile
from inspect import signature, Parameter


def accepts_language(factory):
    """Keep pre-language injected factories usable without masking their errors."""
    parameters = signature(factory).parameters
    return 'language' in parameters or any(p.kind == Parameter.VAR_KEYWORD for p in parameters.values())


class VoiceWorker(QThread):
    recognized = Signal(str, float)
    partial = Signal(str)
    status = Signal(str)
    error = Signal(str)

    def __init__(self, device=None, source_factory=microphone_source,
                 recognizer_factory=load_recognizer, parent=None, language='ru'):
        super().__init__(parent)
        self.device = device
        self.language = language
        self.profile = language_profile(language)
        self.source_factory = source_factory
        self.recognizer_factory = recognizer_factory
        self.inbox = AudioInbox(capacity=200)
        self._stop = Event()

    def stop(self):
        self._stop.set()

    def take_wave(self):
        return self.inbox.take_wave()

    def _processing(self, active):
        if active:
            self.inbox.decoding.set()
            while True:
                try:
                    self.inbox.blocks.get_nowait()
                except Empty:
                    break
            self.status.emit('Розпізнаю… Зачекайте перед наступною фразою')
        else:
            self.inbox.decoding.clear()
            self.status.emit(self.waiting_text)

    @property
    def waiting_text(self):
        return 'Очікує «Jarvis»' if self.language == 'en' else 'Очікує «Джарвис»'

    def run(self):
        try:
            if self._stop.is_set():
                return
            self.status.emit('Завантаження моделі…')
            context, rate = self.source_factory(self.device, self.inbox)
            kwargs = {'language': self.language} if accepts_language(self.recognizer_factory) else {}
            recognizer = self.recognizer_factory(rate, **kwargs)
            if hasattr(recognizer, 'processing_hook'):
                recognizer.processing_hook = self._processing
            if self._stop.is_set():
                return
            with context as stream:
                self.status.emit(self.waiting_text)
                last_audio = monotonic()
                previous_partial = ''
                while not self._stop.is_set():
                    if self.inbox.failed.is_set():
                        raise RuntimeError(self.inbox.message)
                    if not stream.active:
                        raise RuntimeError('Мікрофон відключено. Перевірте пристрій і повторіть підключення.')
                    try:
                        captured_at, pcm = self.inbox.blocks.get(timeout=.1)
                    except Empty:
                        if monotonic() - last_audio > 3:
                            raise RuntimeError('Мікрофон не передає звук. Повторіть підключення.')
                        continue
                    last_audio = monotonic()
                    if last_audio - captured_at > 5:
                        raise RuntimeError('Звук надходить із завеликою затримкою. Повторіть підключення.')
                    recognizer.input_timestamp = captured_at
                    final = recognizer.AcceptWaveform(pcm)
                    if self._stop.is_set() or self.inbox.failed.is_set():
                        continue
                    if not stream.active:
                        raise RuntimeError('Мікрофон відключено під час розпізнавання. Повторіть підключення.')
                    if final:
                        text = json.loads(recognizer.Result()).get('text', '').strip()
                        previous_partial = ''
                        if text:
                            self.recognized.emit(text, getattr(recognizer, 'result_started_at', captured_at))
                    else:
                        text = json.loads(recognizer.PartialResult()).get('partial', '')
                        if text != previous_partial:
                            self.partial.emit(text)
                            previous_partial = text
        except Exception as exc:
            if not self._stop.is_set():
                message = str(exc) if isinstance(exc, RuntimeError) else (
                    'Не вдалося підключити мікрофон або обробити звук. '
                    'Перевірте пристрій, дозволи Windows та встановлення залежностей.')
                self.error.emit(message)

