import dataclasses
import re
import types
import typing
from typing import override

import mnllib
import mnllib.dt

from ..utils import fhex
from .sound import Sound


@dataclasses.dataclass
class TextboxSounds:
    @override
    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return (self.normal, self.fast_forwarded) == (
                other.normal,
                other.fast_forwarded,
            )
        return NotImplemented

    normal: Sound | str | int
    fast_forwarded: Sound | str | int


def parse_rgba_or_neg1(value: str) -> tuple[int, int, int, int]:
    value = re.sub(r"\s+", "", value)

    if len(value) != 8:
        raise ValueError(
            f"RGBA string must be exactly 8 characters long, got {len(value)}: {value}"
        )

    color: list[int] = []
    for i in range(4):
        channel_string = value[i * 2 : (i + 1) * 2]
        if channel_string == "--":
            color.append(-1)
        else:
            color.append(int(channel_string, base=16))

    return typing.cast(tuple[int, int, int, int], tuple(color))


def encode_rgba_or_neg1(value: tuple[int, int, int, int]) -> str:
    result = ""
    for channel in value:
        if 0x00 <= channel <= 0xFF:
            result += f"{channel:02X}"
        elif channel == -1:
            result += "--"
        else:
            raise ValueError(
                "RGBA channel must be between 0x00 and 0xFF, "
                f"or -1, got {fhex(channel)}"
            )
    return result


class FEventInitModule(types.ModuleType):
    pass


class FEventScriptModule(types.ModuleType):
    script_index: int
    subroutines: list[mnllib.Subroutine]
    debug_messages: list[str]

    header: mnllib.dt.FEventScriptHeader
