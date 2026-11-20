from contextlib import contextmanager
from queue import Queue, Full
from threading import Event, Lock
from time import monotonic
import numpy as np


def waveform(pcm: bytes, points=80) -> list[float]:
    """Peak envelope of actual mono int16 PCM; fixed scale, no AGC."""
    samples = np.abs(np.frombuffer(pcm, dtype='<i2').astype(np.float32)) / 32768
    if not samples.size:
        return [0.0] * points
    padded = np.pad(samples, (0, (-samples.size) % points))
    return padded.reshape(points, -1).max(axis=1).tolist()


class AudioInbox:
    def __init__(self, capacity=25, clock=monotonic):
        self.blocks = Queue(maxsize=capacity)
        self.failed = Event()
        self.decoding = Event()
        self.message = ''
        self._lock = Lock()
        self._wave = None
        self.clock = clock

    def callback(self, data, frames, timing, status):
        if self.failed.is_set():
            return
        if status:
            self.message = 'Втрачено частину звуку. Повторіть підключення мікрофона.'
            self.failed.set()
            return
        pcm = bytes(data)
        with self._lock:
            self._wave = waveform(pcm)
        if self.decoding.is_set():
            return
        try:
            self.blocks.put_nowait((self.clock(), pcm))
        except Full:
            self.message = 'Розпізнавання не встигає за звуком. Повторіть підключення.'
            self.failed.set()

    def take_wave(self):
        with self._lock:
            value, self._wave = self._wave, None
        return value


def input_devices():
    import sounddevice as sd
    return [(i, f'{d["name"]} ({sd.query_hostapis(d["hostapi"])["name"]})')
            for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]


def microphone_source(device, inbox):
    import sounddevice as sd
    info = sd.query_devices(device, 'input')
    rate = int(info['default_samplerate'])
    @contextmanager
    def stream():
        # Construction opens the device, so defer until after model loading.
        with sd.RawInputStream(device=device, samplerate=rate, channels=1,
                               dtype='int16', blocksize=max(1, rate // 20),
                               callback=inbox.callback) as active:
            yield active
    return stream(), rate
