import typing

import mnllib
import mnllib.bis

from ....bis.consts import BubbleType, Sound, TailType, TextboxColor
from ....consts import COMPARISON_OPERATORS, StackPopCondition, StackTopModification
from ....utils import fhex, fhex_byte, fhex_int, fhex_short
from ..command_matchers import (
    CommandMatchContext,
    ScriptContext,
    CommandMatcher,
    create_command_matcher_decorator,
    decompile_offset,
    merge_decompiled_match,
    unknown_command_matcher,
)
from ..misc import (
    decompile_const_or_f32_or_variable,
    decompile_const_or_variable,
    decompile_enum,
    decompile_int_bool,
    decompile_variable,
)
from .globals import DecompilerGlobals
from .misc import decompile_text_entry


class BISScriptContext(ScriptContext):
    chunk_triple: mnllib.bis.FEventChunkTriple
    script: mnllib.bis.FEventScript

    def __init__(
        self,
        manager: mnllib.MnLScriptManager,
        script_index: int,
        subroutine_offsets: list[tuple[int, int]],
        debug_message_offsets: list[int],
        subroutine: mnllib.Subroutine,
        chunk_triple: mnllib.bis.FEventChunkTriple,
    ) -> None:
        super().__init__(
            manager, script_index, subroutine_offsets, debug_message_offsets, subroutine
        )

        self.manager = manager
        self.chunk_triple = chunk_triple
        script = chunk_triple[script_index % 3]
        if not isinstance(script, mnllib.bis.FEventScript):
            raise TypeError(
                f"chunk {script_index % 3} of room {fhex(script_index // 3, 4)} is not "
                f"an mnllib.bis.FEventScript, but rather '{type(script).__name__}'"
            )
        self.script = script


BISCommandMatchContext = CommandMatchContext[BISScriptContext]


ARITHMETIC_OPERATORS = ["+", "-", "*", "//", "%", "<<", ">>", "&", "|", "^"]


command_matchers: list[CommandMatcher[BISScriptContext]] = []
command_matcher = create_command_matcher_decorator(command_matchers)


@command_matcher("0000,")
def terminate_script(
    _matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return "terminate_script()"


@command_matcher("0001,")
def return_(
    _matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return "return_()"


@command_matcher("0002,", offset_params=[(0, 4)])
def branch_if(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
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
            matched_commands, context, matched_commands[0].arguments[4], fhex_short
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
    context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{"branch" if matched_commands[0].arguments[0] != 0x01 else "call"}({
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[1], fhex_short
        )
    }{f", type={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    }" if matched_commands[0].arguments[0] not in [0x01, 0x02] else ""})"


@command_matcher("0004,")
def wait(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"wait({decompile_const_or_variable(matched_commands[0].arguments[0])})"


@command_matcher("0005,")
def push(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"push({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex)
    })"


@command_matcher("0006,")
def pop(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"pop({decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable))
    })"


@command_matcher("0007,", offset_params=[(0, 3)])
def branch_if_stack(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
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
            else ""}{f", {
                decompile_enum(StackPopCondition, pop)
            }" if pop != StackPopCondition.NEVER else ""}"
    else:
        additional_operations_str = f"additional_operations_arg={
            decompile_const_or_f32_or_variable(additional_operations_arg, fhex_short)
        }"

    return f"branch_if_stack({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1],
            lambda value: (
                repr(COMPARISON_OPERATORS[value])
                if value in COMPARISON_OPERATORS
                else fhex(value, 4)
            ),
        )
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2], fhex)
    }, {
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[3], fhex_short
        )
    }{additional_operations_str})"


@command_matcher("0008,")
def set_variable(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    if matched_commands[0].arguments[0] == matched_commands[0].result_variable:
        return unknown_command_matcher(matched_commands, context)

    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable))
    } = {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex)
    }"


@command_matcher("(?:000[9A-F]|001[0-2]),")
def arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )} = {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    } {ARITHMETIC_OPERATORS[matched_commands[0].command_id - 0x0009]} {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1], fhex
        )
    }"


