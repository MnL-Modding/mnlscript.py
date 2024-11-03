import math
import io
import struct
import re
import textwrap
import typing

import mnllib

from ...consts import BubbleType, Sound, TailType, TextboxColor
from ...utils import fhex, fhex_byte, fhex_int, fhex_short
from .globals import DecompilerGlobals
from .misc import (
    decompile_bool_int_or_variable,
    decompile_const_or_variable,
    decompile_enum,
    decompile_text_entry,
    decompile_variable,
)


class CommandMatchContext:
    manager: mnllib.MnLScriptManager
    chunk_triple: tuple[
        mnllib.FEventScript | None, mnllib.FEventChunk | None, mnllib.FEventChunk | None
    ]
    script: mnllib.FEventScript
    script_index: int
    subroutine: mnllib.Subroutine

    def __init__(
        self,
        manager: mnllib.MnLScriptManager,
        chunk_triple: tuple[
            mnllib.FEventScript | None,
            mnllib.FEventChunk | None,
            mnllib.FEventChunk | None,
        ],
        script_index: int,
        subroutine: mnllib.Subroutine,
    ) -> None:
        self.manager = manager
        self.chunk_triple = chunk_triple
        script = chunk_triple[script_index % 3]
        if not isinstance(script, mnllib.FEventScript):
            raise TypeError(
                f"chunk {script_index % 3} of room {fhex(script_index // 3, 4)} is not "
                f"an mnllib.FEventScript, but rather '{type(script).__name__}'"
            )
        self.script = script
        self.script_index = script_index
        self.subroutine = subroutine


CommandMatchHandler: typing.TypeAlias = typing.Callable[
    [list[mnllib.Command], CommandMatchContext, int], str | None
]


class CommandMatcher:
    pattern: re.Pattern[str]
    handler: CommandMatchHandler

    def __init__(self, pattern: re.Pattern[str], handler: CommandMatchHandler) -> None:
        self.pattern = pattern
        self.handler = handler


command_matchers: list[CommandMatcher] = []


def command_matcher(
    pattern: str | re.Pattern[str],
) -> typing.Callable[[CommandMatchHandler], CommandMatchHandler]:
    if not isinstance(pattern, re.Pattern):
        pattern = re.compile(rf"\b{pattern}(?:\b|$)", re.IGNORECASE)

    def decorator(handler: CommandMatchHandler) -> CommandMatchHandler:
        command_matchers.append(CommandMatcher(pattern, handler))
        return handler

    return decorator


@command_matcher("0000,")
def terminate_script(
    _matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return "terminate_script()"


@command_matcher("0001,")
def return_(
    _matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return "return_()"


@command_matcher("0004,")
def wait(
    matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return f"wait({decompile_const_or_variable(matched_commands[0].arguments[0])})"


@command_matcher("0005,")
def push(
    matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return f"push({decompile_const_or_variable(matched_commands[0].arguments[0])})"


@command_matcher("0006,")
def pop(
    matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return f"pop({decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable))
    })"


@command_matcher("0008,")
def set_variable(
    matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return f"{decompile_variable(
        typing.cast(mnllib.Variable, matched_commands[0].result_variable))
    } = {
        decompile_const_or_variable(matched_commands[0].arguments[0], fhex)
    }"


for i, operator in enumerate(["+", "-", "*", "//", "%", "<<", ">>", "&", "|", "^"]):

    def factory(i: int, operator: str, /) -> None:
        @command_matcher(f"{0x0009 + i:04X},")
        def arithmetic_command(  # pyright: ignore[reportUnusedFunction]
            matched_commands: list[mnllib.Command],
            _context: CommandMatchContext,
            _match_start_index: int,
        ) -> str | None:
            return f"{decompile_variable(
                typing.cast(mnllib.Variable, matched_commands[0].result_variable)
            )} = {
                decompile_const_or_variable(matched_commands[0].arguments[0], fhex)
            } {operator} {
                decompile_const_or_variable(matched_commands[0].arguments[1], fhex)
            }"

        @command_matcher(f"{0x0018 + i:04X},")
        def in_place_arithmetic_command(  # pyright: ignore[reportUnusedFunction]
            matched_commands: list[mnllib.Command],
            _context: CommandMatchContext,
            _match_start_index: int,
        ) -> str | None:
            if operator in ["+", "-"] and matched_commands[0].arguments[0] in [1, -1]:
                return f"{"add" if operator == "+" else "subtract"}_in_place({
                    decompile_const_or_variable(matched_commands[0].arguments[0], fhex)
                }, {decompile_variable(
                    typing.cast(mnllib.Variable, matched_commands[0].result_variable)
                )})"

            return f"{decompile_variable(
                typing.cast(mnllib.Variable, matched_commands[0].result_variable)
            )} {operator}= {
                decompile_const_or_variable(matched_commands[0].arguments[0], fhex)
            }"

    factory(i, operator)

