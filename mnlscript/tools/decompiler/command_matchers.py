import itertools
import math
import re
import textwrap
import typing

import mnllib

from ...script import OFFSET_FOOTER
from ...utils import fhex
from .misc import (
    decompile_const_or_f32_or_variable,
    decompile_float32,
    decompile_variable,
    fhex_or,
)


class ScriptContext:
    manager: mnllib.MnLScriptManager
    script_index: int
    subroutine_offsets: list[tuple[int, int]]
    debug_message_offsets: list[int]
    subroutine: mnllib.Subroutine

    def __init__(
        self,
        manager: mnllib.MnLScriptManager,
        script_index: int,
        subroutine_offsets: list[tuple[int, int]],
        debug_message_offsets: list[int],
        subroutine: mnllib.Subroutine,
    ) -> None:
        self.manager = manager
        self.script_index = script_index
        self.subroutine_offsets = subroutine_offsets
        self.debug_message_offsets = debug_message_offsets
        self.subroutine = subroutine


class CommandMatchContext[SC: ScriptContext]:
    script: SC
    decompiled_commands: dict[int, str | None]
    labels: dict[int, str]
    split_hints: set[int]
    match_start_index: int
    match_offset: int

    @typing.overload
    def __init__(
        self,
        script: SC,
        decompiled_commands: dict[int, str | None],
        labels: dict[int, str],
        split_hints: set[int],
        match_start_index: int,
        match_offset: int,
    ) -> None: ...
    @typing.overload
    def __init__(self, other: typing.Self, **overrides: typing.Any) -> None: ...

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        if isinstance(args[0], CommandMatchContext):
            self.__dict__.update(args[0].__dict__)
            self.__dict__.update(kwargs)
        else:
            self.script = kwargs["script"] if "script" in kwargs else args[0]
            self.decompiled_commands = (
                kwargs["decompiled_commands"]
                if "decompiled_commands" in kwargs
                else args[1]
            )
            self.labels = kwargs["labels"] if "labels" in kwargs else args[2]
            self.split_hints = (
                kwargs["split_hints"] if "split_hints" in kwargs else args[3]
            )
            self.match_start_index = (
                kwargs["match_start_index"]
                if "match_start_index" in kwargs
                else args[4]
            )
            self.match_offset = (
                kwargs["match_offset"] if "match_offset" in kwargs else args[5]
            )


type CommandMatchHandler[SC: ScriptContext] = typing.Callable[
    [list[mnllib.CodeCommand], CommandMatchContext[SC]], str | dict[int, str] | None
]


class CommandMatcher[SC: ScriptContext]:
    pattern: re.Pattern[str]
    handler: CommandMatchHandler[SC]
    offset_params: list[tuple[int, int]]

    def __init__(
        self,
        pattern: re.Pattern[str],
        handler: CommandMatchHandler[SC],
        offset_params: list[tuple[int, int]] | None = None,
    ) -> None:
        self.pattern = pattern
        self.handler = handler
        self.offset_params = offset_params if offset_params is not None else []


class CommandMatcherDecorator[SC: ScriptContext](typing.Protocol):
    def __call__(
        self,
        pattern: str | re.Pattern[str],
        *,
        offset_params: list[tuple[int, int]] | None = None,
    ) -> typing.Callable[[CommandMatchHandler[SC]], CommandMatchHandler[SC]]: ...


def create_command_matcher_decorator[SC: ScriptContext](
    command_matchers: list[CommandMatcher[SC]],
) -> CommandMatcherDecorator[SC]:
    def command_matcher(
        pattern: str | re.Pattern[str],
        *,
        offset_params: list[tuple[int, int]] | None = None,
    ) -> typing.Callable[[CommandMatchHandler[SC]], CommandMatchHandler[SC]]:
        if not isinstance(pattern, re.Pattern):
            pattern = re.compile(rf"\b(?:{pattern})", re.IGNORECASE)

        def decorator(handler: CommandMatchHandler[SC]) -> CommandMatchHandler[SC]:
            command_matchers.append(CommandMatcher(pattern, handler, offset_params))
            return handler

        return decorator

    return command_matcher


