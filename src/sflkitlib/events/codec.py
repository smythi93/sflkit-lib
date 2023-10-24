from typing import Union, Any

from sflkitlib.events import EventType

ENDIAN = "big"


def get_byte_length(x: Union[int, float]):
    return max((x.bit_length() + 7) // 8, 1)


def encode_event(event_type: EventType, file: str, line: int, event_id: int):
    len_file = len(file)
    len_line = get_byte_length(line)
    len_id = get_byte_length(event_id)
    return b"".join(
        [
            event_type.value.to_bytes(1, ENDIAN),
            len_file.to_bytes(2, ENDIAN),
            file.encode("utf8"),
            len_line.to_bytes(1, ENDIAN),
            line.to_bytes(len_line, ENDIAN),
            len_id.to_bytes(1, ENDIAN),
            event_id.to_bytes(len_id, ENDIAN),
        ]
    )


def encode_line_event(file: str, line: int, event_id: int):
    return encode_event(EventType.LINE, file, line, event_id)


def encode_branch_event(
    file: str,
    line: int,
    event_id: int,
    then_id: int,
    else_id: int,
):
    len_then_id = get_byte_length(then_id)
    len_else_id = get_byte_length(else_id)
    return encode_event(EventType.BRANCH, file, line, event_id) + b"".join(
        [
            len_then_id.to_bytes(1, ENDIAN),
            then_id.to_bytes(len_then_id, ENDIAN, signed=True),
            len_else_id.to_bytes(1, ENDIAN),
            else_id.to_bytes(len_else_id, ENDIAN, signed=True),
        ]
    )


def encode_def_event(
    file: str,
    line: int,
    event_id: int,
    var: str,
    var_id: int,
    value: Any,
    type_: str,
):
    len_var = len(var)
    len_var_id = get_byte_length(var_id)
    if isinstance(value, bytes):
        value = value
    else:
        value = str(value).encode("utf8")
    len_value = len(value)
    len_type = len(type_)
    return encode_event(EventType.DEF, file, line, event_id) + b"".join(
        [
            len_var.to_bytes(2, ENDIAN),
            var.encode("utf8"),
            len_var_id.to_bytes(1, ENDIAN),
            var_id.to_bytes(len_var_id, ENDIAN),
            len_value.to_bytes(4, ENDIAN),
            value,
            len_type.to_bytes(2, ENDIAN),
            type_.encode("utf8"),
        ]
    )


def encode_function_event(
    event_type: EventType,
    file: str,
    line: int,
    event_id: int,
    function: str,
    function_id: int,
):
    len_function_id = get_byte_length(function_id)
    len_function = len(function)
    return encode_event(event_type, file, line, event_id) + b"".join(
        [
            len_function.to_bytes(2, ENDIAN),
            function.encode("utf8"),
            len_function_id.to_bytes(1, ENDIAN),
            function_id.to_bytes(len_function_id, ENDIAN),
        ]
    )


def encode_function_enter_event(
    file: str,
    line: int,
    event_id: int,
    function: str,
    function_id: int,
):
    return encode_function_event(
        EventType.FUNCTION_ENTER, file, line, event_id, function, function_id
    )


def encode_function_exit_event(
    file: str,
    line: int,
    event_id: int,
    function: str,
    function_id: int,
    return_value: Any,
    type_: str,
):
    if isinstance(return_value, bytes):
        value = return_value
    else:
        value = str(return_value).encode("utf8")
    len_value = len(value)
    len_type = len(type_)
    return encode_function_event(
        EventType.FUNCTION_EXIT, file, line, event_id, function, function_id
    ) + b"".join(
        [
            len_value.to_bytes(4, ENDIAN),
            value,
            len_type.to_bytes(2, ENDIAN),
            type_.encode("utf8"),
        ]
    )


def encode_function_error_event(
    file: str,
    line: int,
    event_id: int,
    function: str,
    function_id: int,
):
    return encode_function_event(
        EventType.FUNCTION_ERROR, file, line, event_id, function, function_id
    )


def encode_condition_event(
    file: str,
    line: int,
    event_id: int,
    condition: str,
    value: any,
):
    len_condition = len(condition)
    return encode_event(EventType.CONDITION, file, line, event_id) + b"".join(
        [
            len_condition.to_bytes(4, ENDIAN),
            condition.encode("utf8"),
            (1 if value else 0).to_bytes(1, ENDIAN),
        ]
    )


def encode_loop_event(
    event_type: EventType,
    file: str,
    line: int,
    event_id: int,
    loop_id: int,
):
    len_loop_id = get_byte_length(loop_id)
    return encode_event(event_type, file, line, event_id) + b"".join(
        [
            len_loop_id.to_bytes(1, ENDIAN),
            loop_id.to_bytes(len_loop_id, ENDIAN),
        ]
    )


def encode_loop_begin_event(
    file: str,
    line: int,
    event_id: int,
    loop_id: int,
):
    return encode_loop_event(EventType.LOOP_BEGIN, file, line, event_id, loop_id)


def encode_loop_hit_event(
    file: str,
    line: int,
    event_id: int,
    loop_id: int,
):
    return encode_loop_event(EventType.LOOP_HIT, file, line, event_id, loop_id)


def encode_loop_end_event(
    file: str,
    line: int,
    event_id: int,
    loop_id: int,
):
    return encode_loop_event(EventType.LOOP_END, file, line, event_id, loop_id)


def encode_use_event(
    file: str,
    line: int,
    event_id: int,
    var: str,
    var_id: int,
):
    len_var = len(var)
    len_var_id = get_byte_length(var_id)
    return encode_event(EventType.USE, file, line, event_id) + b"".join(
        [
            len_var.to_bytes(2, ENDIAN),
            var.encode("utf8"),
            len_var_id.to_bytes(1, ENDIAN),
            var_id.to_bytes(len_var_id, ENDIAN),
        ]
    )


def encode_len_event(
    file: str,
    line: int,
    event_id: int,
    var: str,
    var_id: int,
    length: int,
):
    len_var = len(var)
    len_var_id = get_byte_length(var_id)
    len_length = get_byte_length(length)
    return encode_event(EventType.LEN, file, line, event_id) + b"".join(
        [
            len_var.to_bytes(2, ENDIAN),
            var.encode("utf8"),
            len_var_id.to_bytes(1, ENDIAN),
            var_id.to_bytes(len_var_id, ENDIAN),
            len_length.to_bytes(1, ENDIAN),
            length.to_bytes(len_length, ENDIAN),
        ]
    )
