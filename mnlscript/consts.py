import re
import enum
import typing

import bidict


class SelfType(enum.Enum):
    Self = object()


Self = SelfType.Self


INIT_SCRIPT_FILENAME = "__init__.py"
FEVENT_SCRIPT_NAME_REGEX = re.compile(r"([0-9a-fA-F]+)(?:_(enemies))?")


type ComparisonOperator = typing.Literal[
    "==", "!=", "<", ">", "<=", ">=", "&", "|", "^", "== 0", "!= -1"
]
COMPARISON_OPERATORS: bidict.bidict[int, ComparisonOperator] = bidict.bidict(
    dict[int, ComparisonOperator](
        {
            0x00: "==",
            0x01: "!=",
            0x02: "<",
            0x03: ">",
            0x04: "<=",
            0x05: ">=",
            0x06: "&",
            0x07: "|",
            0x08: "^",
            0x09: "== 0",
            0x0A: "!= -1",
        }
    )
)


class StackTopModification(enum.IntEnum):
    NONE = 0x0
    INCREMENT_AFTER = 0x1
    DECREMENT_AFTER = 0x2
    INCREMENT_BEFORE = 0x3
    DECREMENT_BEFORE = 0x4


class StackPopCondition(enum.IntEnum):
    NEVER = 0x0
    IF_TRUE = 0x1
    IF_FALSE = 0x2


class Screen(enum.IntEnum):
    TOP = 0
    BOTTOM = 1
