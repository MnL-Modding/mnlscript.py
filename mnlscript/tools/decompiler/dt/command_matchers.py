import ctypes
import typing

import mnllib
import mnllib.dt
import pymsbmnl

from ....consts import (
    COMPARISON_OPERATORS,
    Screen,
    StackPopCondition,
    StackTopModification,
)
from ....dt.consts import (
    ActorAttribute,
    Actors,
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
from ....dt.misc import encode_rgba_or_neg1
from ....utils import fhex, fhex_byte, fhex_int, fhex_short
from ..misc import (
    decompile_const_or_f32_or_variable,
    decompile_const_or_variable,
    decompile_enum,
    decompile_float32,
    decompile_int_bool,
    decompile_variable,
    fhex_or,
)
from ..command_matchers import (
    CommandMatchContext,
    ScriptContext,
    CommandMatcher,
    create_command_matcher_decorator,
    decompile_offset,
    merge_decompiled_match,
    unknown_command_matcher,
)
from .globals import DecompilerGlobals
from .misc import decompile_sound, decompile_text_entry, decompile_textbox_sounds


class DTScriptContext(ScriptContext):
    script: mnllib.dt.FEventScript
    text_chunks: dict[str, pymsbmnl.LMSDocument]

    def __init__(
        self,
        manager: mnllib.MnLScriptManager,
        script_index: int,
        subroutine_offsets: list[tuple[int, int]],
        debug_message_offsets: list[int],
        subroutine: mnllib.Subroutine,
        script: mnllib.dt.FEventScript,
        text_chunks: dict[str, pymsbmnl.LMSDocument],
    ) -> None:
        super().__init__(
            manager, script_index, subroutine_offsets, debug_message_offsets, subroutine
        )

        self.script = script
        self.text_chunks = text_chunks


DTCommandMatchContext = CommandMatchContext[DTScriptContext]


ARITHMETIC_OPERATORS = ["+", "-", "*", "/", "%", "<<", ">>", "&", "|", "^"]


command_matchers: list[CommandMatcher[DTScriptContext]] = []
command_matcher = create_command_matcher_decorator(command_matchers)


@command_matcher("0000,")
def terminate_script(
    _matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return "terminate_script()"


@command_matcher("0001,")
def return_(
    _matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return "return_()"


@command_matcher("0002,", offset_params=[(0, 4)])
def branch_if(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"branch_if({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex)
    }, {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: (
                repr(COMPARISON_OPERATORS[value])
                if value in COMPARISON_OPERATORS
                else fhex(value, 2)
            ),
        )
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2], fhex)
    }, {
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[4], fhex_int
        )
    }{f", invert={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[3],
            lambda x: decompile_int_bool(x, invert=True),
        )
    }" if matched_commands[0].arguments[3] != 0x01 else ""})"


@command_matcher("0003,", offset_params=[(0, 1)])
def branch(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{"branch" if matched_commands[0].arguments[0] != 0x01 else "call"}({
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[1], fhex_int
        )
    }{f", type={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    }" if matched_commands[0].arguments[0] not in [0x01, 0x02] else ""})"


@command_matcher("0004,")
def wait(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"wait({decompile_const_or_variable(matched_commands[0].arguments[0])})"


@command_matcher("0005,")
def push(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"push({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex)
    })"


@command_matcher("0006,")
def pop(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"pop({decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable))
    })"


@command_matcher("0007,", offset_params=[(0, 3)])
def branch_if_stack(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    additional_operations_arg = matched_commands[0].arguments[0]
    if (
        isinstance(additional_operations_arg, int)
        and additional_operations_arg | 0x00FF == 0x00FF
    ):
        modification = additional_operations_arg & 0x000F
        pop = additional_operations_arg >> 4
        additional_operations_str = f"{f", {
            decompile_enum(StackTopModification, modification)
        }" if modification != StackTopModification.NONE
            or pop != StackPopCondition.NEVER
            else ""
        }{f", {
            decompile_enum(StackPopCondition, pop)
        }" if pop != StackPopCondition.NEVER else ""}"
    else:
        additional_operations_str = f"additional_operations_arg={
            decompile_const_or_f32_or_variable(additional_operations_arg, fhex_short)
        }"

    return f"branch_if_stack({
        decompile_const_or_variable(
            matched_commands[0].arguments[1],
            lambda value: (
                repr(COMPARISON_OPERATORS[round(value)])
                if round(value) in COMPARISON_OPERATORS
                else fhex_or(value, decompile_float32, width=8)
            ),
        )
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2], fhex)
    }, {
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[3], fhex_int
        )
    }{additional_operations_str})"