for command_id, operator in {0x0013: "-", 0x0015: "~"}.items():

    def factory(command_id: int, operator: str, /) -> None:
        @command_matcher(f"{command_id:04X},")
        def unary_arithmetic_command(  # pyright: ignore[reportUnusedFunction]
            matched_commands: list[mnllib.Command],
            _context: CommandMatchContext,
            _match_start_index: int,
        ) -> str | None:
            return f"{decompile_variable(
                typing.cast(mnllib.Variable, matched_commands[0].result_variable)
            )} = {operator}{
                decompile_const_or_variable(matched_commands[0].arguments[0], fhex)
            }"

    factory(command_id, operator)

for i, operator in enumerate(["+", "-"]):

    def factory(i: int, operator: str, /) -> None:
        @command_matcher(f"{0x0016 + i:04X},")
        def incrementing_arithmetic_command(  # pyright: ignore[reportUnusedFunction]
            matched_commands: list[mnllib.Command],
            _context: CommandMatchContext,
            _match_start_index: int,
        ) -> str | None:
            return f"{decompile_variable(
                typing.cast(mnllib.Variable, matched_commands[0].result_variable)
            )} {operator}= 1"

    factory(i, operator)

for command_id, command_function in {
    0x0014: "to_boolean",
    0x0022: "sqrt",
    0x0023: "invsqrt",
    0x0024: "invert",
    0x0025: "sin",
    0x0026: "cos",
    0x0027: "atan",
    0x0032: "fp_sqrt",
    0x0033: "fp_invsqrt",
    0x0034: "fp_invert",
    0x0035: "fp_sin",
    0x0036: "fp_cos",
    0x0037: "fp_atan",
    0x0029: "random_below",
    0x002A: "fp_set_variable",
    0x0030: "fp_to_int",
    0x0031: "fp_trunc",
}.items():

    def factory(command_id: int, command_function: str, /) -> None:
        @command_matcher(f"{command_id:04X},")
        def arithmetic_1_param_command(  # pyright: ignore[reportUnusedFunction]
            matched_commands: list[mnllib.Command],
            _context: CommandMatchContext,
            _match_start_index: int,
        ) -> str | None:
            return f"{command_function}({
                decompile_const_or_variable(matched_commands[0].arguments[0], fhex)
            }, {decompile_variable(
                typing.cast(mnllib.Variable, matched_commands[0].result_variable)
            )})"

    factory(command_id, command_function)

for command_id, command_function in {
    0x0028: "atan2",
    0x002B: "fp_add",
    0x002C: "fp_subtract",
    0x002D: "fp_multiply",
    0x002E: "fp_divide",
    0x002F: "fp_modulo",
    0x0038: "fp_atan2",
}.items():

    def factory(command_id: int, command_function: str, /) -> None:
        @command_matcher(f"{command_id:04X},")
        def arithmetic_2_param_command(  # pyright: ignore[reportUnusedFunction]
            matched_commands: list[mnllib.Command],
            _context: CommandMatchContext,
            _match_start_index: int,
        ) -> str | None:
            return f"{command_function}({
                decompile_const_or_variable(matched_commands[0].arguments[0], fhex)
            }, {
                decompile_const_or_variable(matched_commands[0].arguments[1], fhex)
            }, {decompile_variable(
                typing.cast(mnllib.Variable, matched_commands[0].result_variable)
            )})"

    factory(command_id, command_function)


