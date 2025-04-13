import re
import typing

import mnllib

from .globals import CommonGlobals


LABEL_REGEX = re.compile(r"(?:(labels|subs)\[([^\]]+)\]|([^\[\].]+))(?:\.(.+))?")

type Offset = str | tuple[str, int] | int
OFFSET_FOOTER = "footer"


class CodeCommandWithOffsets(mnllib.CodeCommand):
    offset_arguments: dict[int, Offset]

    def __init__(
        self,
        command_id: int,
        arguments: list[int | float | mnllib.Variable] = [],
        result_variable: mnllib.Variable | None = None,
        *,
        offset_arguments: dict[int, Offset] = {},
    ) -> None:
        super().__init__(command_id, arguments, result_variable)

        self.offset_arguments = offset_arguments


class SubroutineExt(typing.Protocol):
    name: str
    labels: dict[str, int]


def resolve_label(
    label: str,
    subroutine: mnllib.Subroutine,
    subroutine_offset: int,
    subroutine_offsets: dict[str, tuple[int, int]],
) -> int:
    match = LABEL_REGEX.fullmatch(label)
    if match is None:
        raise ValueError(f"invalid label format: {label}")
    index_type, index, label_name, property = match.groups()
    is_footer = property == OFFSET_FOOTER

    subroutine_ext = typing.cast(SubroutineExt, subroutine)

    match index_type:
        case "labels":
            return (
                subroutine_offset
                + list(subroutine_ext.labels.values())[int(index, base=0)]
            )
        case "subs":
            return list(subroutine_offsets.values())[int(index, base=0)][
                0 if not is_footer else 1
            ]
        case _:
            pass

    try:
        return subroutine_offset + subroutine_ext.labels[label_name]
    except (AttributeError, KeyError):
        pass

    try:
        return subroutine_offsets[label_name][0 if not is_footer else 1]
    except KeyError:
        raise LookupError(f"couldn't resolve label: {label}")


def resolve_offset(
    offset: Offset,
    subroutine: mnllib.Subroutine,
    subroutine_offset: int,
    subroutine_offsets: dict[str, tuple[int, int]],
) -> int:
    if isinstance(offset, int):
        return offset

    return resolve_label(
        offset if isinstance(offset, str) else offset[0],
        subroutine,
        subroutine_offset,
        subroutine_offsets,
    ) + (0 if isinstance(offset, str) else offset[1])


def compute_post_command_offsets(
    subroutine: mnllib.Subroutine, offset: int
) -> list[int]:
    result: list[int] = []

    for command in subroutine.commands:
        offset += command.serialized_len(CommonGlobals.script_manager, offset)
        result.append(offset)

    return result


def update_commands_with_offsets(
    subroutines: list[mnllib.Subroutine],
    offset: int,
) -> None:
    subroutine_offsets: dict[str, tuple[int, int]] = {}
    post_command_offsets: list[list[int]] = []

    # current_subroutine_offset = 0
    # with multiprocessing.Pool() as pool:
    #     for i, current_post_command_offsets in enumerate(
    #         pool.imap(compute_post_command_offsets, subroutines, chunksize=10)
    #     ):
    #         subroutine = subroutines[i]
    #         subroutine_ext = typing.cast(SubroutineExt, subroutine)
    #
    #         subroutine_offsets[subroutine_ext.name] = current_subroutine_offset
    #         post_command_offsets.append(
    #             [x + current_subroutine_offset for x in current_post_command_offsets]
    #         )
    #         current_subroutine_offset += (
    #             current_post_command_offsets[-1]
    #             if len(current_post_command_offsets) > 0
    #             else 0
    #         ) + len(subroutine.footer)
    for subroutine in subroutines:
        subroutine_ext = typing.cast(SubroutineExt, subroutine)

        if len(subroutine.commands) > 0 and isinstance(
            subroutine.commands[0], mnllib.ArrayCommand
        ):
            offset += (-offset) % 4

        current_subroutine_offset = offset
        current_post_command_offsets: list[int] = []
        for command in subroutine.commands:
            offset += command.serialized_len(CommonGlobals.script_manager, offset)
            current_post_command_offsets.append(offset)
        subroutine_offsets[subroutine_ext.name] = (current_subroutine_offset, offset)
        post_command_offsets.append(current_post_command_offsets)

        offset += len(subroutine.footer)

    for subroutine_index, subroutine in enumerate(subroutines):
        subroutine_ext = typing.cast(SubroutineExt, subroutine)

        for command_index, command in enumerate(subroutine.commands):
            if isinstance(command, CodeCommandWithOffsets):
                for argument_index, offset_arg in command.offset_arguments.items():
                    command.arguments[argument_index] = (
                        resolve_offset(
                            offset_arg,
                            subroutine,
                            subroutine_offsets[subroutine_ext.name][0],
                            subroutine_offsets,
                        )
                        - post_command_offsets[subroutine_index][command_index]
                    )
