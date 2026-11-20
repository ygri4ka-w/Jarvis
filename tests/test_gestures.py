"""Synthetic landmarks exercise gestures without a camera or native input."""
import importlib.util
import unittest


def hand(pose='neutral', x=.5, y=.7):
    points = [(x, y, 0.) for _ in range(21)]
    points[0] = (x, y, 0.)
    for base, dx in [(5, -.10), (9, 0.), (13, .08), (17, .14)]:
        points[base] = (x + dx, y - .20, 0.)
        points[base + 1] = (x + dx, y - .28, 0.)
        points[base + 2] = (x + dx, y - .34, 0.)
        points[base + 3] = (x + dx, y - .42, 0.)
    points[2], points[3], points[4] = (x-.16,y-.08,0.), (x-.23,y-.15,0.), (x-.28,y-.22,0.)
    raised = {'neutral': {8,12,16,20}, 'pointer': {8}, 'scroll': {8,12},
              'left': {8}, 'right': {12}, 'ambiguous': {8,12}}.get(pose, set())
    for tip in (8, 12, 16, 20):
        if tip not in raised:
            points[tip] = (points[tip][0], y-.12, 0.)
    if pose in ('left', 'right', 'ambiguous'):
        points[4] = (x-.1, y-.42, 0.)
        if pose in ('left', 'ambiguous'):
            points[8] = (x-.09, y-.42, 0.)
        if pose in ('right', 'ambiguous'):
            points[12] = (x-.11, y-.42, 0.)
    if pose in ('volume_up', 'volume_down'):
        points[3] = (x-.2,y-.10,0.)
        points[4] = (x-.2, y + (-.35 if pose == 'volume_up' else .18), 0.)
    return points


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('jarvis_gestures'), 'gesture subsystem is missing')
        from jarvis_gestures import GestureEngine
        self.engine = GestureEngine(smoothing=.25)
        self.engine.update(hand(), 0., 'right')
        self.engine.update(hand(), .2, 'right')

    def clicks(self, pose, start=1.):
        self.engine.update(hand(pose), start, 'right')
        return self.engine.update(hand(pose), start+.2, 'right').actions

    def test_index_pinch_clicks_once_until_release(self):
        self.assertEqual(self.clicks('left'), [('click', 'left')])
        self.assertEqual(self.engine.update(hand('left'), 5., 'right').actions, [])
        self.engine.update(hand(), 6., 'right')
        self.engine.update(hand(), 6.2, 'right')
        self.assertEqual(self.clicks('left', 7.), [('click', 'left')])

    def test_middle_pinch_is_right_button(self):
        self.assertEqual(self.clicks('right'), [('click', 'right')])

    def test_double_pinch_cannot_click_or_transition_directly_to_click(self):
        self.assertEqual(self.clicks('ambiguous'), [])
        self.assertEqual(self.clicks('left', 2.), [])

    def test_lost_or_changed_hand_requires_neutral_rearm(self):
        self.engine.update(None, 1.)
        self.assertEqual(self.clicks('left', 2.), [])
        self.engine.update(hand(), 3., 'right')
        self.engine.update(hand(), 3.2, 'right')
        self.assertEqual(self.clicks('left', 4.), [('click', 'left')])
        self.engine.update(hand('right'), 6., 'left')
        self.assertEqual(self.engine.update(hand('right'), 7., 'left').actions, [])

    def test_pointer_is_mirrored_once_clamped_and_smoothed(self):
        self.engine.update(hand('pointer', x=.3), 1., 'right')
        first = self.engine.update(hand('pointer', x=.3), 1.2, 'right')
        self.assertEqual(first.actions[0][0], 'move')
        self.assertAlmostEqual(first.actions[0][1], .875)
        second = self.engine.update(hand('pointer', x=.7), 1.3, 'right')
        self.assertAlmostEqual(second.actions[0][1], .75)
        self.engine.reset()
        self.engine.update(hand(x=.1), 2., 'right')
        self.engine.update(hand(x=.1), 2.2, 'right')
        self.engine.update(hand('pointer', x=.1), 3., 'right')
        self.assertEqual(self.engine.update(hand('pointer', x=.1), 3.2, 'right').actions[0][1], 1.)

    def test_scroll_is_exclusive_and_direction_tracks_hand(self):
        self.engine.update(hand('scroll'), 1., 'right')
        self.engine.update(hand('scroll'), 1.2, 'right')
        result = self.engine.update(hand('scroll', y=.58), 1.4, 'right')
        self.assertTrue(result.actions)
        self.assertTrue(all(action[0] == 'scroll' and action[1] > 0 for action in result.actions))

    def test_volume_is_exclusive_and_rate_limited(self):
        self.engine.update(hand('volume_up'), 1., 'right')
        self.assertEqual(self.engine.update(hand('volume_up'), 1.2, 'right').actions, [('volume', 1)])
        self.assertEqual(self.engine.update(hand('volume_up'), 1.21, 'right').actions, [])
        self.engine.update(hand('volume_down'), 2., 'right')
        self.assertEqual(self.engine.update(hand('volume_down'), 2.2, 'right').actions, [('volume', -1)])

    def test_invalid_landmarks_are_hand_loss(self):
        self.assertEqual(self.engine.update([(float('nan'), 0, 0)] * 21, 1.).actions, [])
        self.assertEqual(self.clicks('left', 2.), [])

    def test_pinch_jitter_does_not_release_click_latch(self):
        self.assertEqual(self.clicks('left'), [('click', 'left')])
        jitter = hand('left')
        jitter[8] = (.46, .28, 0.)  # 0.30 palm lengths: outside close, inside release.
        self.engine.update(jitter, 2., 'right')
        self.engine.update(jitter, 2.2, 'right')
        self.assertEqual(self.clicks('left', 3.), [])

    def test_new_hand_jump_cannot_click_under_same_handedness_label(self):
        shifted = hand('left', x=1.1)
        self.engine.update(shifted, 1., 'right')
        self.assertEqual(self.engine.update(shifted, 1.2, 'right').actions, [])

    def test_sensitivity_changes_pinch_tolerance_after_neutral_rearm(self):
        self.assertTrue(hasattr(self.engine, 'set_sensitivity'))
        loose_pinch = hand('left')
        loose_pinch[8] = (.46, .28, 0.)  # 0.30 palm lengths.
        self.engine.update(loose_pinch, 1., 'right')
        self.assertFalse(any(a[0] == 'click' for a in self.engine.update(loose_pinch, 1.2, 'right').actions))
        self.engine.set_sensitivity(1.5)
        self.engine.update(loose_pinch, 2., 'right')
        self.assertEqual(self.engine.update(loose_pinch, 2.2, 'right').actions, [])
        self.engine.update(hand(), 3., 'right')
        self.engine.update(hand(), 3.2, 'right')
        self.engine.update(loose_pinch, 4., 'right')
        self.assertEqual(self.engine.update(loose_pinch, 4.2, 'right').actions, [('click', 'left')])

    def test_higher_sensitivity_scrolls_with_smaller_hand_movement(self):
        self.assertTrue(hasattr(self.engine, 'set_sensitivity'))
        self.engine.set_sensitivity(2.)
        self.engine.update(hand(), 0., 'right')
        self.engine.update(hand(), .2, 'right')
        self.engine.update(hand('scroll'), 1., 'right')
        self.engine.update(hand('scroll'), 1.2, 'right')
        self.assertEqual(self.engine.update(hand('scroll', y=.675), 1.4, 'right').actions, [('scroll', 1)])


if __name__ == '__main__':
    unittest.main()