def merge_decompiled_match[O](
    decompiled_commands: dict[int, str | O],
    offset: int,
    decompiled_match: str | dict[int, str] | None,
) -> None:
    if isinstance(decompiled_match, dict):
        decompiled_commands.update(decompiled_match)
    elif decompiled_match is not None:
        decompiled_commands[offset] = decompiled_match


def decompile_offset[SC: ScriptContext](
    matched_commands: list[mnllib.CodeCommand],
    context: CommandMatchContext[SC],
    offset: int | float | mnllib.Variable,
    int_formatter: typing.Callable[[int], str],
    *,
    force_tuple: bool = False,
) -> str:
    if isinstance(offset, int):
        absolute_offset = (
            context.match_offset
            + sum(
                command.serialized_len(context.script.manager, -1)
                for command in matched_commands
            )
            + offset
        )
        try:
            label = context.labels[absolute_offset]
        except KeyError:
            pass
        else:
            return f"{"(" if force_tuple else ""}{
                repr(label)
            }{f", {int_formatter(0)}" if force_tuple else ""}"
        if absolute_offset in context.decompiled_commands:
            label = f"label_{len(context.labels)}"
            context.labels[absolute_offset] = label
            return f"{"(" if force_tuple else ""}{
                repr(label)
            }{f", {int_formatter(0)}" if force_tuple else ""}"
        try:
            subroutine_offset_index, subroutine_offset = next(
                (i, x)
                for i, x in reversed(
                    list(
                        enumerate(
                            itertools.chain.from_iterable(
                                context.script.subroutine_offsets
                            )
                        )
                    )
                )
                if absolute_offset >= x
            )
        except StopIteration:
            pass
        else:
            use_tuple = absolute_offset != subroutine_offset or force_tuple
            return f"{"(" if use_tuple else ""}{repr(
                f"sub_{
                    f"0x{subroutine_offset_index // 2 - 1:x}"
                    if subroutine_offset_index >= 2
                    else "post_table"
                }{"." + OFFSET_FOOTER if subroutine_offset_index % 2 == 1 else ""}"
            )}{f", {int_formatter(absolute_offset - subroutine_offset)})"
                if use_tuple else ""}"

    return decompile_const_or_f32_or_variable(offset, int_formatter)


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
            message = f"{fhex(
                typing.cast(
                    mnllib.CodeCommand, subroutine.commands[match_start_index]
                ).command_id,
                4,
            )} (at index {match_start_index})"
        super().__init__(message)
        self.message = message
        self.subroutine = subroutine
        self.match_start_index = match_start_index

    def __reduce__(
        self,
    ) -> tuple[type[typing.Self], tuple[mnllib.Subroutine, int, str]]:
        return self.__class__, (self.subroutine, self.match_start_index, self.message)


