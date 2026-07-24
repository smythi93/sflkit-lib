import sys


sys.path = sys.path[1:] + sys.path[:1]
import atexit
import os
import pickle
import signal
import threading
from typing import Any

sys.path = sys.path[-1:] + sys.path[:-1]

from sflkitlib.events import codec


def _env_int(name: str, default: int) -> int:
    """Read a non-negative integer setting from the environment.

    Malformed values fall back to *default* rather than crashing the program
    under test.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean setting from the environment."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


_EVENTS_PATH = os.getenv("EVENTS_PATH", default="EVENTS_PATH")
_threading = int(os.getenv("EVENTS_THREADS", default="0"))

# ── Trace budgets ────────────────────────────────────────────────────────────
# Tracing a program that manipulates large values or runs hot loops can produce
# arbitrarily large event streams: every ``def`` event serialises its value in
# full, so a single assignment of a multi-megabyte ``bytes`` buffer writes
# megabytes into the trace.  The settings below bound what a single run may
# emit.  All of them are configurable through the environment; ``0`` disables
# the corresponding limit.
#
# EVENTS_MAX_VALUE_BYTES  Longest str/bytes value serialised into a def or
#                         function-exit event.  Longer values are truncated to
#                         this prefix.  Length events carry the true length, so
#                         length analyses stay exact.
# EVENTS_MAX_LOOP_HITS    Loop-hit events emitted per loop iteration frame.
#                         SFLKit only distinguishes "never", "once" and "more
#                         than once", so the default of 2 is lossless while
#                         removing what is usually the dominant event class.
# EVENTS_MAX_BYTES        Total size of the event stream.  Writing stops once
#                         the budget is exhausted; the truncated stream is
#                         still readable because events are written whole.
# EVENTS_MAX_EVENTS       Total number of events, as an alternative budget.
_max_value_bytes = _env_int("EVENTS_MAX_VALUE_BYTES", 1024)
_max_loop_hits = _env_int("EVENTS_MAX_LOOP_HITS", 2)
_max_bytes = _env_int("EVENTS_MAX_BYTES", 0)
_max_events = _env_int("EVENTS_MAX_EVENTS", 0)

_written_bytes = 0
_written_events = 0
_budget_exhausted = False

_thread_counter = 0
_thread_counter_lock = threading.Lock()
_thread_ids = {}

# Per (thread, loop event) stack of iteration counters, mirroring the loop
# nesting so that recursive entries into the same loop are counted separately.
_loop_hits = {}


def _open_event_file(path: str):
    """Open the event stream at *path*, compressing it when requested.

    Compression is selected by ``EVENTS_COMPRESS`` (``gzip``/``zstd``) or
    implied by a ``.gz``/``.zst`` suffix on the path.  Event traces are highly
    repetitive, so compression typically shrinks them by an order of magnitude.
    When the requested codec is unavailable we silently fall back to an
    uncompressed stream: a missing optional dependency must never break the
    program under test.
    """
    codec_name = os.getenv("EVENTS_COMPRESS", default="").strip().lower()
    if not codec_name:
        lowered = path.lower()
        if lowered.endswith(".gz"):
            codec_name = "gzip"
        elif lowered.endswith(".zst"):
            codec_name = "zstd"
    if codec_name in ("gzip", "gz"):
        try:
            import gzip

            return gzip.open(path, "wb", compresslevel=1)
        except Exception:
            pass
    elif codec_name in ("zstd", "zstandard"):
        try:
            import zstandard

            raw = open(path, "wb")
            return zstandard.ZstdCompressor(level=3).stream_writer(raw)
        except Exception:
            pass
    return open(path, "wb")


_event_path_file = _open_event_file(_EVENTS_PATH)


def _get_thread_id():
    """Get the current thread ID if threading is enabled, otherwise None.

    Uses threading.get_ident() instead of os.getpid() because:
    - threading.get_ident() distinguishes between different threads in the same process
    - os.getpid() returns the same value for all threads in a process
    - This is needed to track events from concurrent threads properly

    Returns:
        int or None: Thread identifier if threading is enabled, None otherwise
    """
    if _threading:
        thread = threading.current_thread()
        if thread not in _thread_ids:
            with _thread_counter_lock:
                global _thread_counter
                _thread_ids[thread] = _thread_counter
                _thread_counter += 1
        return _thread_ids[thread]
    return None


def reset():
    # noinspection PyBroadException
    try:
        dump_events()
    except:
        pass
    global _event_path_file, _written_bytes, _written_events, _budget_exhausted
    _written_bytes = 0
    _written_events = 0
    _budget_exhausted = False
    _loop_hits.clear()
    _event_path_file = _open_event_file(
        os.getenv("EVENTS_PATH", default=_EVENTS_PATH)
    )


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
    try:
        _event_path_file.flush()
        _event_path_file.close()
    except:
        pass


def write(encoded_event: bytes):
    global _event_path_file, _written_bytes, _written_events, _budget_exhausted
    if _budget_exhausted:
        return
    try:
        _event_path_file.write(encoded_event)
    except ValueError:
        return
    except OSError:
        # Out of disk space or a broken pipe: stop tracing rather than let the
        # program under test die inside an instrumentation probe.
        _budget_exhausted = True
        dump_events()
        return
    _written_bytes += len(encoded_event)
    _written_events += 1
    if (_max_bytes and _written_bytes >= _max_bytes) or (
        _max_events and _written_events >= _max_events
    ):
        # Events are written whole, so cutting off here leaves the stream at an
        # event boundary and readable up to this point.
        _budget_exhausted = True
        dump_events()


def _cap_value(value: Any):
    """Shorten oversized str/bytes values before they are serialised.

    A single ``def`` event on a multi-megabyte buffer would otherwise write
    that whole buffer into the trace.  Predicates over such values (empty,
    ASCII-only, contains-digit, ...) are evaluated on the retained prefix.
    """
    if _max_value_bytes <= 0:
        return value
    if isinstance(value, (bytes, bytearray)):
        if len(value) > _max_value_bytes:
            return bytes(value[:_max_value_bytes])
    elif isinstance(value, str):
        if len(value) > _max_value_bytes:
            return value[:_max_value_bytes]
    return value


atexit.register(dump_events)


def _flush_on_signal(signum, frame):
    """Flush the trace when the runner kills a run that overran its timeout.

    ``atexit`` handlers do not run on SIGTERM, so without this a timed-out run
    would lose everything still buffered — which matters most for compressed
    streams, where the buffer is large.  Any previously installed handler is
    chained so we stay invisible to the program under test.
    """
    dump_events()
    previous = _previous_handlers.get(signum)
    if callable(previous):
        previous(signum, frame)
    elif previous == signal.SIG_IGN:
        return
    else:
        os._exit(128 + signum)


_previous_handlers = {}
if _env_flag("EVENTS_FLUSH_ON_SIGNAL", default=True):
    # SIGTERM only: it is how a runner stops a run that overran its timeout,
    # and the process is going away regardless. SIGINT is left alone because a
    # program may catch KeyboardInterrupt and keep running, and it would then
    # continue with a closed trace.
    # noinspection PyBroadException
    try:
        _previous_handlers[signal.SIGTERM] = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, _flush_on_signal)
    except Exception:
        # Not the main thread, or a platform without this signal.
        pass


def add_line_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))


def add_branch_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))


def add_def_event(event_id: int, var_id: int, value: Any, type_: type):
    if var_id is not None:
        if type_ in [int, float, complex, str, bytes, bytearray, bool] or value is None:
            write(
                codec.encode_def_event(
                    event_id,
                    var_id,
                    pickle.dumps(_cap_value(value)),
                    type_.__name__,
                    _get_thread_id(),
                )
            )
        else:
            write(
                codec.encode_def_event(
                    event_id,
                    var_id,
                    pickle.dumps(None),
                    f"{type_.__module__}.{type_.__name__}",
                    _get_thread_id(),
                )
            )


def add_function_enter_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))


def add_function_exit_event(
    event_id: int,
    return_value: Any,
    type_: type,
):
    if (
        type_ in [int, float, complex, str, bytes, bytearray, bool]
        or return_value is None
    ):
        write(
            codec.encode_function_exit_event(
                event_id,
                pickle.dumps(_cap_value(return_value)),
                type_.__name__,
                _get_thread_id(),
            )
        )
    else:
        # noinspection PyBroadException
        try:
            write(
                codec.encode_function_exit_event(
                    event_id,
                    pickle.dumps(bool(return_value)),
                    f"{type_.__module__}.{type_.__name__}",
                    _get_thread_id(),
                )
            )
        except:
            write(
                codec.encode_function_exit_event(
                    event_id,
                    pickle.dumps(None),
                    f"{type_.__module__}.{type_.__name__}",
                    _get_thread_id(),
                )
            )


def add_function_error_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))


def add_condition_event(event_id: int, value: Any):
    if value:
        write(codec.encode_condition_event(event_id, True, _get_thread_id()))
    else:
        write(codec.encode_condition_event(event_id, False, _get_thread_id()))


def _branch_distance(lhs: Any, rhs: Any, op: str):
    """
    How far *lhs* and *rhs* are from satisfying ``lhs <op> rhs``.

    Zero or negative when the comparison already holds, positive by the amount
    still needed otherwise.  Returns ``None`` for operands that do not support
    arithmetic, where no distance is defined.
    """
    try:
        if op == "<":
            return lhs - rhs
        if op == "<=":
            return lhs - rhs
        if op == ">":
            return rhs - lhs
        if op == ">=":
            return rhs - lhs
        if op == "==":
            return abs(lhs - rhs)
        if op == "!=":
            return -abs(lhs - rhs)
    except Exception:
        # Non-numeric operands, or an overloaded operator that raised: the
        # program under test must not fail inside an instrumentation probe.
        return None
    return None


def add_condition_value_event(event_id: int, lhs: Any, rhs: Any, op: str):
    distance = _branch_distance(lhs, rhs, op)
    if distance is not None:
        try:
            distance = float(distance)
        except (TypeError, ValueError):
            distance = None
    write(codec.encode_condition_value_event(event_id, distance, _get_thread_id()))


def add_loop_begin_event(event_id: int):
    thread_id = _get_thread_id()
    if _max_loop_hits > 0:
        _loop_hits.setdefault((thread_id, event_id), []).append(0)
    write(codec.encode_event(event_id, thread_id))


def add_loop_hit_event(event_id: int):
    thread_id = _get_thread_id()
    if _max_loop_hits > 0:
        key = (thread_id, event_id)
        frames = _loop_hits.get(key)
        if frames:
            frames[-1] += 1
            if frames[-1] > _max_loop_hits:
                # SFLKit distinguishes only never/once/more-than-once, so every
                # further hit of this loop frame is redundant.
                return
        else:
            _loop_hits[key] = [1]
    write(codec.encode_event(event_id, thread_id))


def add_loop_end_event(event_id: int):
    thread_id = _get_thread_id()
    if _max_loop_hits > 0:
        key = (thread_id, event_id)
        frames = _loop_hits.get(key)
        if frames:
            frames.pop()
            if not frames:
                del _loop_hits[key]
    write(codec.encode_event(event_id, thread_id))


def add_use_event(event_id: int, var_id: int):
    if var_id is not None:
        write(codec.encode_use_event(event_id, var_id, _get_thread_id()))


def add_len_event(event_id: int, var_id: int, length: int):
    if var_id is not None:
        write(codec.encode_len_event(event_id, var_id, length, _get_thread_id()))


def add_test_start_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))


def add_test_end_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))


def add_test_line_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))


def add_test_def_event(event_id: int, var_id: int):
    if var_id is not None:
        write(codec.encode_base_def_event(event_id, var_id, _get_thread_id()))


def add_test_use_event(event_id: int, var_id: int):
    if var_id is not None:
        write(codec.encode_use_event(event_id, var_id, _get_thread_id()))


def add_test_assert_event(event_id: int):
    write(codec.encode_event(event_id, _get_thread_id()))