@command_matcher("(?:001[8-9A-F]|002[01]),")
def in_place_arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    operator = ARITHMETIC_OPERATORS[matched_commands[0].command_id - 0x0018]

    if operator in ["+", "-"] and matched_commands[0].arguments[0] in [1, -1]:
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


@command_matcher("001[35],")
def unary_arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )} = {
        {0x0013: "-", 0x0015: "~"}
        [matched_commands[0].command_id]
    }{
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    }"


@command_matcher("001[67],")
def incrementing_arithmetic_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )} {"+" if matched_commands[0].command_id == 0x0016 else "-"}= 1"


@command_matcher("(?:0014|002[2-79A]|003[0-7]),")
def arithmetic_1_param_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{
        {
            0x0014: "to_boolean",
            0x0022: "sqrt",
            0x0023: "invsqrt",
            0x0024: "invert",
            0x0025: "sin",
            0x0026: "cos",
            0x0027: "atan",
            0x0032: "fx_sqrt",
            0x0033: "fx_invsqrt",
            0x0034: "fx_invert",
            0x0035: "fx_sin",
            0x0036: "fx_cos",
            0x0037: "fx_atan",
            0x0029: "random_below",
            0x002A: "fx_set_variable",
            0x0030: "fx_to_int",
            0x0031: "fx_trunc",
        }[matched_commands[0].command_id]
    }({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    }, {decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )})"


@command_matcher("(?:002[8B-F]|0038),")
def arithmetic_2_param_command(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{
        {
            0x0028: "atan2",
            0x002B: "fx_add",
            0x002C: "fx_subtract",
            0x002D: "fx_multiply",
            0x002E: "fx_divide",
            0x002F: "fx_modulo",
            0x0038: "fx_atan2",
        }[matched_commands[0].command_id]
    }({
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[0], fhex
        )
    }, {
        decompile_const_or_f32_or_variable(
            matched_commands[0].arguments[1], fhex
        )
    }, {decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    )})"


@command_matcher("003[9A]", offset_params=[(0, 0)])
def load_data(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"load_data{
        "_from_array" if matched_commands[0].command_id == 0x0039 else ""
    }({
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[0], fhex_short
        )
    }{f", {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_short)
    }" if matched_commands[0].command_id == 0x0039 else ""}, res={
        decompile_variable(
            typing.cast(mnllib.Variable, matched_commands[0].result_variable)
        )
    })"


@command_matcher("003[BC],", offset_params=[(0, 0)])
def debug(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
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
            fhex_short,
            force_tuple=True,
        )
    return f"debug{"ln" if matched_commands[0].command_id == 0x003B else ""}({
        decompiled_offset
    })"


@command_matcher("003[DEF],")
def debug_number(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{
        {
            0x003D: "debug_bin",
            0x003E: "debug_dec",
            0x003F: "debug_hex",
        }[matched_commands[0].command_id]
    }({decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_int)})"


@command_matcher("004[9AB],", offset_params=[(0, 2)])
def thread_branch(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"{
        {
            0x0049: "start_thread_here_and_branch",
            0x004A: "unk_thread_branch_0x004a",
            0x004B: "branch_in_thread",
        }[matched_commands[0].command_id]
    }({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    }, {
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[2], fhex_short
        )
    }{f", unk2={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_byte)
    }" if matched_commands[0].arguments[1] != 0x00 else ""})"


@command_matcher("004C,")
def join_thread(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"join_thread({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    })"


@command_matcher("0060,", offset_params=[(0, 1)])
def execute_on_secondary_screen(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"execute_on_secondary_screen({
        decompile_offset(
            matched_commands, context, matched_commands[0].arguments[1], fhex_short
        )
    }, unk1={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    })"


