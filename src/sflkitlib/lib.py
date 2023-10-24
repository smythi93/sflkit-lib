import sys


sys.path = sys.path[1:] + sys.path[:1]
import atexit
import os
import pickle
from typing import Any

sys.path = sys.path[-1:] + sys.path[:-1]

from sflkitlib.events import codec

_event_path_file = open(os.getenv("EVENTS_PATH", default="EVENTS_PATH"), "wb")


def reset():
    # noinspection PyBroadException
    try:
        dump_events()
    except:
        pass
    global _event_path_file
    _event_path_file = open(os.getenv("EVENTS_PATH", default="EVENTS_PATH"), "wb")


def get_id(x: Any):
    try:
        return id(x)
    except (AttributeError, TypeError):
        return None


def get_type(x: Any):
    try:
        return type(x)
    except (AttributeError, TypeError):
        return None


def dump_events():
    _event_path_file.flush()
    _event_path_file.close()


atexit.register(dump_events)


def add_line_event(file: str, line: int, id_: int):
    _event_path_file.write(codec.encode_line_event(file, line, id_))


def add_branch_event(file: str, line: int, id_: int, then_id: int, else_id: int):
    _event_path_file.write(codec.encode_branch_event(file, line, id_, then_id, else_id))


def add_def_event(
    file: str, line: int, id_: int, var: str, var_id: int, value: Any, type_: type
):
    if var_id is not None:
        if (
            type_ in [int, float, complex, str, bytes, bytearray, memoryview, bool]
            or value is None
        ):
            _event_path_file.write(
                codec.encode_def_event(
                    file,
                    line,
                    id_,
                    var,
                    var_id,
                    pickle.dumps(value),
                    type_.__name__,
                )
            )
        else:
            _event_path_file.write(
                codec.encode_def_event(
                    file,
                    line,
                    id_,
                    var,
                    var_id,
                    pickle.dumps(None),
                    f"{type_.__module__}.{type_.__name__}",
                )
            )


def add_function_enter_event(
    file: str, line: int, id_: int, function: str, function_id: int
):
    _event_path_file.write(
        codec.encode_function_enter_event(file, line, id_, function, function_id)
    )


def add_function_exit_event(
    file: str,
    line: int,
    id_: int,
    function: str,
    function_id: int,
    return_value: Any,
    type_: type,
):
    if (
        type_ in [int, float, complex, str, bytes, bytearray, memoryview, bool]
        or return_value is None
    ):
        _event_path_file.write(
            codec.encode_function_exit_event(
                file,
                line,
                id_,
                function,
                function_id,
                pickle.dumps(return_value),
                type_.__name__,
            )
        )
    else:
        # noinspection PyBroadException
        try:
            _event_path_file.write(
                codec.encode_function_exit_event(
                    file,
                    line,
                    id_,
                    function,
                    function_id,
                    pickle.dumps(bool(return_value)),
                    f"{type_.__module__}.{type_.__name__}",
                )
            )
        except:
            _event_path_file.write(
                codec.encode_function_exit_event(
                    file,
                    line,
                    id_,
                    function,
                    function_id,
                    pickle.dumps(None),
                    f"{type_.__module__}.{type_.__name__}",
                )
            )


def add_function_error_event(
    file: str, line: int, id_: int, function: str, function_id: int
):
    _event_path_file.write(
        codec.encode_function_error_event(file, line, id_, function, function_id)
    )


def add_condition_event(file: str, line: int, id_: int, condition: str, value: Any):
    if value:
        _event_path_file.write(
            codec.encode_condition_event(file, line, id_, condition, True)
        )
    else:
        _event_path_file.write(
            codec.encode_condition_event(file, line, id_, condition, False)
        )


def add_loop_begin_event(file: str, line: int, id_: int, loop_id: int):
    _event_path_file.write(codec.encode_loop_begin_event(file, line, id_, loop_id))


def add_loop_hit_event(file: str, line: int, id_: int, loop_id: int):
    _event_path_file.write(codec.encode_loop_hit_event(file, line, id_, loop_id))


def add_loop_end_event(file: str, line: int, id_: int, loop_id: int):
    _event_path_file.write(codec.encode_loop_end_event(file, line, id_, loop_id))


def add_use_event(file: str, line: int, id_: int, var: str, var_id: int):
    if var_id is not None:
        _event_path_file.write(codec.encode_use_event(file, line, id_, var, var_id))


def add_len_event(file: str, line: int, id_: int, var: str, var_id: int, length: int):
    if var_id is not None:
        _event_path_file.write(
            codec.encode_len_event(file, line, id_, var, var_id, length)
        )