@command_matcher("000[CD]", offset_params=[(0, 0)])
def load_data(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"load_data{
        "_from_array" if matched_commands[0].command_id == 0x000C else ""
    }({
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[0], fhex_int
        )
    }{f", {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_short)
    }" if matched_commands[0].command_id == 0x000C else ""}, res={
        decompile_variable(
            typing.cast(mnllib.Variable, matched_commands[0].result_variable)
        )
    })"


@command_matcher("000E,")
def set_variable(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    if matched_commands[0].arguments[0] == matched_commands[0].result_variable:
        return unknown_command_matcher(matched_commands, context)

    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable))
    } = {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex)
    }"


@command_matcher("(?:000F|001[0-8]),")
def arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )} = {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    } {ARITHMETIC_OPERATORS[matched_commands[0].command_id - 0x000F]} {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1], fhex
        )
    }"


@command_matcher("(?:001[E-F]|002[0-7]),")
def in_place_arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    operator = ARITHMETIC_OPERATORS[matched_commands[0].command_id - 0x001E]

    if operator in ["+", "-"] and matched_commands[0].arguments[0] in [1.0, -1.0]:
        return f"{"add" if operator == "+" else "subtract"}_in_place({
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[0], fhex
            )
        }, {decompile_variable(
            typing.cast(mnllib.Variable, matched_commands[0].result_variable)
        )})"

    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )} {operator}= {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    }"


@command_matcher("001[9B],")
def unary_arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )} = {
        {0x0019: "-", 0x001B: "~"}
        [matched_commands[0].command_id]
    }{
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    }"


@command_matcher("001[CD],")
def incrementing_arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )} {"+" if matched_commands[0].command_id == 0x001C else "-"}= 1"


@command_matcher("001A,")
def arithmetic_1_param_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{
        {
            0x001A: "to_boolean",
        }[matched_commands[0].command_id]
    }({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    }, {decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )})"


@command_matcher("003[9A],", offset_params=[(0, 0)])
def debug(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    decompiled_offset: str | None = None
    if isinstance(matched_commands[0].arguments[0], int):
        relative_offset = (
            context.match_offset
            + sum(
                command.serialized_len(context.script.manager, -1)
                for command in matched_commands
            )
            + matched_commands[0].arguments[0]
            - context.script.subroutine_offsets[-1][1]
        )
        try:
            decompiled_offset = repr(
                context.script.script.debug_messages[
                    context.script.debug_message_offsets.index(relative_offset)
                ]
            )
        except ValueError:
            pass

    if decompiled_offset is None:
        decompiled_offset = decompile_offset(
            matched_commands,
            context,
            matched_commands[0].arguments[0],
            fhex_int,
            force_tuple=True,
        )
    return f"debug{"ln" if matched_commands[0].command_id == 0x0039 else ""}({
        decompiled_offset
    })"


@command_matcher("003[BCD],")
def debug_number(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{
        {
            0x003B: "debug_float",
            0x003C: "debug_bin",
            0x003D: "debug_hex",
        }[matched_commands[0].command_id]
    }({decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_int)})"


@command_matcher("004[1-3],", offset_params=[(0, 2)])
def thread_branch(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{
        {
            0x0041: "start_thread_here_and_branch",
            0x0042: "unk_thread_branch_0x0042",
            0x0043: "branch_in_thread",
        }[matched_commands[0].command_id]
    }({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    }, {
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[2], fhex_int
        )
    }{f", unk2={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_byte)
    }" if matched_commands[0].arguments[1] != 0x00 else ""})"


@command_matcher("0044,")
def join_thread(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"join_thread({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    })"


@command_matcher("0057,", offset_params=[(0, 1)])
def execute_on_bottom_screen(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"execute_on_bottom_screen({
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[1], fhex_int
        )
    }, unk1={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    })"


@command_matcher("005A,")
def set_blocked_buttons(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    result_variable = typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    return f"set_blocked_buttons({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: decompile_enum(Screen, value, fhex_byte),
        )
    }, {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[2],
            lambda value: decompile_enum(ButtonFlags, value),
        )
    }{f", unk2={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_byte)
    }" if matched_commands[0].arguments[1] != 0x00 else ""}{f", res={
        decompile_variable(result_variable)
    }" if result_variable.number != 0x1000 else ""})"