@command_matcher("(?:0096,)?01B[9A],(?:01BD,)?(?:0096,)?")
def say(
    matched_commands: list[mnllib.Command],
    context: CommandMatchContext,
    match_start_index: int,
) -> str | None:
    result = io.StringIO()
    result_post = io.StringIO()

    anim: int | mnllib.Variable | None = None
    if matched_commands[0].command_id == 0x0096:
        if (
            matched_commands[1].command_id != 0x01BA
            or matched_commands[0].arguments[0] != matched_commands[1].arguments[0]
            or matched_commands[0].arguments[2] != 0x01
        ):
            result.write(
                f"{set_animation(matched_commands[:1], context, match_start_index)}\n"
            )
        else:
            anim = matched_commands[0].arguments[1]
        del matched_commands[0]
        match_start_index += 1

    wait_command_unk1: int | mnllib.Variable | None = None
    if len(matched_commands) >= 2 and matched_commands[1].command_id == 0x01BD:
        wait_command_unk1 = matched_commands[1].arguments[0]
        if wait_command_unk1 != 0x00:
            result_post.write(
                f"\n{wait_for_textbox(
                    matched_commands[1:2], context, match_start_index + 1
                )}"
            )
        del matched_commands[1]

    post_anim: int | mnllib.Variable | None = None
    if len(matched_commands) >= 2 and matched_commands[1].command_id == 0x0096:
        if (
            matched_commands[0].command_id != 0x01BA
            or matched_commands[1].arguments[0] != matched_commands[0].arguments[0]
            or matched_commands[1].arguments[2] != 0x01
        ):
            result_post.write(
                f"\n{set_animation(
                    matched_commands[1:2], context, match_start_index + 1
                )}"
            )
        else:
            post_anim = matched_commands[1].arguments[1]
        del matched_commands[1]

    common_args = matched_commands[0].arguments[
        1 if matched_commands[0].command_id == 0x01BA else 2 : (
            -1 if matched_commands[0].command_id == 0x01BA else -2
        )
    ]
    text_entry_index = common_args[10]
    room_id = context.script_index // 3
    if text_entry_index == DecompilerGlobals.next_text_entry_index[room_id]:
        language_table = context.chunk_triple[2]
        if not isinstance(language_table, mnllib.LanguageTable):
            raise TypeError(
                f"chunk 2 of room {fhex(room_id, 4)} is not "
                f"an mnllib.LanguageTable, but rather '{type(language_table).__name__}'"
            )
        message = decompile_text_entry(
            language_table, typing.cast(int, text_entry_index)
        )
        DecompilerGlobals.next_text_entry_index[room_id] += 1
    else:
        message = decompile_const_or_variable(text_entry_index, fhex_byte)
    arguments: list[str] = [
        # actor_or_position
        (
            decompile_const_or_variable(matched_commands[0].arguments[0], fhex_byte)
            if matched_commands[0].command_id == 0x01BA
            else f"({decompile_const_or_variable(
                matched_commands[0].arguments[0], fhex_short
            )}, {decompile_const_or_variable(
                matched_commands[0].arguments[1], fhex_short
            )})"
        ),
        # sound
        decompile_const_or_variable(
            common_args[9], lambda value: decompile_enum(Sound, value, fhex_int)
        ),
        message,
        f"anim={
            decompile_const_or_variable(
                anim, fhex_byte
            ) if anim is not None else "None"
        }",
        f"post_anim={
            decompile_const_or_variable(
                post_anim, fhex_byte
            ) if post_anim is not None else "None"
        }",
    ]
    if common_args[2] != BubbleType.NORMAL:
        arguments.append(
            f"bubble={decompile_const_or_variable(
                common_args[2],
                lambda value: decompile_enum(BubbleType, value, fhex_byte)
            )}"
        )
    if common_args[3] != TailType.NORMAL:
        arguments.append(
            f"tail={decompile_const_or_variable(
                common_args[3],
                lambda value: decompile_enum(TailType, value, fhex_byte)
            )}"
        )
    if common_args[8] != 0:
        arguments.append(
            f"wait={
                "False" if common_args[8] == 1
                else decompile_const_or_variable(common_args[8], fhex_byte)
            }"
        )
    if matched_commands[0].arguments[-1] != TextboxColor.NORMAL:
        arguments.append(
            f"color={decompile_const_or_variable(
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
            f"tail_size={decompile_const_or_variable(common_args[4], fhex_byte)}"
        )
    if common_args[5] != -1:
        arguments.append(
            f"tail_direction={decompile_const_or_variable(common_args[5], fhex_byte)}"
        )
    if isinstance(common_args[6], int):
        tail_hoffset, textbox_hoffset = struct.unpack(
            "<bb", struct.pack("<h", common_args[6])
        )
        if textbox_hoffset != -1:
            arguments.append(f"textbox_hoffset={fhex(textbox_hoffset, 2)}")
        if tail_hoffset != -1:
            arguments.append(f"tail_hoffset={fhex(tail_hoffset, 2)}")
    else:
        arguments.append(
            f"hoffsets_arg={decompile_const_or_variable(common_args[6], fhex_short)}"
        )
    if common_args[8] != 0 and wait_command_unk1 == 0x00:
        arguments.append("force_wait_command=True")
    if common_args[8] == 0 and wait_command_unk1 != 0x00:
        arguments.append("force_wait_command=False")
    result_variable = typing.cast(mnllib.Variable, matched_commands[0].result_variable)
    if result_variable.number != 0x1000:
        arguments.append(f"res={decompile_variable(result_variable)}")
    if common_args[7] != 0x01:
        arguments.append(
            f"unk9={decompile_const_or_variable(common_args[7], fhex_byte)}"
        )
    if (
        matched_commands[0].command_id == 0x01B9
        and matched_commands[0].arguments[13] != 0x0000
    ):
        arguments.append(
            f"unk14={decompile_const_or_variable(
                matched_commands[0].arguments[13], fhex_short
            )}"
        )
    result.write(f"say({", ".join(arguments)})")

    return result.getvalue() + result_post.getvalue()


