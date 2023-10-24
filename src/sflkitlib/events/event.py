import io
import sys
from abc import abstractmethod, ABC
from typing import Any, List, Union, Tuple, BinaryIO

from sflkitlib.events import EventType
from sflkitlib.events.codec import (
    encode_event,
    encode_def_event,
    encode_branch_event,
    encode_function_event,
    encode_function_exit_event,
    encode_condition_event,
    encode_loop_event,
    encode_use_event,
    encode_len_event,
    ENDIAN,
)

sys.path = sys.path[1:] + sys.path[:1]
import json
import pickle

sys.path = sys.path[-1:] + sys.path[:-1]


class Event(object):
    def __init__(self, file: str, line: int, id_: int, event_type: EventType):
        self.file = file
        self.line = line
        self.event_id = id_
        self.event_type = event_type

    def __hash__(self):
        return hash((self.file, self.line, self.event_id, self.event_type.value))

    def __eq__(self, other):
        if isinstance(other, Event):
            return (
                self.file == other.file
                and self.line == other.line
                and self.event_id == other.event_id
                and self.event_type == other.event_type
            )
        return False

    def __repr__(self):
        return f"{self.__class__.__name__}({self.file},{self.line},{self.event_id})"

    @abstractmethod
    def handle(self, model: Any):
        raise NotImplementedError()

    def serialize(self):
        return {
            "file": self.file,
            "line": self.line,
            "id": self.event_id,
            "event_type": self.event_type.value,
        }

    @staticmethod
    def get_byte_length(x: Union[int, float]):
        return (x.bit_length() + 7) // 8

    def dump(self) -> bytes:
        return encode_event(self.event_type, self.file, self.line, self.event_id)

    @staticmethod
    def deserialize(s: dict):
        return None


class EventEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Event):
            return o.serialize()
        else:
            super().default(o)


class LineEvent(Event):
    def __init__(self, file: str, line: int, id_: int):
        super().__init__(file, line, id_, EventType.LINE)

    def handle(self, model: Any):
        model.handle_line_event(self)

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id"])
        assert s["event_type"] == EventType.LINE.value
        return LineEvent(*[s[p] for p in ["file", "line", "id"]])


class BranchEvent(Event):
    def __init__(self, file: str, line: int, id_: int, then_id: int, else_id: int):
        super().__init__(file, line, id_, EventType.BRANCH)
        self.then_id = then_id
        self.else_id = else_id

    def handle(self, model: Any):
        model.handle_branch_event(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},{self.then_id},{self.else_id})"

    def serialize(self):
        default = super().serialize()
        default["then_id"] = self.then_id
        default["else_id"] = self.else_id
        return default

    def dump(self):
        return encode_branch_event(
            self.file,
            self.line,
            self.event_id,
            self.then_id,
            self.else_id,
        )

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "then_id", "else_id"])
        assert s["event_type"] == EventType.BRANCH.value
        return BranchEvent(
            *[s[p] for p in ["file", "line", "id", "then_id", "else_id"]]
        )


class DefEvent(Event):
    def __init__(
        self,
        file,
        line: int,
        id_: int,
        var: str,
        var_id: int = None,
        value: Any = None,
        type_: str = None,
    ):
        super().__init__(file, line, id_, EventType.DEF)
        self.var = var
        self.var_id = var_id
        self.value = value
        self.type_ = type_

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},"
            f"{self.var},{self.var_id},{self.value})"
        )

    def handle(self, model: Any):
        model.handle_def_event(self)

    def serialize(self):
        default = super().serialize()
        default["var"] = self.var
        return default

    def dump(self):
        return encode_def_event(
            self.file,
            self.line,
            self.event_id,
            self.var,
            self.var_id,
            self.value,
            self.type_,
        )

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "var"])
        assert s["event_type"] == EventType.DEF.value
        return DefEvent(*[s[p] for p in ["file", "line", "id", "var"]])


