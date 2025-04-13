# TODO: Fix type annotations and remove asserts once
# concatenating keyword parameters is added.


import ctypes
import typing
import mnllib
import pymsbmnl

from ..commands import (
    arithmetic_0_param_command,
    arithmetic_1_param_command,
    arithmetic_2_param_command,
    command_emitter,
    emit_command_with_offsets,
    emit_command,
)
from ..consts import (
    COMPARISON_OPERATORS,
    ComparisonOperator,
    Screen,
    StackPopCondition,
    StackTopModification,
)
from ..misc import emit_debug_message
from ..script import OFFSET_FOOTER, Offset
from .consts import (
    PLACEHOLDER_OFFSET,
    ActorAttribute,
    BottomScreenButton,
    ButtonFlags,
    CameraMode,
    FirstStrike,
    MusicFlag,
    TextboxAlignment,
    TextboxFlags,
    TextboxTailType,
    Transition,
    WorldType,
)
from .globals import Globals
from .misc import TextboxSounds, parse_rgba_or_neg1
from .sound import Sound
from .text import emit_text_entry


def sound_to_int(
    sound: Sound | str | int | mnllib.Variable, bank_shift: int = 24
) -> int | mnllib.Variable:
    if isinstance(sound, str):
        sound = Globals.sound_names.inverse[sound]
    if isinstance(sound, Sound):
        return (sound.bank << bank_shift) | sound.sound_id
    return sound


