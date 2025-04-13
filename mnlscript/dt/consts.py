import enum

from .misc import TextboxSounds
from .sound import Sound


PLACEHOLDER_OFFSET = 0x7BADF00D


class Sounds(Sound, enum.Enum):
    SPEECH_GENERIC_LOW = 1, 0x0004
    SPEECH_GENERIC_LOW_FF = 1, 0x0005
    SPEECH_TOAD = 1, 0x0006
    SPEECH_TOAD_FF = 1, 0x0007
    SPEECH_GENERIC_HIGH = 1, 0x0008
    SPEECH_GENERIC_HIGH_FF = 1, 0x0009
    SPEECH_BOWSER = 1, 0x000A
    SPEECH_BOWSER_FF = 1, 0x000B
    SPEECH_STARLOW = 1, 0x000C
    SPEECH_STARLOW_FF = 1, 0x000D
    SPEECH_PEACH = 1, 0x000E
    SPEECH_PEACH_FF = 1, 0x000F
    SPEECH_ANTASMA = 1, 0x0010
    SPEECH_ANTASMA_FF = 1, 0x0011
    SPEECH_SILENT = 2, 0x03D1
    SPEECH_SILENT_FF = 2, 0x03D2


class ButtonFlags(enum.IntFlag):
    NONE = 0

    A = 1 << 0x00
    B = 1 << 0x01
    SELECT = 1 << 0x02
    START = 1 << 0x03
    RIGHT = 1 << 0x04
    LEFT = 1 << 0x05
    UP = 1 << 0x06
    DOWN = 1 << 0x07
    R = 1 << 0x08
    L = 1 << 0x09
    X = 1 << 0x0A
    Y = 1 << 0x0B
    DEBUG = 1 << 0x0C
    GPIO14 = 1 << 0x0D

    CIRCLE_PAD_RIGHT = 1 << 0x1C
    CIRCLE_PAD_LEFT = 1 << 0x1D
    CIRCLE_PAD_UP = 1 << 0x1E
    CIRCLE_PAD_DOWN = 1 << 0x1F

    ALL = 0xFFF


class WorldType(enum.IntEnum):
    REAL = 0x00
    DREAM = 0x01


class Transition(enum.IntEnum):
    NONE = 0x00
    NORMAL = 0x01
    BOSS = 0x02
    BOWSER = 0x03


class FirstStrike(enum.IntEnum):
    NONE = 0x00
    JUMP = 0x01
    HAMMER = 0x02
    JUMP_ON_SPIKY_ENEMY = 0x03
    TRIP_AND_FALL = 0x04


class Actors(enum.IntEnum):
    MARIO = 0x00
    LUIGI = 0x01


class ActorAttribute(enum.IntEnum):
    X_POSITION = 0x02
    Y_POSITION = 0x03
    Z_POSITION = 0x04
    GRAVITY1 = 0x25
    RETAIN_Y = 0x29
    WALL_COLLISION = 0x2B
    GRAVITY2 = 0x2C
    OBJECT_COLLISION = 0x31


class CameraMode(enum.IntEnum):
    LOCKED = 0x00
    UNLOCKED = 0x01
    SPIRAL = 0x02


class MusicFlag(enum.IntEnum):
    NO_MUSIC = 0x00000000
    RESTART_ONLY_IF_DIFFERENT = 0xFFFFFFFD
    FORCE_KEEP_CURRENT = 0xFFFFFFFE
    FORCE_RESTART = 0xFFFFFFFF


class BottomScreenButton(enum.IntEnum):
    WORLD = 0x00
    MENU = 0x01
    SAVE = 0x02
    ZOOM = 0x04


class TextboxFlags(enum.IntFlag):
    NONE = 0

    REMOVE_WHEN_DISMISSED = 1 << 0x00


class TextboxTailType(enum.IntEnum):
    NONE = 0x0
    SMALL = 0x1
    LARGE1 = 0x2
    LEFT_ANGLED = 0x3
    THINKING = 0x4
    LARGE = 0x5


class TextboxAlignment(enum.IntEnum):
    BOTTOM_LEFT = 0x0
    BOTTOM_CENTER = 0x1
    BOTTOM_RIGHT = 0x2
    MIDDLE_RIGHT = 0x3
    MIDDLE_LEFT = 0x4
    TOP_RIGHT = 0x5
    TOP_CENTER = 0x6
    TOP_LEFT = 0x7
    AUTOMATIC = 0x8
    SCREEN_TOP_CENTER = 0x9


class TextboxSoundsPreset(TextboxSounds, enum.Enum):
    SILENT = Sounds.SPEECH_SILENT, Sounds.SPEECH_SILENT_FF

    GENERIC_LOW = Sounds.SPEECH_GENERIC_LOW, Sounds.SPEECH_GENERIC_LOW_FF
    TOAD = Sounds.SPEECH_TOAD, Sounds.SPEECH_TOAD_FF
    GENERIC_HIGH = Sounds.SPEECH_GENERIC_HIGH, Sounds.SPEECH_GENERIC_HIGH_FF
    BOWSER = Sounds.SPEECH_BOWSER, Sounds.SPEECH_BOWSER_FF
    STARLOW = Sounds.SPEECH_STARLOW, Sounds.SPEECH_STARLOW_FF
    PEACH = Sounds.SPEECH_PEACH, Sounds.SPEECH_PEACH_FF
    ANTASMA = Sounds.SPEECH_ANTASMA, Sounds.SPEECH_ANTASMA_FF