@command_matcher("005D,")
def set_movement_multipliers(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_movement_multipliers({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: decompile_enum(Screen, value, fhex_byte),
        )
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2])
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[3])
    }{f", unk2={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_byte)
    }" if matched_commands[0].arguments[1] != 0x00 else ""})"


@command_matcher("005F,")
def set_touches_blocked(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_touches_blocked({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], decompile_int_bool
        )
    })"


@command_matcher("0068,")
def start_battle(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"start_battle({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_int)
    }, {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1],
            lambda value: decompile_enum(WorldType, value, fhex_byte),
        )
    }{f", transition={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[6],
            lambda value: decompile_enum(Transition, value, fhex_byte),
        )
    }" if matched_commands[0].arguments[6] != Transition.NORMAL else ""
    }{f", first_strike={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[5],
            lambda value: decompile_enum(FirstStrike, value, fhex_byte),
        )
    }" if matched_commands[0].arguments[5] != FirstStrike.NONE else ""}{f", music={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[7], decompile_sound
        )
    }" if matched_commands[0].arguments[7] != 0x00000000 else ""}{f", unk3={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2], fhex_short)
    }" if matched_commands[0].arguments[2] != 0x0000 else ""}, unk4={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[3], fhex_byte)
    }{f", unk5={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[4], fhex_byte)
    }" if matched_commands[0].arguments[4] != 0x00 else ""})"


@command_matcher("0075,(?:0076,)?")
def tint_screen(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    decompiled_commands: dict[int, str] = {}
    wait = False
    if len(matched_commands) >= 2:
        wait_offset = context.match_offset + matched_commands[0].serialized_len(
            context.script.manager, -1
        )
        if wait_offset in context.split_hints:
            merge_decompiled_match(
                decompiled_commands,
                wait_offset,
                wait_for_screen_tint(
                    matched_commands[1:2],
                    DTCommandMatchContext(
                        context,
                        match_start_index=context.match_start_index + 1,
                        match_offset=wait_offset,
                    ),
                ),
            )
        else:
            wait = True

    initial = matched_commands[0].arguments[0:4]
    if all(x == -0x0001 for x in initial):
        initial_str = None
    elif all(isinstance(x, int) and -0x0001 <= x <= 0x00FF for x in initial):
        initial_str = repr(
            encode_rgba_or_neg1(typing.cast(tuple[int, int, int, int], tuple(initial)))
        )
    else:
        initial_str = f"({
            ", ".join([
                decompile_const_or_f32_or_variable(x, fhex_short)
                for x in initial
            ]),
        })"

    tint = matched_commands[0].arguments[4:8]
    if all(isinstance(x, int) and -0x0001 <= x <= 0x00FF for x in tint):
        tint_str = repr(
            encode_rgba_or_neg1(typing.cast(tuple[int, int, int, int], tuple(tint)))
        )
    else:
        tint_str = f"({
            ", ".join([
                decompile_const_or_f32_or_variable(x, fhex_short)
                for x in tint
            ]),
        })"

    decompiled_commands[context.match_offset] = (
        f"tint_screen({tint_str}{
            f", initial={initial_str}" if initial_str is not None else ""
        }, transition_duration={
            decompile_const_or_f32_or_variable(matched_commands[0].arguments[8])
        }{", wait=False" if not wait else ""})"
    )
    return decompiled_commands


@command_matcher("0076,")
def wait_for_screen_tint(
    _matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return "wait_for_screen_tint()"


@command_matcher("0079,")
def get_actor_attribute(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"get_actor_attribute({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: decompile_enum(Actors, value, fhex_byte),
        )
    }, {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1],
            lambda value: decompile_enum(ActorAttribute, value, fhex_byte),
        )
    }, res={decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )})"


@command_matcher("007A,")
def set_actor_attribute(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_actor_attribute({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: decompile_enum(Actors, value, fhex_byte),
        )
    }, {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1],
            lambda value: decompile_enum(ActorAttribute, value, fhex_byte),
        )
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2], fhex_int)
    })"


