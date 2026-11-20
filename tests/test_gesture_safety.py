import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from test_gestures import hand


class Desktop:
    """Fake OS boundary: no test can touch the actual desktop."""
    def __init__(self):
        self.actions = []
        self.escape = False
    def move(self, x, y):
        self.actions.append(('move', x, y))
    def click(self, button):
        self.actions.append(('click', button))
    def scroll(self, steps):
        self.actions.append(('scroll', steps))
    def volume(self, direction):
        self.actions.append(('volume', direction))
    def escape_pressed(self):
        return self.escape


class Tracker:
    def __init__(self):
        self.points = hand()
        self.closed = False
        self.fail = False
    def detect(self, frame):
        if self.fail:
            raise RuntimeError('test detector failure')
        return (self.points, 'Right')
    def close(self):
        self.closed = True


class ProcessorTests(unittest.TestCase):
    def setUp(self):
        import jarvis_gestures
        self.assertTrue(hasattr(jarvis_gestures, 'GestureProcessor'), 'frame processor is missing')
        self.cls = jarvis_gestures.GestureProcessor
        self.desktop = Desktop()
        self.tracker = Tracker()
        self.now = 0.
        self.created_on = []
        self.processor = self.cls(adapter=self.desktop, tracker_factory=self.make_tracker,
                                  clock=lambda: self.now, start_monitor=False)
        self.frame = np.zeros((80,100,3), dtype=np.uint8)
        self.addCleanup(self.processor.close)
    def make_tracker(self):
        self.created_on.append(threading.get_ident())
        return self.tracker
    def process(self, pose, now):
        self.now = now
        self.tracker.points = hand(pose)
        return self.processor.process(self.frame.copy())

    def test_disabled_defaults_never_initialize_tracker_or_input(self):
        self.processor.process(self.frame)
        self.assertEqual(self.created_on, [])
        self.assertEqual(self.desktop.actions, [])
        self.assertFalse(self.processor.snapshot()['control'])

    def test_tracker_initializes_on_capture_thread_and_preview_only_has_no_input(self):
        self.processor.set_enabled(True, False)
        thread = threading.Thread(target=lambda: self.process('pointer', 1.))
        thread.start()
        thread.join()
        self.assertNotEqual(self.created_on[0], threading.get_ident())
        self.process('pointer', 2.)
        self.assertEqual(self.desktop.actions, [])
        self.assertEqual(len(self.processor.snapshot()['landmarks']), 21)

    def test_control_enable_requires_new_neutral_then_dispatches_click(self):
        self.processor.set_enabled(True, False)
        self.process('neutral', 0.)
        self.process('neutral', .2)
        self.processor.set_enabled(True, True)
        self.process('left', 1.)
        self.process('left', 1.2)
        self.assertEqual(self.desktop.actions, [])
        self.process('neutral', 2.)
        self.process('neutral', 2.2)
        self.process('right', 3.)
        self.process('right', 3.2)
        self.assertEqual(self.desktop.actions, [('click', 'right')])

    def test_error_returns_original_video_and_disables_control(self):
        self.processor.set_enabled(True, True)
        self.tracker.fail = True
        output = self.processor.process(self.frame)
        self.assertIs(output, self.frame)
        state = self.processor.snapshot()
        self.assertFalse(state['control'])
        self.assertTrue(state['error'])

    def test_escape_stops_control_even_without_camera_frames_or_window_focus(self):
        self.processor.close()
        self.processor = self.cls(adapter=self.desktop, tracker_factory=self.make_tracker)
        self.processor.set_enabled(True, True)
        self.desktop.escape = True
        deadline = time.monotonic()+1.
        while not self.processor.snapshot()['emergency_stopped'] and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.processor.snapshot()['emergency_stopped'])
        self.assertFalse(self.processor.snapshot()['control'])
        self.assertEqual(self.desktop.actions, [])

    def test_close_releases_tracker_and_can_reopen_for_camera_restart(self):
        self.processor.set_enabled(True, False)
        self.processor.process(self.frame)
        self.processor.close()
        self.assertTrue(self.tracker.closed)
        self.assertFalse(self.processor.snapshot()['control'])
        self.processor.set_enabled(True, False)
        self.processor.process(self.frame)
        self.assertEqual(len(self.created_on), 2)

    def test_missing_task_model_is_local_error_and_keeps_video_alive(self):
        with TemporaryDirectory() as folder:
            processor = self.cls(adapter=self.desktop, model_path=Path(folder)/'absent.task', start_monitor=False)
            self.addCleanup(processor.close)
            processor.set_enabled(True, False)
            self.assertIs(processor.process(self.frame), self.frame)
            self.assertIn('hand_landmarker.task', processor.snapshot()['error'])

    def test_disabling_control_discards_detection_already_in_flight(self):
        entered, resume = threading.Event(), threading.Event()
        self.processor.set_enabled(True, True)
        self.process('neutral', 0.)
        self.process('neutral', .2)
        self.process('left', 1.)
        original_detect = self.tracker.detect
        def delayed(frame):
            entered.set()
            resume.wait(2.)
            return original_detect(frame)
        self.tracker.detect = delayed
        thread = threading.Thread(target=lambda: self.process('left', 1.2))
        thread.start()
        self.assertTrue(entered.wait(1.))
        self.processor.set_enabled(True, False)
        resume.set()
        thread.join(2.)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.desktop.actions, [])

    def test_live_sensitivity_change_disarms_until_neutral_and_rejects_nan(self):
        self.assertTrue(hasattr(self.processor, 'set_sensitivity'))
        self.processor.set_enabled(True, True)
        self.process('neutral', 0.)
        self.process('neutral', .2)
        self.processor.set_sensitivity(2.)
        self.process('left', 1.)
        self.process('left', 1.2)
        self.assertEqual(self.desktop.actions, [])
        with self.assertRaises(ValueError):
            self.processor.set_sensitivity(float('nan'))


class NativeBoundaryTests(unittest.TestCase):
    def test_partial_click_injection_attempts_release_before_reporting_error(self):
        from jarvis_gestures.windows_input import WindowsInput
        batches = []
        class Send:
            def __call__(self, count, events, size):
                batches.append([(event.type, event.payload.mouse.flags) for event in events])
                return 1 if len(batches) == 1 else count
        class Api:
            SendInput = Send()
        adapter = WindowsInput()
        adapter._api = Api()
        with self.assertRaises(RuntimeError):
            adapter.click('left')
        self.assertEqual(batches, [[(0,2),(0,4)], [(0,4)]])

    def test_pointer_bounds_map_to_actual_screen_edges(self):
        from jarvis_gestures.windows_input import WindowsInput
        positions = []
        class Api:
            def GetSystemMetrics(self, metric):
                return 1920 if metric == 0 else 1080
            def SetCursorPos(self, x, y):
                positions.append((x,y))
                return 1
        adapter = WindowsInput()
        adapter._api = Api()
        adapter.move(0., 0.)
        adapter.move(1., 1.)
        self.assertEqual(positions, [(0,0), (1919,1079)])


if __name__ == '__main__':
    unittest.main()
