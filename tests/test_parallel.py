import os
import shutil
import subprocess
import threading
import unittest

from sflkitlib.events.event import LineEvent, load_next_event, DefEvent

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_PARALLEL_DIR = os.path.join(TEST_DIR, "example")
TESTS = "tests.test_example"


class ParallelTest(unittest.TestCase):

    @staticmethod
    def load_events(path, events_mapping):
        events = []
        with open(path, "rb") as f:
            while f.peek(1):
                event = load_next_event(f, events_mapping, with_thread_id=True)
                events.append(event)
        return events

    def remove_files(self, file):
        path = os.path.join(TEST_PARALLEL_DIR, file)
        if os.path.exists(path):
            os.remove(path)

    def tearDown(self):
        self.remove_files("events_21345")
        self.remove_files("events_32106")
        self.remove_files("events_67")
        self.remove_files("ids_21345.txt")
        self.remove_files("ids_32106.txt")
        self.remove_files("ids_67.txt")

    def test_example(self):
        environ = os.environ.copy()
        environ["EVENTS_THREADS"] = "1"
        environ_1 = environ.copy()
        environ_1["EVENTS_PATH"] = os.path.join(TEST_PARALLEL_DIR, "events_21345")
        subprocess.run(
            [
                "python",
                "-m",
                "unittest",
                TESTS + ".ExampleTests.test_21345",
            ],
            env=environ_1,
            cwd=TEST_PARALLEL_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        environ_2 = environ.copy()
        environ_2["EVENTS_PATH"] = os.path.join(TEST_PARALLEL_DIR, "events_32106")
        subprocess.run(
            [
                "python",
                "-m",
                "unittest",
                TESTS + ".ExampleTests.test_32106",
            ],
            env=environ_2,
            cwd=TEST_PARALLEL_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        environ_3 = environ.copy()
        environ_3["EVENTS_PATH"] = os.path.join(TEST_PARALLEL_DIR, "events_67")
        subprocess.run(
            [
                "python",
                "-m",
                "unittest",
                TESTS + ".ExampleTests.test_67",
            ],
            env=environ_3,
            cwd=TEST_PARALLEL_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # load events
        events_mapping = {
            1: LineEvent("example.py", 1, 1),
            2: LineEvent("example.py", 2, 2),
            3: LineEvent("example.py", 3, 3),
            4: LineEvent("example.py", 4, 4),
            5: DefEvent("example.py", 5, 5, var="n"),
        }

        all_events_21345 = self.load_events(
            os.path.join(TEST_PARALLEL_DIR, "events_21345"), events_mapping
        )
        all_events_32106 = self.load_events(
            os.path.join(TEST_PARALLEL_DIR, "events_32106"), events_mapping
        )
        all_events_67 = self.load_events(
            os.path.join(TEST_PARALLEL_DIR, "events_67"), events_mapping
        )

        self.assertTrue(len(all_events_21345) > 0)
        self.assertTrue(len(all_events_32106) > 0)
        self.assertTrue(len(all_events_67) > 0)

        # get all thread ids from the files
        thread_ids_21345 = set(event.thread_id for event in all_events_21345)
        thread_ids_32106 = set(event.thread_id for event in all_events_32106)
        thread_ids_67 = set(event.thread_id for event in all_events_67)

        # load thread_ids from ids files
        with open(os.path.join(TEST_PARALLEL_DIR, "ids_21345.txt"), "r") as f:
            ids_21345 = set(int(line.strip()) for line in f.readlines())
        with open(os.path.join(TEST_PARALLEL_DIR, "ids_32106.txt"), "r") as f:
            ids_32106 = set(int(line.strip()) for line in f.readlines())
        with open(os.path.join(TEST_PARALLEL_DIR, "ids_67.txt"), "r") as f:
            ids_67 = set(int(line.strip()) for line in f.readlines())

        print(ids_21345)
        print(ids_32106)
        print(ids_67)
        self.assertEqual(thread_ids_21345, ids_21345)
        self.assertEqual(thread_ids_32106, ids_32106)
        self.assertEqual(thread_ids_67, ids_67)

        # Sort events by thread id
        events_by_thread_21345 = {}
        for event in all_events_21345:
            events_by_thread_21345.setdefault(event.thread_id, []).append(event)
        events_by_thread_32106 = {}
        for event in all_events_32106:
            events_by_thread_32106.setdefault(event.thread_id, []).append(event)
        events_by_thread_67 = {}
        for event in all_events_67:
            events_by_thread_67.setdefault(event.thread_id, []).append(event)

        # check that events are correctly ordered within each thread
        main_thread_21345 = min(thread_ids_21345)
        main_thread_32106 = min(thread_ids_32106)
        main_thread_67 = min(thread_ids_67)
        # first line 2
        self.assertIsInstance(events_by_thread_21345[main_thread_21345][0], LineEvent)
        self.assertIsInstance(events_by_thread_32106[main_thread_32106][0], LineEvent)
        self.assertIsInstance(events_by_thread_67[main_thread_67][0], LineEvent)
        self.assertEqual(
            events_by_thread_21345[main_thread_21345][0].line,
            2,
        )
        self.assertEqual(
            events_by_thread_32106[main_thread_32106][0].line,
            2,
        )
        self.assertEqual(
            events_by_thread_67[main_thread_67][0].line,
            2,
        )
        # second def 5
        self.assertIsInstance(events_by_thread_21345[main_thread_21345][1], DefEvent)
        self.assertIsInstance(events_by_thread_32106[main_thread_32106][1], DefEvent)
        self.assertIsInstance(events_by_thread_67[main_thread_67][1], DefEvent)
        self.assertEqual(
            events_by_thread_21345[main_thread_21345][1].line,
            5,
        )
        self.assertEqual(
            events_by_thread_32106[main_thread_32106][1].line,
            5,
        )
        self.assertEqual(
            events_by_thread_67[main_thread_67][1].line,
            5,
        )
        # third line 4
        self.assertIsInstance(events_by_thread_21345[main_thread_21345][2], LineEvent)
        self.assertIsInstance(events_by_thread_32106[main_thread_32106][2], LineEvent)
        self.assertIsInstance(events_by_thread_67[main_thread_67][2], LineEvent)
        self.assertEqual(
            events_by_thread_21345[main_thread_21345][2].line,
            4,
        )
        self.assertEqual(
            events_by_thread_32106[main_thread_32106][2].line,
            4,
        )
        self.assertEqual(
            events_by_thread_67[main_thread_67][2].line,
            4,
        )

        # now the threads should be line 3 followed by multiple line 1s this could repeated, e.g., 3 1 1 3 1
        for thread_id in thread_ids_21345:
            if thread_id == main_thread_21345:
                continue
            events = events_by_thread_21345[thread_id]
            self.assertIsInstance(events[0], LineEvent)
            self.assertEqual(events[0].line, 3)
            last_3 = True
            for event in events[1:]:
                self.assertIsInstance(event, LineEvent)
                if last_3:
                    self.assertEqual(event.line, 1)
                    last_3 = False
                elif event.line == 3:
                    self.assertEqual(event.line, 3)
                    last_3 = True
                else:
                    self.assertEqual(event.line, 1)
                    last_3 = False
        for thread_id in thread_ids_32106:
            if thread_id == main_thread_32106:
                continue
            events = events_by_thread_32106[thread_id]
            self.assertIsInstance(events[0], LineEvent)
            self.assertEqual(events[0].line, 3)
            last_3 = True
            for event in events[1:]:
                self.assertIsInstance(event, LineEvent)
                if last_3:
                    self.assertEqual(event.line, 1)
                    last_3 = False
                elif event.line == 3:
                    self.assertEqual(event.line, 3)
                    last_3 = True
                else:
                    self.assertEqual(event.line, 1)
                    last_3 = False
        for thread_id in thread_ids_67:
            if thread_id == main_thread_67:
                continue
            events = events_by_thread_67[thread_id]
            self.assertIsInstance(events[0], LineEvent)
            self.assertEqual(events[0].line, 3)
            last_3 = True
            for event in events[1:]:
                self.assertIsInstance(event, LineEvent)
                if last_3:
                    self.assertEqual(event.line, 1)
                    last_3 = False
                elif event.line == 3:
                    self.assertEqual(event.line, 3)
                    last_3 = True
                else:
                    self.assertEqual(event.line, 1)
                    last_3 = False