@command_matcher("(?:0087,)?014C,(?:0150,)?(?:014D,)?(?:0087,)?")
def say(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    decompiled_commands: dict[int, str] = {}
    decompiled_post_commands: dict[int, str] = {}

    say_offset = context.match_offset
    current_match_index = context.match_start_index
    current_offset = context.match_offset

    anim: int | mnllib.Variable | None = None
    if matched_commands[0].command_id == 0x0087:
        post_offset = current_offset + matched_commands[0].serialized_len(
            context.script.manager, -1
        )
        if (
            post_offset in context.split_hints
            or matched_commands[1].arguments[2] == -1
            or matched_commands[0].arguments[0] != matched_commands[1].arguments[2]
            or matched_commands[0].arguments[2] != 0x01
        ):
            merge_decompiled_match(
                decompiled_commands,
                current_offset,
                set_animation(matched_commands[:1], context),
            )
            say_offset = post_offset
        else:
            anim = typing.cast(int | mnllib.Variable, matched_commands[0].arguments[1])
        current_match_index += 1
        current_offset = post_offset
        del matched_commands[0]

    current_post_match_index = current_match_index + 1
    current_post_offset = current_offset + matched_commands[0].serialized_len(
        context.script.manager, -1
    )
    actor = matched_commands[0].arguments[2]
    textbox_id = typing.cast(mnllib.Variable, matched_commands[0].result_variable)

    sound_normal: int | mnllib.Variable | None = None
    sound_fast_forwarded: int | mnllib.Variable | None = None
    if len(matched_commands) >= 2 and matched_commands[1].command_id == 0x0150:
        if (
            current_post_offset in context.split_hints
            or matched_commands[1].arguments[0] != textbox_id
        ):
            merge_decompiled_match(
                decompiled_post_commands,
                current_post_offset,
                set_textbox_sounds(
                    matched_commands[1:2],
                    DTCommandMatchContext(
                        context,
                        match_start_index=current_post_match_index,
                        match_offset=current_post_offset,
                    ),
                ),
            )
        else:
            sound_normal = typing.cast(
                int | mnllib.Variable, matched_commands[1].arguments[1]
            )
            sound_fast_forwarded = typing.cast(
                int | mnllib.Variable, matched_commands[1].arguments[2]
            )
        current_post_match_index += 1
        current_post_offset += matched_commands[1].serialized_len(
            context.script.manager, -1
        )
        del matched_commands[1]

    wait = False
    if len(matched_commands) >= 2 and matched_commands[1].command_id == 0x014D:
        if (
            len(decompiled_post_commands) > 0
            or current_post_offset in context.split_hints
            or matched_commands[1].arguments[0] != textbox_id
        ):
            merge_decompiled_match(
                decompiled_post_commands,
                current_post_offset,
                wait_for_textbox(
                    matched_commands[1:2],
                    DTCommandMatchContext(
                        context,
                        match_start_index=current_post_match_index,
                        match_offset=current_post_offset,
                    ),
                ),
            )
        else:
            wait = True
        current_post_match_index += 1
        current_post_offset += matched_commands[1].serialized_len(
            context.script.manager, -1
        )
        del matched_commands[1]

    post_anim: int | mnllib.Variable | None = None
    if len(matched_commands) >= 2 and matched_commands[1].command_id == 0x0087:
        if (
            len(decompiled_post_commands) > 0
            or current_post_offset in context.split_hints
            or actor == -1
            or matched_commands[1].arguments[0] != actor
            or matched_commands[1].arguments[2] != 0x01
        ):
            merge_decompiled_match(
                decompiled_post_commands,
                current_post_offset,
                set_animation(
                    matched_commands[1:2],
                    DTCommandMatchContext(
                        context,
                        match_start_index=current_post_match_index,
                        match_offset=current_post_offset,
                    ),
                ),
            )
        else:
            post_anim = typing.cast(
                int | mnllib.Variable, matched_commands[1].arguments[1]
            )
        current_post_match_index += 1
        current_post_offset += matched_commands[1].serialized_len(
            context.script.manager, -1
        )
        del matched_commands[1]

    text_entry_index = matched_commands[0].arguments[1]
    room_id = context.script.script_index // 2
    if (
        isinstance(text_entry_index, int)
        and ctypes.c_ubyte(text_entry_index).value
        == DecompilerGlobals.next_text_entry_index[room_id]
    ):
        message = decompile_text_entry(context.script.text_chunks, text_entry_index)
        DecompilerGlobals.next_text_entry_index[room_id] += 1
    else:
        message = decompile_const_or_f32_or_variable(
            text_entry_index, lambda value: fhex(ctypes.c_ubyte(value).value, 2)
        )
    arguments: list[str] = [
        # actor
        (
            decompile_const_or_f32_or_variable(
                actor, lambda value: decompile_enum(Actors, value, fhex_byte)
            )
            if actor != -1
            else "None"
        ),
        # sounds
        (
            decompile_textbox_sounds(sound_normal, sound_fast_forwarded)
            if sound_normal is not None and sound_fast_forwarded is not None
            else "None"
        ),
        # message
        message,
    ]
    if matched_commands[0].arguments[3:6] != [0.0, 0.0, 0.0]:
        arguments.append(
            f"offset=({", ".join([
                decompile_const_or_f32_or_variable(x, fhex_int)
                for x in matched_commands[0].arguments[3:6]
            ])})"
        )
    if actor != -1 and anim != 0x01:
        arguments.append(
            f"anim={decompile_const_or_f32_or_variable(
                anim, fhex_byte
            ) if anim is not None else "None"}"
        )
    if actor != -1 and post_anim != 0x03:
        arguments.append(
            f"post_anim={decompile_const_or_f32_or_variable(
                post_anim, fhex_byte
            ) if post_anim is not None else "None"}"
        )
    if not wait:
        arguments.append(f"wait={wait!r}")
    if matched_commands[0].arguments[9] != 4096.0:
        arguments.append(
            f"tail_hoffset={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[9], fhex_int
            )}"
        )
    if matched_commands[0].arguments[8] != TextboxFlags.REMOVE_WHEN_DISMISSED | 2:
        arguments.append(
            f"flags={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[8],
                lambda value: decompile_enum(TextboxFlags, value),
            )}"
        )
    properties_arg = matched_commands[0].arguments[10]
    if isinstance(properties_arg, int) and properties_arg | 0x0000007F == 0x0000007F:
        tail = properties_arg & 0x00000007
        alignment = properties_arg >> 3
        if tail != (TextboxTailType.LARGE if actor != -1 else TextboxTailType.NONE):
            arguments.append(f"tail={decompile_enum(TextboxTailType, tail)}")
        if alignment != TextboxAlignment.AUTOMATIC:
            arguments.append(f"alignment={decompile_enum(TextboxAlignment, alignment)}")
    else:
        arguments.append(
            f"properties_arg={decompile_const_or_f32_or_variable(
                properties_arg, fhex_int
            )}"
        )
    if matched_commands[0].arguments[0] != -0x01:
        arguments.append(
            f"unk1={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[0], fhex_byte
            )}"
        )
    if matched_commands[0].arguments[6] != 0x0000:
        arguments.append(
            f"unk7={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[6], fhex_short
            )}"
        )
    if matched_commands[0].arguments[7] != 0x0000:
        arguments.append(
            f"unk8={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[7], fhex_short
            )}"
        )
    if matched_commands[0].arguments[11] != 0:
        arguments.append(
            f"unk_sound={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[11],
                lambda value: decompile_sound(value, bank_shift=16),
            )}"
        )
    if textbox_id.number != 0x1000:
        arguments.append(f"res_textbox_id={decompile_variable(textbox_id)}")
    decompiled_commands[say_offset] = f"say({", ".join(arguments)})"

    return decompiled_commands | decompiled_post_commands


