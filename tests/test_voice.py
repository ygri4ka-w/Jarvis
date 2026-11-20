import json
import threading
import time
import numpy as np
import pytest
from PySide6.QtCore import Qt


def test_waveform_is_silent_or_proportional_to_real_pcm():
    from jarvis_voice.audio import waveform
    silence = waveform(bytes(640), 80)
    quiet = waveform(np.full(320, 1000, dtype='<i2').tobytes(), 80)
    loud = waveform(np.full(320, 10000, dtype='<i2').tobytes(), 80)
    assert len(loud) == 80
    assert max(silence) == 0
    assert max(loud) == pytest.approx(10 * max(quiet))
    assert max(loud) <= 1


def test_inbox_overflow_fails_instead_of_executing_stale_audio():
    from jarvis_voice.audio import AudioInbox
    inbox = AudioInbox(capacity=2)
    for _ in range(3):
        inbox.callback(bytes(640), 320, None, None)
    assert inbox.failed.is_set()
    assert inbox.blocks.qsize() <= 2


class FakeStream:
    def __init__(self, callback):
        self.callback = callback
        self.closed = False
        self.active = True
    def __enter__(self):
        self.callback(np.full(320, 4000, dtype='<i2').tobytes(), 320, None, None)
        return self
    def __exit__(self, *args):
        self.closed = True
        self.active = False


class FakeRecognizer:
    def AcceptWaveform(self, data):
        return True
    def Result(self):
        return json.dumps({'text': 'джарвіс который час'})
    def PartialResult(self):
        return json.dumps({'partial': ''})


def test_worker_passes_final_text_real_wave_and_releases_stream():
    from jarvis_voice.worker import VoiceWorker
    streams, results = [], []
    def source(device, inbox):
        stream = FakeStream(inbox.callback)
        streams.append(stream)
        return stream, 16000
    worker = VoiceWorker(source_factory=source, recognizer_factory=lambda rate: FakeRecognizer())
    worker.recognized.connect(lambda text, timestamp: results.append(text), Qt.DirectConnection)
    worker.start()
    try:
        deadline = time.monotonic() + 2
        while not results and time.monotonic() < deadline:
            time.sleep(.01)
        assert results == ['джарвіс который час']
        assert max(worker.take_wave()) > 0
    finally:
        worker.stop()
        assert worker.wait(2000)
    assert streams[0].closed


def test_stop_while_loading_does_not_open_microphone():
    from jarvis_voice.worker import VoiceWorker
    entered, resume = threading.Event(), threading.Event()
    stream = FakeStream(lambda *args: None)
    def recognizer(rate):
        entered.set()
        resume.wait(2)
        return FakeRecognizer()
    opened = []
    stream.__class__ = type('TrackedStream', (FakeStream,), {'__enter__': lambda self: opened.append(True) or self})
    worker = VoiceWorker(source_factory=lambda device, inbox: (stream, 16000), recognizer_factory=recognizer)
    worker.start()
    try:
        assert entered.wait(2)
        worker.stop()
    finally:
        resume.set()
        assert worker.wait(2000)
    assert not opened


def test_missing_model_gives_actionable_error(tmp_path):
    from jarvis_voice.recognition import load_recognizer
    with pytest.raises(RuntimeError, match='модел'):
        load_recognizer(16000, tmp_path / 'missing')


def test_worker_discards_partial_recognition_and_late_final_on_stop():
    from jarvis_voice.worker import VoiceWorker
    entered, resume = threading.Event(), threading.Event()
    results = []
    class SlowRecognizer(FakeRecognizer):
        def AcceptWaveform(self, data):
            entered.set()
            resume.wait(2)
            return True
    worker = VoiceWorker(source_factory=lambda device, inbox: (FakeStream(inbox.callback), 16000),
                         recognizer_factory=lambda rate: SlowRecognizer())
    worker.recognized.connect(lambda text, timestamp: results.append(text), Qt.DirectConnection)
    worker.start()
    try:
        assert entered.wait(2)
        worker.stop()
    finally:
        resume.set()
        assert worker.wait(2000)
    assert results == []


@pytest.mark.parametrize('failure', ['open', 'disconnect', 'overflow', 'model'])
def test_worker_reports_one_error_and_releases_opened_stream(failure):
    from jarvis_voice.worker import VoiceWorker
    errors, streams = [], []
    class BrokenStream(FakeStream):
        def __enter__(self):
            if failure == 'open':
                raise RuntimeError('Не вдалося відкрити мікрофон')
            if failure == 'disconnect':
                self.active = False
            elif failure == 'overflow':
                for _ in range(230):
                    self.callback(bytes(640), 320, None, None)
            return self
    def source(device, inbox):
        stream = BrokenStream(inbox.callback)
        streams.append(stream)
        return stream, 16000
    def recognizer(rate):
        if failure == 'model':
            raise RuntimeError('Не знайдено модель')
        return FakeRecognizer()
    worker = VoiceWorker(source_factory=source, recognizer_factory=recognizer)
    worker.error.connect(errors.append, Qt.DirectConnection)
    worker.start()
    assert worker.wait(2000)
    assert len(errors) == 1
    if failure in ('disconnect', 'overflow'):
        assert streams[0].closed


def test_disconnect_during_decode_does_not_execute_result():
    from jarvis_voice.worker import VoiceWorker
    streams, results, errors = [], [], []
    def source(device, inbox):
        stream = FakeStream(inbox.callback)
        streams.append(stream)
        return stream, 16000
    class DisconnectRecognizer(FakeRecognizer):
        def AcceptWaveform(self, data):
            streams[0].active = False
            return True
    worker = VoiceWorker(source_factory=source, recognizer_factory=lambda rate: DisconnectRecognizer())
    worker.recognized.connect(lambda text, timestamp: results.append(text), Qt.DirectConnection)
    worker.error.connect(errors.append, Qt.DirectConnection)
    worker.start()
    assert worker.wait(2000)
    assert not results
    assert len(errors) == 1
    assert streams[0].closed


