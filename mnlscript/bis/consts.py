import enum


PLACEHOLDER_OFFSET = 0x7BAD


class Actors(enum.IntEnum):
    MARIO = 0x00
    LUIGI = 0x01
    BOWSER = 0x02


class PlayerStat(enum.IntEnum):
    BASE_HP = 0x00
    BASE_SP = 0x01
    BASE_POW = 0x02
    BASE_DEF = 0x03
    BASE_SPEED = 0x04
    BASE_STACHE = 0x05
    MAX_HP = 0x06
    CURRENT_HP = 0x07
    MAX_SP = 0x08
    CURRENT_SP = 0x09
    CURRENT_POW = 0x0A
    CURRENT_DEF = 0x0B
    CURRENT_SPEED = 0x0C
    CURRENT_STACHE = 0x0D
    RANK = 0x0E
    EXP = 0x11
    GEAR_AMOUNT = 0x15
    GEAR_PIECE_1 = 0x16
    GEAR_PIECE_2 = 0x17
    GEAR_PIECE_3 = 0x18
    BADGE = 0x19


class ActorAttribute(enum.IntEnum):
    X_POSITION = 0x0B
    Y_POSITION = 0x0C
    Z_POSITION = 0x0D


class BubbleType(enum.IntEnum):
    NONE = 0x00
    NORMAL = 0x01
    SHOUTING = 0x02


class TailType(enum.IntEnum):
    NONE = 0x00
    NORMAL = 0x01
    SHOUTING = 0x03


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