@command_matcher("0087,")
def set_animation(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_animation({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: decompile_enum(Actors, value, fhex_byte),
        )
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_byte)
    }{f", unk3={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2], fhex_byte)
    }" if matched_commands[0].arguments[2] != 0x01 else ""})"


@command_matcher("00E3,")
def set_action_icons_shown(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_action_icons_shown({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], decompile_int_bool
        )
    }{f", animated={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1], decompile_int_bool
        )
    }" if matched_commands[0].arguments[1] != 0x01 else ""})"


@command_matcher("010A,")
def set_camera_mode(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_camera_mode({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: decompile_enum(CameraMode, value, fhex_byte),
        )
    })"


@command_matcher("010C,(?:0110,)?")
def move_camera(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    decompiled_commands: dict[int, str] = {}
    wait = False
    if len(matched_commands) >= 2:
        wait_offset = context.match_offset + matched_commands[0].serialized_len(
            context.script.manager, -1
        )
        if wait_offset in context.split_hints:
            merge_decompiled_match(
                decompiled_commands,
                wait_offset,
                wait_for_camera(
                    matched_commands[1:2],
                    DTCommandMatchContext(
                        context,
                        match_start_index=context.match_start_index + 1,
                        match_offset=wait_offset,
                    ),
                ),
            )
        else:
            wait = True

    decompiled_commands[context.match_offset] = (
        f"move_camera(({", ".join([
            decompile_const_or_f32_or_variable(x, fhex_int)
            for x in matched_commands[0].arguments[1:4]
        ])}), unk5={decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[4], fhex_int
        )}, unk6={decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[5], fhex_int
        )}, unk7={decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[6], fhex_int
        )}, unk8={decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[7], fhex_int
        )}{f", relative={
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[0], decompile_int_bool
            )
        }" if matched_commands[0].arguments[0] != 0x00 else ""}{f", unk9={
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[8], decompile_int_bool
            )
        }" if matched_commands[0].arguments[8] != 0x01 else ""}{f", endless={
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[8],
                lambda x: decompile_int_bool(x, invert=True),
            )
        }" if matched_commands[0].arguments[9] != 0x01 else ""}{
            ", wait=False" if not wait else ""
        })"
    )
    return decompiled_commands