class FunctionEvent(Event, ABC):
    def __init__(
        self,
        file: str,
        line: int,
        id_: int,
        event_type: EventType,
        function: str,
        function_id: int,
    ):
        super().__init__(file, line, id_, event_type)
        self.function = function
        self.function_id = function_id

    def serialize(self):
        default = super().serialize()
        default["function_id"] = self.function_id
        default["function"] = self.function
        return default

    def dump(self):
        return encode_function_event(
            self.event_type,
            self.file,
            self.line,
            self.event_id,
            self.function,
            self.function_id,
        )


class FunctionEnterEvent(FunctionEvent):
    def __init__(self, file: str, line: int, id_: int, function: str, function_id: int):
        super().__init__(
            file, line, id_, EventType.FUNCTION_ENTER, function, function_id
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},{self.function})"

    def handle(self, model: Any):
        model.handle_function_enter_event(self)

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "function_id", "function"])
        assert s["event_type"] == EventType.FUNCTION_ENTER.value
        return FunctionEnterEvent(
            *[s[p] for p in ["file", "line", "id", "function_id", "function"]]
        )


class FunctionExitEvent(FunctionEvent):
    def __init__(
        self,
        file: str,
        line: int,
        id_: int,
        function: str,
        function_id: int,
        return_value: Any = None,
        type_: str = None,
        tmp_var: str = None,
    ):
        super().__init__(
            file, line, id_, EventType.FUNCTION_EXIT, function, function_id
        )
        self.return_value = return_value
        self.type_ = type_
        self.tmp_var = tmp_var

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},"
            f"{self.function},{self.return_value},{self.type_})"
        )

    def handle(self, model: Any):
        model.handle_function_exit_event(self)

    def dump(self):
        return encode_function_exit_event(
            self.file,
            self.line,
            self.event_id,
            self.function,
            self.function_id,
            self.return_value,
            self.type_,
        )

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "function_id", "function"])
        assert s["event_type"] == EventType.FUNCTION_EXIT.value
        return FunctionExitEvent(
            *[s[p] for p in ["file", "line", "id", "function_id", "function"]]
        )


class FunctionErrorEvent(FunctionEvent):
    def __init__(self, file: str, line: int, id_: int, function: str, function_id: int):
        super().__init__(
            file, line, id_, EventType.FUNCTION_ERROR, function, function_id
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},"
            f"{self.function_id},{self.function})"
        )

    def handle(self, model: Any):
        model.handle_function_error_event(self)

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "function_id", "function"])
        assert s["event_type"] == EventType.FUNCTION_ERROR.value
        return FunctionErrorEvent(
            *[s[p] for p in ["file", "line", "id", "function_id", "function"]]
        )


class ConditionEvent(Event):
    def __init__(
        self,
        file: str,
        line: int,
        id_: int,
        condition: str,
        value: bool = None,
        tmp_var: str = None,
    ):
        super().__init__(file, line, id_, EventType.CONDITION)
        self.value = value
        self.condition = condition
        self.tmp_var = tmp_var

    def __repr__(self):
        return f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},{self.value},{self.condition})"

    def handle(self, model: Any):
        model.handle_condition_event(self)

    def serialize(self):
        default = super().serialize()
        default["condition"] = self.condition
        return default

    def dump(self):
        return encode_condition_event(
            self.file,
            self.line,
            self.event_id,
            self.condition,
            self.value,
        )

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "condition"])
        assert s["event_type"] == EventType.CONDITION.value
        return ConditionEvent(*[s[p] for p in ["file", "line", "id", "condition"]])


class LoopEvent(Event, ABC):
    def __init__(
        self, file: str, line: int, id_: int, event_type: EventType, loop_id: int
    ):
        super().__init__(file, line, id_, event_type)
        self.loop_id = loop_id

    def serialize(self):
        default = super().serialize()
        default["loop_id"] = self.loop_id
        return default

    def dump(self):
        return encode_loop_event(
            self.event_type,
            self.file,
            self.line,
            self.event_id,
            self.loop_id,
        )


class LoopBeginEvent(LoopEvent):
    def __init__(self, file: str, line: int, id_: int, loop_id: int):
        super().__init__(file, line, id_, EventType.LOOP_BEGIN, loop_id)

    def handle(self, model: Any):
        model.handle_loop_begin_event(self)

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "loop_id"])
        assert s["event_type"] == EventType.LOOP_BEGIN.value
        return LoopBeginEvent(*[s[p] for p in ["file", "line", "id", "loop_id"]])