@command_matcher("0096,")
def set_animation(
    matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return f"set_animation({
        decompile_const_or_variable(matched_commands[0].arguments[0], fhex_byte)
        if matched_commands[0].arguments[0] != -1 else "Self"
    }, {
        decompile_const_or_variable(matched_commands[0].arguments[1], fhex_byte)
    }{f", unk3={
        decompile_const_or_variable(matched_commands[0].arguments[2], fhex_byte)
    }" if matched_commands[0].arguments[2] != 0x01 else ""})"


@command_matcher("01BD,")
def wait_for_textbox(
    matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return f"wait_for_textbox({f"unk1={
        decompile_const_or_variable(matched_commands[0].arguments[0], fhex_byte)
    }" if matched_commands[0].arguments[0] != 0x00 else ""})"


@command_matcher("0199,")
def show_save_dialog(
    matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    args: list[str] = []
    if matched_commands[0].arguments[2] != 1:
        args.append(
            f"fade_in={decompile_bool_int_or_variable(
                matched_commands[0].arguments[2], fhex_byte,
            )}"
        )
    if matched_commands[0].arguments[0] != 0x00:
        args.append(
            f"unk1={decompile_const_or_variable(
                matched_commands[0].arguments[0], fhex_byte,
            )}"
        )
    if matched_commands[0].arguments[1] != 0x01:
        args.append(
            f"unk2={decompile_const_or_variable(
                matched_commands[0].arguments[1], fhex_byte,
            )}"
        )
    return f"show_save_dialog({", ".join(args)})"


@command_matcher("01AE,")
def swap_screens(
    _matched_commands: list[mnllib.Command],
    _context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    return "swap_screens()"


@command_matcher("....,")
def unknown_command(
    matched_commands: list[mnllib.Command],
    context: CommandMatchContext,
    _match_start_index: int,
) -> str | None:
    formatted_args = [
        decompile_const_or_variable(
            argument,
            lambda value: fhex(
                value,
                mnllib.COMMAND_PARAMETER_STRUCT_MAP[
                    context.manager.command_parameter_metadata_table[
                        matched_commands[0].command_id
                    ].parameter_types[i]
                ].size
                * 2,
            ),
        )
        for i, argument in enumerate(matched_commands[0].arguments)
    ]
    return f"emit_command({fhex(matched_commands[0].command_id, 4)}{
        f", [{", ".join(formatted_args)}]"
        if len(formatted_args) > 0 or matched_commands[0].result_variable is not None
        else ""
    }{
        f", {decompile_variable(matched_commands[0].result_variable)}"
        if matched_commands[0].result_variable is not None
        else ""
    })"


class CommandsNotMatchedError(Exception):
    message: str
    subroutine: mnllib.Subroutine
    match_start_index: int

    def __init__(
        self,
        subroutine: mnllib.Subroutine,
        match_start_index: int,
        message: str | None = None,
    ) -> None:
        if message is None:
            message = (
                f"{fhex(subroutine.commands[match_start_index].command_id, 4)} "
                f"(at index {match_start_index})"
            )
        super().__init__(message)
        self.message = message
        self.subroutine = subroutine
        self.match_start_index = match_start_index

    def __reduce__(
        self,
    ) -> tuple[type[typing.Self], tuple[mnllib.Subroutine, int, str]]:
        return self.__class__, (self.subroutine, self.match_start_index, self.message)


def decompile_subroutine_commands(
    manager: mnllib.MnLScriptManager,
    subroutine: mnllib.Subroutine,
    chunk_triple: tuple[
        mnllib.FEventScript | None, mnllib.FEventChunk | None, mnllib.FEventChunk | None
    ],
    script_index: int,
    output: typing.TextIO,
    line_prefix: str,
) -> None:
    commands_string = "".join(
        [f"{command.command_id:04X}," for command in subroutine.commands]
    )
    context = CommandMatchContext(manager, chunk_triple, script_index, subroutine)
    command_index = 0
    while command_index < len(subroutine.commands):
        for matcher in command_matchers:
            match = matcher.pattern.match(commands_string, pos=command_index * 5)
            if match is None:
                continue
            match_start, match_end = match.span()
            matched_commands_number = math.ceil((match_end - match_start) / 5)
            decompiled_match = matcher.handler(
                subroutine.commands[
                    command_index : command_index + matched_commands_number
                ],
                context,
                command_index,
            )
            if decompiled_match is None:
                continue
            if command_index != 0:
                output.write("\n")
            output.write(textwrap.indent(decompiled_match, prefix=line_prefix))
            command_index += matched_commands_number
            break
        else:
            raise CommandsNotMatchedError(subroutine, command_index)