@command_matcher("0113,(?:0110,)?")
def rotate_camera(
    matched_commands: list[mnllib.CodeCommand],
    context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    decompiled_commands: dict[int, str] = {}
    wait = False
    if len(matched_commands) >= 2:
        wait_offset = context.match_offset + matched_commands[0].serialized_len(
            context.script.manager, -1
        )
        if wait_offset in context.split_hints:
            merge_decompiled_match(
                decompiled_commands,
                wait_offset,
                wait_for_camera(
                    matched_commands[1:2],
                    DTCommandMatchContext(
                        context,
                        match_start_index=context.match_start_index + 1,
                        match_offset=wait_offset,
                    ),
                ),
            )
        else:
            wait = True

    decompiled_commands[context.match_offset] = (
        f"rotate_camera(({", ".join([
            decompile_const_or_f32_or_variable(x, fhex_int)
            for x in matched_commands[0].arguments[2:5]
        ])}), speed=({", ".join([
            decompile_const_or_f32_or_variable(x)
            for x in matched_commands[0].arguments[5:8]
        ])}){f", relative={
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[0], decompile_int_bool
            )
        }" if matched_commands[0].arguments[0] != 0x00 else ""}, around_focus={
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[1], decompile_int_bool
            )
        }{f", endless={
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[8],
                lambda x: decompile_int_bool(x, invert=True),
            )
        }" if matched_commands[0].arguments[8] != 0x01 else ""}{
            ", wait=False" if not wait else ""
        })"
    )
    return decompiled_commands


@command_matcher("0110,")
def wait_for_camera(
    _matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return "wait_for_camera()"


@command_matcher("0138,")
def change_room(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"change_room({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_short)
    }, position=({", ".join([
        decompile_const_or_f32_or_variable(x)
        for x in matched_commands[0].arguments[1:4]
    ])}), init_sub={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[6], fhex)
    }{f", facing={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[4])
    }" if matched_commands[0].arguments[4] != 0x00 else ""}{f", step_forward={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[5], decompile_int_bool
        )
    }" if matched_commands[0].arguments[5] != 0x00 else ""}{f", music={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[7],
            lambda value: decompile_enum(MusicFlag, value, decompile_sound),
        )
    }" if matched_commands[0].arguments[7] != MusicFlag.RESTART_ONLY_IF_DIFFERENT
        else ""
    }{f", unk9={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[8], fhex_byte)
    }" if matched_commands[0].arguments[8] != 0x00 else ""})"


@command_matcher("013B,")
def set_bottom_screen_button_shown(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_bottom_screen_button_shown({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0],
            lambda value: decompile_enum(BottomScreenButton, value, fhex_byte),
        )
    }, {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1], decompile_int_bool
        )
    }{f", animated={
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[2], decompile_int_bool
        )
    }" if matched_commands[0].arguments[2] != 0x01 else ""})"


@command_matcher("014D,")
def wait_for_textbox(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"wait_for_textbox({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
        if matched_commands[0].arguments[0] != mnllib.Variable(0x1000) else ""
    })"


@command_matcher("0150,")
def set_textbox_sounds(
    matched_commands: list[mnllib.CodeCommand],
    _context: DTCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_textbox_sounds({
        decompile_textbox_sounds(
            matched_commands[0].arguments[1],
            matched_commands[0].arguments[2],
            force_parentheses=False,
        )
    }{f", textbox_id={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    }" if matched_commands[0].arguments[0] != mnllib.Variable(0x1000) else ""})"


command_matcher("....,")(unknown_command_matcher)