class LoopHitEvent(LoopEvent):
    def __init__(self, file: str, line: int, id_: int, loop_id: int):
        super().__init__(file, line, id_, EventType.LOOP_HIT, loop_id)

    def handle(self, model: Any):
        model.handle_loop_hit_event(self)

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "loop_id"])
        assert s["event_type"] == EventType.LOOP_HIT.value
        return LoopHitEvent(*[s[p] for p in ["file", "line", "id", "loop_id"]])


class LoopEndEvent(LoopEvent):
    def __init__(self, file: str, line: int, id_: int, loop_id: int):
        super().__init__(file, line, id_, EventType.LOOP_END, loop_id)

    def handle(self, model: Any):
        model.handle_loop_end_event(self)

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "loop_id"])
        assert s["event_type"] == EventType.LOOP_END.value
        return LoopEndEvent(*[s[p] for p in ["file", "line", "id", "loop_id"]])


class UseEvent(Event):
    def __init__(self, file: str, line: int, id_: int, var: str, var_id: int = None):
        super().__init__(file, line, id_, EventType.USE)
        self.var = var
        self.var_id = var_id

    def __repr__(self):
        return f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},{self.var},{self.var_id})"

    def handle(self, model: Any):
        model.handle_use_event(self)

    def serialize(self):
        default = super().serialize()
        default["var"] = self.var
        return default

    def dump(self):
        return encode_use_event(
            self.file, self.line, self.event_id, self.var, self.var_id
        )

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "var"])
        assert s["event_type"] == EventType.USE.value
        return UseEvent(*[s[p] for p in ["file", "line", "id", "var"]])


class LenEvent(Event):
    def __init__(
        self,
        file: str,
        line: int,
        id_: int,
        var: str,
        var_id: int = None,
        length: int = None,
    ):
        super().__init__(file, line, id_, EventType.LEN)
        self.var = var
        self.var_id = var_id
        self.length = length

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.file},{self.line},{self.event_id},"
            f"{self.var},{self.var_id},{self.length})"
        )

    def handle(self, model: Any):
        model.handle_len_event(self)

    def serialize(self):
        default = super().serialize()
        default["var"] = self.var
        return default

    def dump(self):
        return encode_len_event(
            self.file,
            self.line,
            self.event_id,
            self.var,
            self.var_id,
            self.length,
        )

    @staticmethod
    def deserialize(s: dict):
        assert all(p in s for p in ["file", "line", "id", "var"])
        assert s["event_type"] == EventType.LEN.value
        return LenEvent(*[s[p] for p in ["file", "line", "id", "var"]])


def serialize(event: Event):
    return event.serialize()


event_mapping = {
    EventType.LINE: LineEvent,
    EventType.BRANCH: BranchEvent,
    EventType.DEF: DefEvent,
    EventType.USE: UseEvent,
    EventType.FUNCTION_ENTER: FunctionEnterEvent,
    EventType.FUNCTION_EXIT: FunctionExitEvent,
    EventType.FUNCTION_ERROR: FunctionErrorEvent,
    EventType.LOOP_BEGIN: LoopBeginEvent,
    EventType.LOOP_HIT: LoopHitEvent,
    EventType.LOOP_END: LoopEndEvent,
    EventType.CONDITION: ConditionEvent,
    EventType.LEN: LenEvent,
}


def deserialize(s: dict):
    assert "event_type" in s
    type_ = EventType(s["event_type"])
    return event_mapping[type_].deserialize(s)


def dump(path: str, events: List[Event]):
    with open(path, "wb") as fp:
        for e in events:
            fp.write(e.dump())


def read_int(stream: BinaryIO, n: int, signed: bool = False) -> int:
    return int.from_bytes(stream.read(n), ENDIAN, signed=signed)


def read_len_str(stream: BinaryIO, n: int) -> str:
    length = read_int(stream, n)
    return stream.read(length).decode("utf8")


def read_len_bytes(stream: BinaryIO, n: int) -> bytes:
    length = read_int(stream, n)
    return stream.read(length)


def read_len_int(stream: BinaryIO, n: int, signed: bool = False) -> int:
    length = read_int(stream, n)
    return read_int(stream, length, signed=signed)