@command_matcher("(?:0096,)?01B[9A],(?:01BD,)?(?:0096,)?")
def say(
    matched_commands: list[mnllib.CodeCommand],
    context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    decompiled_commands: dict[int, str] = {}
    decompiled_post_commands: dict[int, str] = {}

    say_offset = context.match_offset
    current_match_index = context.match_start_index
    current_offset = context.match_offset

    anim: int | mnllib.Variable | None = None
    if matched_commands[0].command_id == 0x0096:
        post_offset = current_offset + matched_commands[0].serialized_len(
            context.script.manager, -1
        )
        if (
            post_offset in context.split_hints
            or matched_commands[1].command_id != 0x01BA
            or matched_commands[0].arguments[0] != matched_commands[1].arguments[0]
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

    wait_command_unk1: int | mnllib.Variable | None = None
    wait_split = False
    if len(matched_commands) >= 2 and matched_commands[1].command_id == 0x01BD:
        wait_command_unk1 = typing.cast(
            int | mnllib.Variable, matched_commands[1].arguments[0]
        )
        if current_post_offset in context.split_hints or wait_command_unk1 != 0x00:
            wait_split = True
            merge_decompiled_match(
                decompiled_post_commands,
                current_post_offset,
                wait_for_textbox(
                    matched_commands[1:2],
                    BISCommandMatchContext(
                        context,
                        match_start_index=current_match_index,
                        match_offset=current_post_offset,
                    ),
                ),
            )
        current_post_match_index += 1
        current_post_offset += matched_commands[1].serialized_len(
            context.script.manager, -1
        )
        del matched_commands[1]

    post_anim: int | mnllib.Variable | None = None
    if len(matched_commands) >= 2 and matched_commands[1].command_id == 0x0096:
        if (
            len(decompiled_post_commands) > 0
            or current_post_offset in context.split_hints
            or matched_commands[0].command_id != 0x01BA
            or matched_commands[1].arguments[0] != matched_commands[0].arguments[0]
            or matched_commands[1].arguments[2] != 0x01
        ):
            merge_decompiled_match(
                decompiled_post_commands,
                current_post_offset,
                set_animation(
                    matched_commands[1:2],
                    BISCommandMatchContext(
                        context,
                        match_start_index=current_post_offset,
                        match_offset=current_post_match_index,
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

    common_args = matched_commands[0].arguments[
        1 if matched_commands[0].command_id == 0x01BA else 2 : (
            -1 if matched_commands[0].command_id == 0x01BA else -2
        )
    ]
    text_entry_index = common_args[10]
    room_id = context.script.script_index // 3
    if text_entry_index == DecompilerGlobals.next_text_entry_index[room_id]:
        language_table = context.script.chunk_triple[2]
        if not isinstance(language_table, mnllib.bis.LanguageTable):
            raise TypeError(
                f"chunk 2 of room {fhex(room_id, 4)} is not "
                f"an mnllib.LanguageTable, but rather '{type(language_table).__name__}'"
            )
        message = decompile_text_entry(
            language_table, typing.cast(int, text_entry_index)
        )
        DecompilerGlobals.next_text_entry_index[room_id] += 1
    else:
        message = decompile_const_or_f32_or_variable(text_entry_index, fhex_byte)
    arguments: list[str] = [
        # actor_or_position
        (
            decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[0], fhex_byte
            )
            if matched_commands[0].command_id == 0x01BA
            else f"({decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[0]
            )}, {decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[1]
            )})"
        ),
        # sound
        decompile_const_or_f32_or_variable(
            common_args[9],
            lambda value: decompile_enum(Sound, value, fhex_short),
        ),
        # message
        message,
    ]
    if matched_commands[0].command_id == 0x01BA and anim != 0x01:
        arguments.append(
            f"anim={decompile_const_or_f32_or_variable(
                anim, fhex_byte
            ) if anim is not None else "None"}"
        )
    if matched_commands[0].command_id == 0x01BA and post_anim != 0x03:
        arguments.append(
            f"post_anim={decompile_const_or_f32_or_variable(
                post_anim, fhex_byte
            ) if post_anim is not None else "None"}"
        )
    if common_args[2] != BubbleType.NORMAL:
        arguments.append(
            f"bubble={decompile_const_or_f32_or_variable(
                common_args[2],
                lambda value: decompile_enum(BubbleType, value, fhex_byte)
            )}"
        )
    if common_args[3] != TailType.NORMAL:
        arguments.append(
            f"tail={decompile_const_or_f32_or_variable(
                common_args[3],
                lambda value: decompile_enum(TailType, value, fhex_byte)
            )}"
        )
    if common_args[8] != 0:
        arguments.append(
            f"wait={
                "False" if common_args[8] == 1
                else decompile_const_or_f32_or_variable(common_args[8], fhex_byte)
            }"
        )
    if matched_commands[0].arguments[-1] != TextboxColor.NORMAL:
        arguments.append(
            f"color={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[-1],
                lambda value: decompile_enum(TextboxColor, value, fhex_byte)
            )}"
        )
    if common_args[0] != 0:
        arguments.append(f"width={decompile_const_or_variable(common_args[0])}")
    if common_args[1] != 0:
        arguments.append(f"height={decompile_const_or_variable(common_args[1])}")
    if common_args[4] != -1:
        arguments.append(
            f"tail_size={
                decompile_const_or_f32_or_variable(common_args[4], fhex_byte)
            }"
        )
    if common_args[5] != -1:
        arguments.append(
            f"tail_direction={
                decompile_const_or_f32_or_variable(common_args[5], fhex_byte)
            }"
        )
    if isinstance(common_args[6], int):
        tail_hoffset = common_args[6] & 0x00FF
        textbox_hoffset = common_args[6] >> 8
        if textbox_hoffset != -1:
            arguments.append(f"textbox_hoffset={fhex(textbox_hoffset, 2)}")
        if tail_hoffset != -1:
            arguments.append(f"tail_hoffset={fhex(tail_hoffset, 2)}")
    else:
        arguments.append(
            f"hoffsets_arg={
                decompile_const_or_f32_or_variable(common_args[6], fhex_short)
            }"
        )
    if common_args[8] != 0 and wait_command_unk1 == 0x00 and not wait_split:
        arguments.append("force_wait_command=True")
    if (common_args[8] == 0 and wait_command_unk1 != 0x00) or wait_split:
        arguments.append("force_wait_command=False")
    result_variable = typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    if result_variable.number != 0x1000:
        arguments.append(f"res={decompile_variable(result_variable)}")
    if common_args[7] != 0x01:
        arguments.append(
            f"unk9={decompile_const_or_f32_or_variable(common_args[7], fhex_byte)}"
        )
    if (
        matched_commands[0].command_id == 0x01B9
        and matched_commands[0].arguments[13] != 0x0000
    ):
        arguments.append(
            f"unk14={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[13], fhex_short
            )}"
        )
    decompiled_commands[say_offset] = f"say({", ".join(arguments)})"

    return decompiled_commands | decompiled_post_commands


