import unittest

from sflkitlib.events import EventType


class TestEvents(unittest.TestCase):
    def test_normal_events(self):
        self.assertEqual(
            EventType.events(),
            {
                EventType.LINE,
                EventType.BRANCH,
                EventType.FUNCTION_ENTER,
                EventType.FUNCTION_EXIT,
                EventType.FUNCTION_ERROR,
                EventType.DEF,
                EventType.USE,
                EventType.CONDITION,
                EventType.LOOP_BEGIN,
                EventType.LOOP_HIT,
                EventType.LOOP_END,
                EventType.LEN,
            },
        )

    def test_test_events(self):
        self.assertEqual(
            EventType.test_events(),
            {
                EventType.TEST_START,
                EventType.TEST_END,
                EventType.TEST_LINE,
                EventType.TEST_DEF,
                EventType.TEST_USE,
                EventType.TEST_ASSERT,
            },
        )

    def test_list(self):
        self.assertEqual(
            list(EventType),
            [
                EventType.LINE,
                EventType.BRANCH,
                EventType.FUNCTION_ENTER,
                EventType.FUNCTION_EXIT,
                EventType.FUNCTION_ERROR,
                EventType.DEF,
                EventType.USE,
                EventType.CONDITION,
                EventType.LOOP_BEGIN,
                EventType.LOOP_HIT,
                EventType.LOOP_END,
                EventType.LEN,
            ],
        )

    def test_iter(self):
        self.assertEqual(
            [e for e in iter(EventType)],
            [
                EventType.LINE,
                EventType.BRANCH,
                EventType.FUNCTION_ENTER,
                EventType.FUNCTION_EXIT,
                EventType.FUNCTION_ERROR,
                EventType.DEF,
                EventType.USE,
                EventType.CONDITION,
                EventType.LOOP_BEGIN,
                EventType.LOOP_HIT,
                EventType.LOOP_END,
                EventType.LEN,
            ],
        )
