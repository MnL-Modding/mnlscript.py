import typing

from dynamicscope import DYNAMIC_SCOPE
import mnllib


class MnLScriptWarning(UserWarning):
    pass


def emit_debug_message(message: str, *, msgs: list[str] | None = None) -> int:
    if msgs is None:
        msgs = typing.cast(list[str], DYNAMIC_SCOPE.debug_messages)

    offset = sum(len(x.encode(mnllib.MNL_DEBUG_MESSAGE_ENCODING)) + 1 for x in msgs)
    msgs.append(message)
    return offset
