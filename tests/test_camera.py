import threading
import time

import numpy as np
import pytest


class FakeDevice:
    def __init__(self, opened=True, fail_after=None, raises=False):
        self.opened = opened
        self.fail_after = fail_after
        self.raises = raises
        self.reads = 0
        self.releases = 0

    def isOpened(self):
        return self.opened

    def read(self):
        self.reads += 1
        if self.raises:
            raise RuntimeError('driver failure')
        if self.fail_after is not None and self.reads > self.fail_after:
            return False, None
        return True, np.full((48, 64, 3), (10, 20, 30), dtype=np.uint8)

    def release(self):
        self.releases += 1


def test_capture_reads_and_releases_once():
    from jarvis_camera.capture import Capture
    device = FakeDevice()
    capture = Capture(0, lambda index: device)
    capture.open()
    assert capture.read()[0, 0].tolist() == [10, 20, 30]
    capture.close()
    capture.close()
    assert device.releases == 1


@pytest.mark.parametrize('device', [FakeDevice(opened=False), FakeDevice(fail_after=0), FakeDevice(raises=True)])
def test_capture_errors_release_device(device):
    from jarvis_camera.capture import Capture, CameraError
    capture = Capture(0, lambda index: device)
    with pytest.raises(CameraError):
        try:
            capture.open()
            capture.read()
        finally:
            capture.close()
    assert device.releases == 1


def test_worker_latest_rgb_frame_and_stop():
    from jarvis_camera.worker import CameraWorker
    device = FakeDevice()
    processed = threading.Event()
    def processor(frame):
        processed.set()
        return frame
    worker = CameraWorker(0, lambda index: device, processor)
    worker.start()
    try:
        assert processed.wait(2)
        deadline = time.monotonic() + 2
        frame = None
        while frame is None and time.monotonic() < deadline:
            frame = worker.take_frame()
            time.sleep(.01)
        assert frame[0, 0].tolist() == [30, 20, 10]
    finally:
        worker.stop()
        assert worker.wait(2000)
    worker.take_frame()
    assert worker.take_frame() is None
    assert device.releases == 1


def test_worker_stop_before_start_does_not_open_device():
    from jarvis_camera.worker import CameraWorker
    opened = []
    worker = CameraWorker(0, lambda index: opened.append(index))
    worker.stop()
    worker.start()
    assert worker.wait(2000)
    assert opened == []
