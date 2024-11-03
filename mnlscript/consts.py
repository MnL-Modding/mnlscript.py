import re
import enum


class SelfType(enum.Enum):
    Self = object()


Self = SelfType.Self


PADDING_TEXT_TABLE_ID = 0x49


FEVENT_SCRIPT_NAME_REGEX = re.compile(r"([0-9a-fA-F]+)(?:_(\d+))?")


class BubbleType(enum.IntEnum):
    NONE = 0x00
    NORMAL = 0x01
    SCREAMING = 0x02


class TailType(enum.IntEnum):
    NONE = 0x00
    NORMAL = 0x01
    SCREAMING = 0x03


class TextboxColor(enum.IntEnum):
    NORMAL = -0x01
    SYSTEM = 0x01


# class Animation(enum.IntEnum):
#     SPEAKING = 0x01
#     IDLE = 0x03


class Sound(enum.IntEnum):
    NONE = 0x00000000
    SPEECH_BOWSER = 0x0002014F
    SPEECH_FAWFUL = 0x00020153
    SPEECH_TOAD = 0x00024149
