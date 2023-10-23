import io
import os
import unittest
from pathlib import Path

from sflkitlib.events import codec
from sflkitlib.events import event

FILE = "main.py"
LINE = 1
ID = 0


class CodecTest(unittest.TestCase):
    def _assert(self, e: event.Event, dump: bytes):
        self.assertEqual(e.dump(), dump)
        self.assertEqual(e, event.load_next_event(io.BytesIO(dump)))

    def test_line(self):
        e = event.LineEvent(FILE, LINE, ID)
        dump = codec.encode_line_event(FILE, LINE, ID)
        self._assert(e, dump)

    def test_branch(self):
        e = event.BranchEvent(FILE, LINE, ID, 0, -1)
        dump = codec.encode_branch_event(FILE, LINE, ID, 0, -1)
        self._assert(e, dump)

    def test_def(self):
        e = event.DefEvent(FILE, LINE, ID, "x", 1, 1, "int")
        dump = codec.encode_def_event(FILE, LINE, ID, "x", 1, 1, "int")
        self._assert(e, dump)

    def test_function_enter(self):
        e = event.FunctionEnterEvent(FILE, LINE, ID, "main", 1)
        dump = codec.encode_function_enter_event(FILE, LINE, ID, "main", 1)
        self._assert(e, dump)

    def test_function_exit(self):
        e = event.FunctionExitEvent(FILE, LINE, ID, "main", 1, 1, "int")
        dump = codec.encode_function_exit_event(FILE, LINE, ID, "main", 1, 1, "int")
        self._assert(e, dump)

    def test_function_error(self):
        e = event.FunctionErrorEvent(FILE, LINE, ID, "main", 1)
        dump = codec.encode_function_error_event(FILE, LINE, ID, "main", 1)
        self._assert(e, dump)

    def test_condition(self):
        e = event.ConditionEvent(FILE, LINE, ID, "x < y", False)
        dump = codec.encode_condition_event(FILE, LINE, ID, "x < y", False)
        self._assert(e, dump)

    def test_loop_begin(self):
        e = event.LoopBeginEvent(FILE, LINE, ID, 1)
        dump = codec.encode_loop_begin_event(FILE, LINE, ID, 1)
        self._assert(e, dump)

    def test_loop_hit(self):
        e = event.LoopHitEvent(FILE, LINE, ID, 1)
        dump = codec.encode_loop_hit_event(FILE, LINE, ID, 1)
        self._assert(e, dump)

    def test_loop_end(self):
        e = event.LoopEndEvent(FILE, LINE, ID, 1)
        dump = codec.encode_loop_end_event(FILE, LINE, ID, 1)
        self._assert(e, dump)

    def test_use(self):
        e = event.UseEvent(FILE, LINE, ID, "x", 1)
        dump = codec.encode_use_event(FILE, LINE, ID, "x", 1)
        self._assert(e, dump)

    def test_len(self):
        e = event.LenEvent(FILE, LINE, ID, "x", 1, 5)
        dump = codec.encode_len_event(FILE, LINE, ID, "x", 1, 5)
        self._assert(e, dump)

    def test_read_multiple(self):
        e_1 = event.LineEvent(FILE, 1, 0)
        e_2 = event.LineEvent(FILE, 2, 1)
        e_3 = event.LineEvent(FILE, 3, 2)
        path = Path("tmp")
        with path.open("wb") as fp:
            fp.write(e_1.dump())
            fp.write(e_2.dump())
            fp.write(e_3.dump())
        try:
            events = event.load(path)
            self.assertEqual(3, len(events))
            self.assertEqual(e_1, events[0])
            self.assertEqual(e_2, events[1])
            self.assertEqual(e_3, events[2])
        finally:
            os.remove(path)