@command_emitter()
def branch_if(
    a: float | mnllib.Variable,
    operation: ComparisonOperator | int | mnllib.Variable,
    b: float | mnllib.Variable,
    target: Offset | mnllib.Variable,
    *,
    invert: bool | int | mnllib.Variable = False,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(operation, str):
        operation = COMPARISON_OPERATORS.inverse[operation]
    if isinstance(invert, bool):
        invert = int(not invert)

    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0002,
            [operation, a, b, invert, PLACEHOLDER_OFFSET],
            offset_arguments={4: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(
            0x0002, [operation, a, b, invert, target], subroutine=subroutine
        )


@command_emitter()
def branch(
    target: Offset | mnllib.Variable,
    *,
    type: int | mnllib.Variable = 0x02,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0003,
            [type, PLACEHOLDER_OFFSET],
            offset_arguments={1: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0003, [type, target], subroutine=subroutine)


@command_emitter()
def call(
    target: Offset | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return branch(target, type=0x01, subroutine=subroutine)


@command_emitter()
def wait(
    frames: int | mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0004, [frames], subroutine=subroutine)


def push(
    value: int | float | mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0005, [value], subroutine=subroutine)


@command_emitter()
def pop(
    res: mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0006, [], res, subroutine=subroutine)


@command_emitter()
def branch_if_stack(
    operation: ComparisonOperator | int | float | mnllib.Variable,
    b: float | mnllib.Variable,
    target: Offset | mnllib.Variable,
    modification: StackTopModification | int = StackTopModification.NONE,
    pop: StackPopCondition | int = StackPopCondition.NEVER,
    *,
    additional_operations_arg: int | mnllib.Variable | None = None,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(operation, str):
        operation = COMPARISON_OPERATORS.inverse[operation]
    if additional_operations_arg is None:
        additional_operations_arg = modification | (pop << 4)

    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0007,
            [additional_operations_arg, operation, b, PLACEHOLDER_OFFSET],
            offset_arguments={3: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(
            0x0007,
            [additional_operations_arg, operation, b, target],
            subroutine=subroutine,
        )


@command_emitter()
def load_data_from_array(
    array_offset: Offset | mnllib.Variable,
    index: int | mnllib.Variable,
    *,
    res: mnllib.Variable,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(array_offset, (str, tuple)):
        return emit_command_with_offsets(
            0x000C,
            [PLACEHOLDER_OFFSET, index],
            res,
            offset_arguments={0: array_offset},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x000C, [array_offset, index], res, subroutine=subroutine)


@command_emitter()
def load_data(
    offset: Offset | mnllib.Variable,
    *,
    res: mnllib.Variable,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(offset, (str, tuple)):
        return emit_command_with_offsets(
            0x000D,
            [PLACEHOLDER_OFFSET],
            res,
            offset_arguments={0: offset},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x000D, [offset], res, subroutine=subroutine)


@command_emitter()
def set_variable(
    value: float | mnllib.Variable,
    res: mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x000E, [value], res, subroutine=subroutine)


add = arithmetic_2_param_command("add", 0x000F)
subtract = arithmetic_2_param_command("subtract", 0x0010)
multiply = arithmetic_2_param_command("multiply", 0x0011)
divide = arithmetic_2_param_command("divide", 0x0012)
modulo = arithmetic_2_param_command("modulo", 0x0013)
logical_shift_left = arithmetic_2_param_command("logical_shift_left", 0x0014)
logical_shift_right = arithmetic_2_param_command("logical_shift_right", 0x0015)
bitwise_and = arithmetic_2_param_command("bitwise_and", 0x0016)
bitwise_or = arithmetic_2_param_command("bitwise_or", 0x0017)
bitwise_xor = arithmetic_2_param_command("bitwise_xor", 0x0018)
add_in_place = arithmetic_1_param_command("add_in_place", 0x001E)
subtract_in_place = arithmetic_1_param_command("subtract_in_place", 0x001F)
multiply_in_place = arithmetic_1_param_command("multiply_in_place", 0x0020)
divide_in_place = arithmetic_1_param_command("divide_in_place", 0x0021)
modulo_in_place = arithmetic_1_param_command("modulo_in_place", 0x0022)
logical_shift_left_in_place = arithmetic_1_param_command(
    "logical_shift_left_in_place", 0x0023
)
logical_shift_right_in_place = arithmetic_1_param_command(
    "logical_shift_right_in_place", 0x0024
)
bitwise_and_in_place = arithmetic_1_param_command("bitwise_and_in_place", 0x0025)
bitwise_or_in_place = arithmetic_1_param_command("bitwise_or_in_place", 0x0026)
bitwise_xor_in_place = arithmetic_1_param_command("bitwise_xor_in_place", 0x0027)

negate = arithmetic_1_param_command("negate", 0x0019)
to_boolean = arithmetic_1_param_command("to_boolean", 0x001A)
bitwise_not = arithmetic_1_param_command("bitwise_not", 0x001B)
increment = arithmetic_0_param_command("increment", 0x001C)
decrement = arithmetic_0_param_command("decrement", 0x001D)


@command_emitter()
def debug_message(
    message: str | Offset | mnllib.Variable,
    *,
    command_id: int,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(message, (str, tuple)):
        return emit_command_with_offsets(
            command_id,
            [PLACEHOLDER_OFFSET],
            offset_arguments={
                0: (
                    (f"subs[-1].{OFFSET_FOOTER}", emit_debug_message(message))
                    if isinstance(message, str)
                    else message
                ),
            },
            subroutine=subroutine,
        )
    else:
        return emit_command(command_id, [message], subroutine=subroutine)


@command_emitter()
def debugln(
    message: str | Offset | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return debug_message(message, command_id=0x0039, subroutine=subroutine)


@command_emitter()
def debug(
    message: str | Offset | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return debug_message(message, command_id=0x003A, subroutine=subroutine)


@command_emitter()
def debug_float(
    number: int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x003B, [number], subroutine=subroutine)


@command_emitter()
def debug_bin(
    number: int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x003C, [number], subroutine=subroutine)


@command_emitter()
def debug_hex(
    number: int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x003D, [number], subroutine=subroutine)


@command_emitter()
def start_thread_here_and_branch(
    thread_id: int | mnllib.Variable,
    target: Offset | mnllib.Variable,
    *,
    unk2: int | mnllib.Variable = 0x00,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0041,
            [thread_id, unk2, PLACEHOLDER_OFFSET],
            offset_arguments={2: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0041, [thread_id, unk2, target], subroutine=subroutine)


@command_emitter()
def unk_thread_branch_0x0042(
    thread_id: int | mnllib.Variable,
    target: Offset | mnllib.Variable,
    *,
    unk2: int | mnllib.Variable = 0x00,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0042,
            [thread_id, unk2, PLACEHOLDER_OFFSET],
            offset_arguments={2: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0042, [thread_id, unk2, target], subroutine=subroutine)


@command_emitter()
def branch_in_thread(
    thread_id: int | mnllib.Variable,
    target: Offset | mnllib.Variable,
    *,
    unk2: int | mnllib.Variable = 0x00,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0043,
            [thread_id, unk2, PLACEHOLDER_OFFSET],
            offset_arguments={2: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0043, [thread_id, unk2, target], subroutine=subroutine)


@command_emitter()
def join_thread(
    thread_id: int | mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0044, [thread_id], subroutine=subroutine)


@command_emitter()
def execute_on_bottom_screen(
    target: Offset | mnllib.Variable,
    *,
    unk1: int | mnllib.Variable,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0057,
            [unk1, PLACEHOLDER_OFFSET],
            offset_arguments={1: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0057, [unk1, target], subroutine=subroutine)


@command_emitter()
def set_blocked_buttons(
    screen: Screen | int | mnllib.Variable,
    buttons: ButtonFlags | int | mnllib.Variable,
    *,
    unk2: int | mnllib.Variable = 0x00,
    res: mnllib.Variable = mnllib.Variable(0x1000),
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x005A, [screen, unk2, buttons], res, subroutine=subroutine)


@command_emitter()
def set_movement_multipliers(
    screen: Screen | int | mnllib.Variable,
    horizontal: float | mnllib.Variable,
    vertical: float | mnllib.Variable,
    *,
    unk2: int | mnllib.Variable = 0x00,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    """
    Although most multipliers are interpreted as either
    "fully block" (`0.0`) or "fully allow" (`1.0`),
    negative values reverse the direction of movement (at the same normal speed),
    and infinity sometimes makes all movement (even vertical) go to the right.
    """
    return emit_command(
        0x005D, [screen, unk2, horizontal, vertical], subroutine=subroutine
    )


@command_emitter()
def set_touches_blocked(
    value: bool | int | mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(
        0x005F,
        [int(value) if isinstance(value, bool) else value],
        subroutine=subroutine,
    )


@command_emitter()
def start_battle(
    encounter_id: int | mnllib.Variable,
    world: WorldType | int | mnllib.Variable,
    *,
    transition: Transition | int | mnllib.Variable = Transition.NORMAL,
    first_strike: FirstStrike | int | mnllib.Variable = FirstStrike.NONE,
    music: Sound | str | int | mnllib.Variable = 0x00000000,
    unk3: int | mnllib.Variable = 0x0000,
    unk4: int | mnllib.Variable,
    unk5: int | mnllib.Variable = 0x00,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(
        0x0068,
        [
            encounter_id,
            world,
            unk3,
            unk4,
            unk5,
            first_strike,
            transition,
            sound_to_int(music),
        ],
        subroutine=subroutine,
    )


@command_emitter()
def tint_screen(
    tint: (
        str
        | tuple[
            int | mnllib.Variable,
            int | mnllib.Variable,
            int | mnllib.Variable,
            int | mnllib.Variable,
        ]
    ),
    *,
    initial: (
        str
        | tuple[
            int | mnllib.Variable,
            int | mnllib.Variable,
            int | mnllib.Variable,
            int | mnllib.Variable,
        ]
    ) = (-0x0001, -0x0001, -0x0001, -0x0001),
    transition_duration: int | mnllib.Variable,
    wait: bool = True,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(initial, str):
        initial = parse_rgba_or_neg1(initial)
    if isinstance(tint, str):
        tint = parse_rgba_or_neg1(tint)

    tint_screen_cmd = emit_command(
        0x0075, [*initial, *tint, transition_duration], subroutine=subroutine
    )

    if wait:
        wait_for_screen_tint(subroutine=subroutine)

    return tint_screen_cmd


@command_emitter()
def wait_for_screen_tint(
    *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0076, subroutine=subroutine)


@command_emitter()
def get_actor_attribute(
    actor: int | mnllib.Variable,
    attribute: ActorAttribute | int | mnllib.Variable,
    *,
    res: mnllib.Variable,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x0079, [actor, attribute], res, subroutine=subroutine)


@command_emitter()
def set_actor_attribute(
    actor: int | mnllib.Variable,
    attribute: ActorAttribute | int | mnllib.Variable,
    value: int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x007A, [actor, attribute, value], subroutine=subroutine)


@command_emitter()
def set_animation(
    actor: int | mnllib.Variable,
    animation: int | mnllib.Variable,
    *,
    unk3: int | mnllib.Variable = 0x01,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x0087, [actor, animation, unk3], subroutine=subroutine)


@command_emitter()
def set_action_icons_shown(
    value: bool | int | mnllib.Variable,
    *,
    animated: bool | int | mnllib.Variable = True,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(
        0x00E3,
        [
            int(value) if isinstance(value, bool) else value,
            int(animated) if isinstance(animated, bool) else animated,
        ],
        subroutine=subroutine,
    )


@command_emitter()
def set_camera_mode(
    mode: CameraMode | int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x010A, [mode], subroutine=subroutine)


@command_emitter()
def move_camera(
    position: tuple[
        float | mnllib.Variable, float | mnllib.Variable, float | mnllib.Variable
    ],
    *,
    unk5: float | mnllib.Variable,
    unk6: float | mnllib.Variable,
    unk7: float | mnllib.Variable,
    unk8: float | mnllib.Variable,
    relative: bool | int | mnllib.Variable = False,
    unk9: bool | int | mnllib.Variable = True,
    endless: bool | int | mnllib.Variable = False,
    wait: bool = True,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    move_camera_cmd = emit_command(
        0x010C,
        [
            int(relative) if isinstance(relative, bool) else relative,
            *position,
            unk5,
            unk6,
            unk7,
            unk8,
            int(unk9) if isinstance(unk9, bool) else unk9,
            int(not endless) if isinstance(endless, bool) else endless,
        ],
        subroutine=subroutine,
    )

    if wait:
        wait_for_camera(subroutine=subroutine)

    return move_camera_cmd


@command_emitter()
def wait_for_camera(
    *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0110, subroutine=subroutine)


@command_emitter()
def rotate_camera(
    rotation: tuple[
        float | mnllib.Variable, float | mnllib.Variable, float | mnllib.Variable
    ],
    *,
    speed: tuple[
        float | mnllib.Variable, float | mnllib.Variable, float | mnllib.Variable
    ],
    relative: bool | int | mnllib.Variable = False,
    around_focus: bool | int | mnllib.Variable,
    endless: bool | int | mnllib.Variable = False,
    wait: bool = True,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    rotate_camera_cmd = emit_command(
        0x0113,
        [
            int(relative) if isinstance(relative, bool) else relative,
            int(around_focus) if isinstance(around_focus, bool) else around_focus,
            *rotation,
            *speed,
            int(not endless) if isinstance(endless, bool) else endless,
        ],
        subroutine=subroutine,
    )

    if wait:
        wait_for_camera(subroutine=subroutine)

    return rotate_camera_cmd


@command_emitter()
def change_room(
    room_id: int | mnllib.Variable,
    position: tuple[
        float | mnllib.Variable, float | mnllib.Variable, float | mnllib.Variable
    ],
    *,
    init_sub: int | mnllib.Variable,
    facing: int | mnllib.Variable = 0,
    step_forward: bool | int | mnllib.Variable = False,
    music: (
        Sound | str | int | MusicFlag | mnllib.Variable
    ) = MusicFlag.RESTART_ONLY_IF_DIFFERENT,
    unk9: int | mnllib.Variable = 0x00,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(
        0x0138,
        [
            room_id,
            *position,
            facing,
            int(step_forward) if isinstance(step_forward, bool) else step_forward,
            init_sub,
            sound_to_int(music),
            unk9,
        ],
        subroutine=subroutine,
    )


@command_emitter()
def set_bottom_screen_button_shown(
    button: BottomScreenButton | int | mnllib.Variable,
    value: bool | int | mnllib.Variable,
    *,
    animated: bool | int | mnllib.Variable = True,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(
        0x013B,
        [
            button,
            int(value) if isinstance(value, bool) else value,
            int(animated) if isinstance(animated, bool) else animated,
        ],
        subroutine=subroutine,
    )


@command_emitter()
def show_textbox(
    actor: int | mnllib.Variable | None,
    message: (
        str
        | pymsbmnl.LMSMessage
        | dict[str, str | pymsbmnl.LMSMessage]
        | int
        | mnllib.Variable
    ),
    *,
    offset: tuple[
        float | mnllib.Variable, float | mnllib.Variable, float | mnllib.Variable
    ] = (0.0, 0.0, 0.0),
    tail_hoffset: float | mnllib.Variable | None = None,
    flags: TextboxFlags | int | mnllib.Variable = (
        TextboxFlags.REMOVE_WHEN_DISMISSED | 2
    ),
    tail: TextboxTailType | int | None = None,
    alignment: TextboxAlignment | int = TextboxAlignment.AUTOMATIC,
    properties_arg: int | mnllib.Variable | None = None,
    unk1: int | mnllib.Variable = -0x01,
    unk7: int | mnllib.Variable = 0x0000,
    unk8: int | mnllib.Variable = 0x0000,
    unk_sound: Sound | str | int | mnllib.Variable | None = None,
    res_textbox_id: mnllib.Variable = mnllib.Variable(0x1000),
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if actor is None:
        actor = -1
    if tail is None:
        tail = TextboxTailType.LARGE if actor != -1 else TextboxTailType.NONE

    if isinstance(message, (str, pymsbmnl.LMSMessage, dict)):
        message_id: int | mnllib.Variable | None = emit_text_entry(message)
    else:
        message_id = message

    return emit_command(
        0x014C,
        [
            unk1,
            (
                ctypes.c_byte(message_id).value
                if isinstance(message_id, int)
                else message_id
            ),
            actor,
            *offset,
            unk7,
            unk8,
            flags,
            tail_hoffset if tail_hoffset is not None else 4096.0,
            properties_arg if properties_arg is not None else (tail | (alignment << 3)),
            sound_to_int(unk_sound, bank_shift=16) if unk_sound is not None else 0,
        ],
        res_textbox_id,
        subroutine=subroutine,
    )


@command_emitter()
def wait_for_textbox(
    textbox_id: int | mnllib.Variable = mnllib.Variable(0x1000),
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x014D, [textbox_id], subroutine=subroutine)


@typing.overload
def set_textbox_sounds(
    sounds: (
        TextboxSounds
        | tuple[
            Sound | str | int | mnllib.Variable, Sound | str | int | mnllib.Variable
        ]
    ),
    /,
    *,
    textbox_id: int | mnllib.Variable = mnllib.Variable(0x1000),
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand: ...
@typing.overload
def set_textbox_sounds(
    normal: Sound | str | int | mnllib.Variable,
    fast_forwarded: Sound | str | int | mnllib.Variable,
    *,
    textbox_id: int | mnllib.Variable = mnllib.Variable(0x1000),
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand: ...


@command_emitter()
def set_textbox_sounds(
    normal: (
        TextboxSounds
        | tuple[
            Sound | str | int | mnllib.Variable, Sound | str | int | mnllib.Variable
        ]
        | Sound
        | str
        | int
        | mnllib.Variable
    ),
    fast_forwarded: Sound | str | int | mnllib.Variable | None = None,
    *,
    textbox_id: int | mnllib.Variable = mnllib.Variable(0x1000),
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(normal, TextboxSounds):
        if fast_forwarded is not None:
            raise TypeError(
                "the 2nd argument must not be specified if the 1st is a TextboxSounds"
            )
        normal_arg: Sound | str | int | mnllib.Variable = normal.normal
        fast_forwarded_arg: Sound | str | int | mnllib.Variable = normal.fast_forwarded
    elif isinstance(normal, tuple):
        if fast_forwarded is not None:
            raise TypeError(
                "the 2nd argument must not be specified if the 1st is a tuple"
            )
        normal_arg = normal[0]
        fast_forwarded_arg = normal[1]
    else:
        if fast_forwarded is None:
            raise TypeError(
                "fast_forwarded must not be None if the sounds are provided separately"
            )
        normal_arg = normal
        fast_forwarded_arg = fast_forwarded

    return emit_command(
        0x0150,
        [
            textbox_id,
            sound_to_int(normal_arg, bank_shift=16),
            sound_to_int(fast_forwarded_arg, bank_shift=16),
        ],
        subroutine=subroutine,
    )


@command_emitter()
def say(
    actor: int | mnllib.Variable | None,
    sounds: (
        TextboxSounds
        | tuple[
            Sound | str | int | mnllib.Variable, Sound | str | int | mnllib.Variable
        ]
        | None
    ),
    message: (
        pymsbmnl.LMSMessage
        | dict[str, str | pymsbmnl.LMSMessage]
        | int
        | mnllib.Variable
    ),
    *,
    offset: tuple[
        float | mnllib.Variable, float | mnllib.Variable, float | mnllib.Variable
    ] = (0.0, 0.0, 0.0),
    anim: int | mnllib.Variable | None = 0x01,
    post_anim: int | mnllib.Variable | None = 0x03,
    wait: bool | int | mnllib.Variable = True,
    tail_hoffset: float | mnllib.Variable | None = None,
    flags: TextboxFlags | int | mnllib.Variable = (
        TextboxFlags.REMOVE_WHEN_DISMISSED | 2
    ),
    tail: TextboxTailType | int | None = None,
    alignment: TextboxAlignment | int = TextboxAlignment.AUTOMATIC,
    properties_arg: int | mnllib.Variable | None = None,
    unk1: int | mnllib.Variable = -0x01,
    unk7: int | mnllib.Variable = 0x0000,
    unk8: int | mnllib.Variable = 0x0000,
    unk_sound: Sound | str | int | mnllib.Variable | None = None,
    res_textbox_id: mnllib.Variable = mnllib.Variable(0x1000),
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if actor is None:
        actor = -1

    if actor != -1 and anim is not None:
        set_animation(actor, anim, subroutine=subroutine)

    show_textbox_cmd = show_textbox(
        actor=actor,
        message=message,
        offset=offset,
        tail_hoffset=tail_hoffset,
        flags=flags,
        tail=tail,
        alignment=alignment,
        properties_arg=properties_arg,
        unk1=unk1,
        unk7=unk7,
        unk8=unk8,
        unk_sound=unk_sound,
        res_textbox_id=res_textbox_id,
        subroutine=subroutine,
    )

    if sounds is not None:
        set_textbox_sounds(sounds, textbox_id=res_textbox_id, subroutine=subroutine)
    if wait:
        wait_for_textbox(res_textbox_id, subroutine=subroutine)
    if actor != -1 and post_anim is not None:
        set_animation(actor, post_anim, subroutine=subroutine)

    return show_textbox_cmd
