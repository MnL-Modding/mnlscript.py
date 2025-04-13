# TODO: Fix type annotations and remove asserts once
# concatenating keyword parameters is added.


import typing

import mnllib

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
    Self,
    SelfType,
    StackPopCondition,
    StackTopModification,
)
from ..misc import emit_debug_message
from ..script import OFFSET_FOOTER, Offset
from .consts import PLACEHOLDER_OFFSET, BubbleType, TailType, TextboxColor
from .text import LanguageName, TextEntryDefinition, emit_text_entry


COMMON_ARITHMETIC_COMMANDS = [
    "add",
    "subtract",
    "multiply",
    "divide",
    "modulo",
]
COMMON_ARITHMETIC_COMMANDS_2 = ["sqrt", "invsqrt", "invert", "sin", "cos", "atan"]
INTEGER_ARITHMETIC_COMMANDS = [
    "logical_shift_left",
    "logical_shift_right",
    "bitwise_and",
    "bitwise_or",
    "bitwise_xor",
]


@command_emitter()
def branch_if(
    a: int | mnllib.Variable,
    operation: ComparisonOperator | int | mnllib.Variable,
    b: int | mnllib.Variable,
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


@command_emitter()
def push(
    value: int | mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0005, [value], subroutine=subroutine)


@command_emitter()
def pop(
    res: mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0006, [], res, subroutine=subroutine)


@command_emitter()
def branch_if_stack(
    operation: ComparisonOperator | int | mnllib.Variable,
    b: int | mnllib.Variable,
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
def set_variable(
    value: int | mnllib.Variable,
    res: mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x0008, [value], res, subroutine=subroutine)


# This doesn't work for type checking, unfortunately.
# for i, name in enumerate(
#     itertools.chain(COMMON_ARITHMETIC_COMMANDS, INTEGER_ARITHMETIC_COMMANDS)
# ):
#     _globals[name] = arithmetic_2_param_command(name, 0x0009 + i)
#
#     assign_command_name = name + "_in_place"
#     _globals[assign_command_name] = arithmetic_1_param_command(
#         assign_command_name, 0x0018 + i
#     )
add = arithmetic_2_param_command("add", 0x0009)
subtract = arithmetic_2_param_command("subtract", 0x000A)
multiply = arithmetic_2_param_command("multiply", 0x000B)
divide = arithmetic_2_param_command("divide", 0x000C)
modulo = arithmetic_2_param_command("modulo", 0x000D)
logical_shift_left = arithmetic_2_param_command("logical_shift_left", 0x000E)
logical_shift_right = arithmetic_2_param_command("logical_shift_right", 0x000F)
bitwise_and = arithmetic_2_param_command("bitwise_and", 0x0010)
bitwise_or = arithmetic_2_param_command("bitwise_or", 0x0011)
bitwise_xor = arithmetic_2_param_command("bitwise_xor", 0x0012)
add_in_place = arithmetic_1_param_command("add_in_place", 0x0018)
subtract_in_place = arithmetic_1_param_command("subtract_in_place", 0x0019)
multiply_in_place = arithmetic_1_param_command("multiply_in_place", 0x001A)
divide_in_place = arithmetic_1_param_command("divide_in_place", 0x001B)
modulo_in_place = arithmetic_1_param_command("modulo_in_place", 0x001C)
logical_shift_left_in_place = arithmetic_1_param_command(
    "logical_shift_left_in_place", 0x001D
)
logical_shift_right_in_place = arithmetic_1_param_command(
    "logical_shift_right_in_place", 0x001E
)
bitwise_and_in_place = arithmetic_1_param_command("bitwise_and_in_place", 0x001F)
bitwise_or_in_place = arithmetic_1_param_command("bitwise_or_in_place", 0x0020)
bitwise_xor_in_place = arithmetic_1_param_command("bitwise_xor_in_place", 0x0021)

negate = arithmetic_1_param_command("negate", 0x0013)
to_boolean = arithmetic_1_param_command("to_boolean", 0x0014)
bitwise_not = arithmetic_1_param_command("bitwise_not", 0x0015)
increment = arithmetic_0_param_command("increment", 0x0016)
decrement = arithmetic_0_param_command("decrement", 0x0017)

# for i, name in enumerate(COMMON_ARITHMETIC_COMMANDS_2):
#     _globals[name] = arithmetic_1_param_command(name, 0x0022 + i)
#
#     fx_command_name = "fx_" + name
#     _globals[fx_command_name] = arithmetic_1_param_command(
#         fx_command_name, 0x0032 + i
#     )
sqrt = arithmetic_1_param_command("sqrt", 0x0022)
invsqrt = arithmetic_1_param_command("invsqrt", 0x0023)
invert = arithmetic_1_param_command("invert", 0x0024)
sin = arithmetic_1_param_command("sin", 0x0025)
cos = arithmetic_1_param_command("cos", 0x0026)
atan = arithmetic_1_param_command("atan", 0x0027)
fx_sqrt = arithmetic_1_param_command("fx_sqrt", 0x0032)
fx_invsqrt = arithmetic_1_param_command("fx_invsqrt", 0x0033)
fx_invert = arithmetic_1_param_command("fx_invert", 0x0034)
fx_sin = arithmetic_1_param_command("fx_sin", 0x0035)
fx_cos = arithmetic_1_param_command("fx_cos", 0x0036)
fx_atan = arithmetic_1_param_command("fx_atan", 0x0037)

atan2 = arithmetic_2_param_command("atan2", 0x0028)
random_below = arithmetic_1_param_command("random_below", 0x0029)

fx_set_variable = arithmetic_1_param_command("fx_set_variable", 0x002A)

# for i, name in enumerate(COMMON_ARITHMETIC_COMMANDS):
#     fx_command_name = "fx_" + name
#     _globals[fx_command_name] = arithmetic_2_param_command(
#         fx_command_name, 0x002B + i
#     )
fx_add = arithmetic_2_param_command("fx_add", 0x002B)
fx_subtract = arithmetic_2_param_command("fx_subtract", 0x002C)
fx_multiply = arithmetic_2_param_command("fx_multiply", 0x002D)
fx_divide = arithmetic_2_param_command("fx_divide", 0x002E)
fx_modulo = arithmetic_2_param_command("fx_modulo", 0x002F)

fx_to_int = arithmetic_1_param_command("fx_to_int", 0x0030)
fx_trunc = arithmetic_1_param_command("fx_trunc", 0x0031)
fx_atan2 = arithmetic_2_param_command("fx_atan2", 0x0038)


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
            0x0039,
            [PLACEHOLDER_OFFSET, index],
            res,
            offset_arguments={0: array_offset},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0039, [array_offset, index], res, subroutine=subroutine)


@command_emitter()
def load_data(
    offset: Offset | mnllib.Variable,
    *,
    res: mnllib.Variable,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(offset, (str, tuple)):
        return emit_command_with_offsets(
            0x003A,
            [PLACEHOLDER_OFFSET],
            res,
            offset_arguments={0: offset},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x003A, [offset], res, subroutine=subroutine)


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
    return debug_message(message, command_id=0x003B, subroutine=subroutine)


@command_emitter()
def debug(
    message: str | Offset | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return debug_message(message, command_id=0x003C, subroutine=subroutine)


@command_emitter()
def debug_bin(
    number: int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x003D, [number], subroutine=subroutine)


@command_emitter()
def debug_dec(
    number: int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x003E, [number], subroutine=subroutine)


@command_emitter()
def debug_hex(
    number: int | mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(0x003F, [number], subroutine=subroutine)


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
            0x0049,
            [thread_id, unk2, PLACEHOLDER_OFFSET],
            offset_arguments={2: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0049, [thread_id, unk2, target], subroutine=subroutine)


@command_emitter()
def unk_thread_branch_0x004a(
    thread_id: int | mnllib.Variable,
    target: Offset | mnllib.Variable,
    *,
    unk2: int | mnllib.Variable = 0x00,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x004A,
            [thread_id, unk2, PLACEHOLDER_OFFSET],
            offset_arguments={2: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x004A, [thread_id, unk2, target], subroutine=subroutine)


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
            0x004B,
            [thread_id, unk2, PLACEHOLDER_OFFSET],
            offset_arguments={2: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x004B, [thread_id, unk2, target], subroutine=subroutine)


@command_emitter()
def join_thread(
    thread_id: int | mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x004C, [thread_id], subroutine=subroutine)


@command_emitter()
def execute_on_secondary_screen(
    target: Offset | mnllib.Variable,
    *,
    unk1: int | mnllib.Variable,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if isinstance(target, (str, tuple)):
        return emit_command_with_offsets(
            0x0060,
            [unk1, PLACEHOLDER_OFFSET],
            offset_arguments={1: target},
            subroutine=subroutine,
        )
    else:
        return emit_command(0x0060, [unk1, target], subroutine=subroutine)


@command_emitter()
def set_animation(
    actor: int | SelfType | mnllib.Variable,
    animation: int | mnllib.Variable,
    *,
    unk3: int | mnllib.Variable = 0x01,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(
        0x0096,
        [actor if actor is not Self else -1, animation, unk3],
        subroutine=subroutine,
    )


@command_emitter()
def show_save_dialog(
    fade_in: bool | int | mnllib.Variable = True,
    *,
    unk1: int | mnllib.Variable = 0x00,
    unk2: int | mnllib.Variable = 0x01,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    return emit_command(
        0x0199,
        [unk1, unk2, int(fade_in) if isinstance(fade_in, bool) else fade_in],
        subroutine=subroutine,
    )


@command_emitter()
def swap_screens(*, subroutine: mnllib.Subroutine | None = None) -> mnllib.CodeCommand:
    return emit_command(0x01AE, subroutine=subroutine)


@command_emitter()
def show_textbox(
    actor_or_position: (
        int | mnllib.Variable | tuple[int | mnllib.Variable, int | mnllib.Variable]
    ),
    sound: int | mnllib.Variable,
    message: (
        TextEntryDefinition
        | dict[LanguageName, TextEntryDefinition]
        | int
        | mnllib.Variable
    ),
    bubble: int | mnllib.Variable = BubbleType.NORMAL,
    tail: int | mnllib.Variable = TailType.NORMAL,
    wait: bool | int | mnllib.Variable = True,
    color: int | mnllib.Variable = TextboxColor.NORMAL,
    width: int | mnllib.Variable | None = None,
    height: int | mnllib.Variable | None = None,
    tail_size: int | mnllib.Variable = -0x01,
    tail_direction: int | mnllib.Variable | None = None,
    textbox_hoffset: int | None = None,
    tail_hoffset: int | None = None,
    *,
    hoffsets_arg: int | mnllib.Variable | None = None,
    res: mnllib.Variable = mnllib.Variable(0x1000),
    unk9: int | mnllib.Variable = 0x01,
    unk14: int | mnllib.Variable = 0x0000,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    if (
        textbox_hoffset is not None or tail_hoffset is not None
    ) and hoffsets_arg is not None:
        raise ValueError(
            "at most one of textbox_hoffset/tail_hoffset and hoffsets_arg may be "
            "provided to say()"
        )

    if isinstance(message, (TextEntryDefinition, dict)):
        message_id: int | mnllib.Variable | None = emit_text_entry(message)
    else:
        message_id = message

    args = [
        width if width is not None else 0,
        height if height is not None else 0,
        bubble,
        tail,
        tail_size,
        tail_direction if tail_direction is not None else -1,
        (
            hoffsets_arg
            if hoffsets_arg is not None
            else (
                ((textbox_hoffset if textbox_hoffset is not None else -1) << 8)
                | (tail_hoffset if tail_hoffset is not None else -1)
            )
        ),
        unk9,
        int(not wait) if isinstance(wait, bool) else wait,
        sound,
        message_id,
    ]

    if isinstance(actor_or_position, (tuple, list)):
        return emit_command(
            0x01B9,
            [actor_or_position[0], actor_or_position[1], *args, unk14, color],
            res,
            subroutine=subroutine,
        )
    else:
        return emit_command(
            0x01BA,
            [actor_or_position, *args, color],
            res,
            subroutine=subroutine,
        )


@command_emitter()
def wait_for_textbox(
    *, unk1: int | mnllib.Variable = 0x00, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x01BD, [unk1], subroutine=subroutine)


@command_emitter()
def say(
    actor_or_position: (
        int | mnllib.Variable | tuple[int | mnllib.Variable, int | mnllib.Variable]
    ),
    sound: int | mnllib.Variable,
    message: (
        TextEntryDefinition
        | dict[LanguageName, TextEntryDefinition]
        | int
        | mnllib.Variable
    ),
    anim: int | mnllib.Variable | None = 0x01,
    post_anim: int | mnllib.Variable | None = 0x03,
    bubble: int | mnllib.Variable = BubbleType.NORMAL,
    tail: int | mnllib.Variable = TailType.NORMAL,
    wait: bool | int | mnllib.Variable = True,
    color: int | mnllib.Variable = TextboxColor.NORMAL,
    width: int | mnllib.Variable | None = None,
    height: int | mnllib.Variable | None = None,
    tail_size: int | mnllib.Variable = -0x01,
    tail_direction: int | mnllib.Variable | None = None,
    textbox_hoffset: int | None = None,
    tail_hoffset: int | None = None,
    *,
    hoffsets_arg: int | mnllib.Variable | None = None,
    force_wait_command: bool | None = None,
    res: mnllib.Variable = mnllib.Variable(0x1000),
    unk9: int | mnllib.Variable = 0x01,
    unk14: int | mnllib.Variable = 0x0000,
    subroutine: mnllib.Subroutine | None = None,
) -> mnllib.CodeCommand:
    is_actor = not isinstance(actor_or_position, (tuple, list))

    if is_actor and anim is not None:
        set_animation(
            typing.cast(
                int | mnllib.Variable, actor_or_position
            ),  # pyright: ignore [reportUnnecessaryCast]
            anim,
            subroutine=subroutine,
        )

    show_textbox_cmd = show_textbox(
        actor_or_position=actor_or_position,
        sound=sound,
        message=message,
        bubble=bubble,
        tail=tail,
        wait=wait,
        color=color,
        width=width,
        height=height,
        tail_size=tail_size,
        tail_direction=tail_direction,
        textbox_hoffset=textbox_hoffset,
        tail_hoffset=tail_hoffset,
        hoffsets_arg=hoffsets_arg,
        res=res,
        unk9=unk9,
        unk14=unk14,
        subroutine=subroutine,
    )

    if (
        (wait is True or (type(wait) is int and wait == 0))
        if force_wait_command is None
        else force_wait_command
    ):
        wait_for_textbox(subroutine=subroutine)
    if is_actor and post_anim is not None:
        set_animation(
            typing.cast(
                int | mnllib.Variable, actor_or_position
            ),  # pyright: ignore [reportUnnecessaryCast]
            post_anim,
            subroutine=subroutine,
        )

    return show_textbox_cmd