@command_matcher("0096,")
def set_animation(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"set_animation({
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
        if matched_commands[0].arguments[0] != -1 else "Self"
    }, {
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[1], fhex_byte)
    }{f", unk3={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[2], fhex_byte)
    }" if matched_commands[0].arguments[2] != 0x01 else ""})"


@command_matcher("0199,")
def show_save_dialog(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    args: list[str] = []
    if matched_commands[0].arguments[2] != 1:
        args.append(
            f"fade_in={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[2], decompile_int_bool
            )}"
        )
    if matched_commands[0].arguments[0] != 0x00:
        args.append(
            f"unk1={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[0], fhex_byte,
            )}"
        )
    if matched_commands[0].arguments[1] != 0x01:
        args.append(
            f"unk2={decompile_const_or_f32_or_variable(
                matched_commands[0].arguments[1], fhex_byte,
            )}"
        )
    return f"show_save_dialog({", ".join(args)})"


@command_matcher("01AE,")
def swap_screens(
    _matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return "swap_screens()"


@command_matcher("01BD,")
def wait_for_textbox(
    matched_commands: list[mnllib.CodeCommand],
    _context: BISCommandMatchContext,
) -> str | dict[int, str] | None:
    return f"wait_for_textbox({f"unk1={
        decompile_const_or_f32_or_variable(matched_commands[0].arguments[0], fhex_byte)
    }" if matched_commands[0].arguments[0] != 0x00 else ""})"


command_matcher("....,")(unknown_command_matcher)