def load_event(e: bytes) -> Event:
    return load_next_event(io.BytesIO(e))


def load_next_event(stream: BinaryIO) -> Event:
    test = stream.read(1)
    if not test:
        raise ValueError("empty stream")
    event_type = EventType(int.from_bytes(test, ENDIAN))
    file = read_len_str(stream, 2)
    line = read_len_int(stream, 1)
    event_id = read_len_int(stream, 1)
    if event_type == EventType.BRANCH:
        then_id = read_len_int(stream, 1, signed=True)
        else_id = read_len_int(stream, 1, signed=True)
        return BranchEvent(file, line, event_id, then_id, else_id)
    elif event_type == EventType.DEF:
        # noinspection PyBroadException
        var = read_len_str(stream, 2)
        var_id = read_len_int(stream, 1)
        value = read_len_bytes(stream, 4)
        type_ = read_len_str(stream, 2)
        try:
            return DefEvent(
                file,
                line,
                event_id,
                var,
                var_id,
                pickle.loads(value),
                type_,
            )
        except:
            value = value.decode("utf8")
            if value == "True":
                return DefEvent(
                    file,
                    line,
                    event_id,
                    var,
                    var_id,
                    True,
                    type_,
                )
            elif value == "False":
                return DefEvent(
                    file,
                    line,
                    event_id,
                    var,
                    var_id,
                    False,
                    type_,
                )
            else:
                return DefEvent(
                    file,
                    line,
                    event_id,
                    var,
                    var_id,
                    None,
                    type_,
                )
    elif event_type == EventType.USE:
        var = read_len_str(stream, 2)
        var_id = read_len_int(stream, 1)
        return UseEvent(file, line, event_id, var, var_id)
    elif event_type in [
        EventType.FUNCTION_ENTER,
        EventType.FUNCTION_EXIT,
        EventType.FUNCTION_ERROR,
    ]:
        function = read_len_str(stream, 2)
        function_id = read_len_int(stream, 1)
        if event_type == EventType.FUNCTION_ENTER:
            return FunctionEnterEvent(file, line, event_id, function, function_id)
        elif event_type == EventType.FUNCTION_ERROR:
            return FunctionErrorEvent(file, line, event_id, function, function_id)
        else:
            # noinspection PyBroadException
            value = read_len_bytes(stream, 4)
            type_ = read_len_str(stream, 2)
            try:
                return FunctionExitEvent(
                    file,
                    line,
                    event_id,
                    function,
                    function_id,
                    pickle.loads(value),
                    type_,
                )
            except:
                value = value.decode("utf8")
                if value == "True":
                    return FunctionExitEvent(
                        file,
                        line,
                        event_id,
                        function,
                        function_id,
                        True,
                        type_,
                    )
                elif value == "False":
                    return FunctionExitEvent(
                        file,
                        line,
                        event_id,
                        function,
                        function_id,
                        False,
                        type_,
                    )
                else:
                    return FunctionExitEvent(
                        file,
                        line,
                        event_id,
                        function,
                        function_id,
                        None,
                        type_,
                    )
    elif event_type == EventType.CONDITION:
        condition = read_len_str(stream, 4)
        value = bool(read_int(stream, 1))
        return ConditionEvent(file, line, event_id, condition, value)
    elif event_type in [EventType.LOOP_BEGIN, EventType.LOOP_HIT, event_type.LOOP_END]:
        loop_id = read_len_int(stream, 1)
        return event_mapping[event_type](file, line, event_id, loop_id)
    elif event_type == EventType.LEN:
        var = read_len_str(stream, 2)
        var_id = read_len_int(stream, 1)
        length = read_len_int(stream, 1)
        return LenEvent(file, line, event_id, var, var_id, length)
    else:
        return event_mapping[event_type](file, line, event_id)


def load(path) -> List[Event]:
    events = list()
    with open(path, "rb") as fp:
        while True:
            try:
                events.append(load_next_event(fp))
            except:
                break
    return events


def load_json(path) -> List[Event]:
    with open(path, "r") as fp:
        events = json.load(fp)
    return list(map(deserialize, events))