def decompile_subroutine_commands[SC: ScriptContext](
    command_matchers: list[CommandMatcher[SC]],
    subroutine: mnllib.Subroutine,
    script_context: SC,
    offset: int,
    add_offsets: bool,
    output: typing.TextIO,
    line_prefix: str,
) -> None:
    decompiled_commands: dict[int, str | None] = {}
    labels: dict[int, str] = {}
    branching_commands: list[
        tuple[CommandMatcher[SC], list[mnllib.CodeCommand], int, int]
    ] = []
    split_hints = set[int]()
    commands_string = "".join(
        [
            (
                f"{command.command_id:04X},"
                if isinstance(command, mnllib.CodeCommand)
                else "----,"
            )
            for command in subroutine.commands
        ]
    )
    command_index = 0
    while command_index < len(subroutine.commands):
        command = subroutine.commands[command_index]

        if (
            command_index == len(subroutine.commands) - 1
            and isinstance(command, mnllib.CodeCommand)
            and command.command_id == 0x0001
        ):
            decompiled_commands[offset] = None
            break

        if isinstance(command, mnllib.RawDataCommand):
            decompiled_commands[offset] = f"data({command.data!r})"
            command_index += 1
            offset += command.serialized_len(script_context.manager, offset)
            continue
        elif isinstance(command, mnllib.ArrayCommand):
            decompiled_commands[offset] = (
                f"array(MnLDataTypes.{
                    mnllib.MnLDataTypes(
                        command.data_type  # type: ignore[call-arg,arg-type]
                    ).name
                }, [{", ".join([
                    fhex_or(
                        x,
                        decompile_float32,
                        width=command.data_type.struct_obj.size * 2,
                    )
                    for x in command.array
                ])}])"
            )
            command_index += 1
            offset += command.serialized_len(script_context.manager, offset)
            continue

        for matcher in command_matchers:
            match = matcher.pattern.match(commands_string, pos=command_index * 5)
            if match is None:
                continue
            match_start, match_end = match.span()
            matched_commands_number = math.ceil((match_end - match_start) / 5)
            matched_commands_raw = subroutine.commands[
                command_index : command_index + matched_commands_number
            ]
            if any(
                not isinstance(command, mnllib.CodeCommand)
                for command in matched_commands_raw
            ):
                continue
            matched_commands = typing.cast(
                list[mnllib.CodeCommand], matched_commands_raw
            )
            if len(matcher.offset_params) > 0:
                branching_commands.append(
                    (matcher, matched_commands, command_index, offset)
                )
                decompiled_commands[offset] = None
                for offset_command_index, offset_param in matcher.offset_params:
                    offset_arg = matched_commands[offset_command_index].arguments[
                        offset_param
                    ]
                    if isinstance(offset_arg, int):
                        split_hints.add(
                            offset
                            + sum(
                                command.serialized_len(script_context.manager, -1)
                                for command in matched_commands[
                                    : offset_command_index + 1
                                ]
                            )
                            + offset_arg
                        )
            else:
                decompiled_match = matcher.handler(
                    matched_commands.copy(),
                    CommandMatchContext(
                        script_context,
                        decompiled_commands,
                        labels,
                        split_hints,
                        command_index,
                        offset,
                    ),
                )
                if decompiled_match is None:
                    continue
                merge_decompiled_match(decompiled_commands, offset, decompiled_match)
            command_index += matched_commands_number
            offset += sum(
                command.serialized_len(script_context.manager, -1)
                for command in matched_commands
            )
            break
        else:
            raise CommandsNotMatchedError(subroutine, command_index)

    for matcher, matched_commands, command_index, offset in branching_commands:
        merge_decompiled_match(
            decompiled_commands,
            offset,
            matcher.handler(
                matched_commands,
                CommandMatchContext(
                    script_context,
                    decompiled_commands,
                    labels,
                    split_hints,
                    command_index,
                    offset,
                ),
            ),
        )

    first = True
    for offset, decompiled_command in sorted(decompiled_commands.items()):
        if offset in labels:
            if not first:
                output.write("\n\n")
            else:
                first = False
            output.write(
                textwrap.indent(
                    f"label({repr(labels[offset])})"
                    + (f"  # {fhex(offset, 8)}" if add_offsets else ""),
                    prefix=line_prefix,
                )
            )

        if decompiled_command is None:
            continue
        if not first:
            output.write("\n")
        else:
            first = False
        output.write(
            textwrap.indent(
                decompiled_command + (f"  # {fhex(offset, 8)}" if add_offsets else ""),
                prefix=line_prefix,
            )
        )


def unknown_command_matcher[SC: ScriptContext](
    matched_commands: list[mnllib.CodeCommand],
    context: CommandMatchContext[SC],
) -> str | dict[int, str] | None:
    formatted_args = [
        decompile_const_or_f32_or_variable(
            argument,
            lambda value: fhex(
                value,
                width=context.script.manager.command_metadata_table[
                    matched_commands[0].command_id
                ]
                .parameter_types[i]
                .struct_obj.size
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
