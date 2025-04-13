import argparse
import copyreg
import enum
import pathlib
import struct
import typing

import mnllib
import numpy

from ..consts import DEFAULT_SCRIPTS_DIR_PATH
from ...utils import fhex


class MnLScriptDecompilerWarning(UserWarning):
    pass


def pickle_struct(value: struct.Struct) -> tuple[type[struct.Struct], tuple[str]]:
    return struct.Struct, (value.format,)


copyreg.pickle(struct.Struct, pickle_struct)


def decompile_float32(value: float | numpy.float32) -> str:
    return str(numpy.float32(value))


def decompile_int_bool[T](
    value: T,
    unknown_formatter: typing.Callable[[T], str] = lambda value: fhex_or(
        value, repr, width=2
    ),
    *,
    invert: bool = False,
) -> str:
    if value in [0, 1]:
        return repr(bool(value) != invert)
    return unknown_formatter(value)


def decompile_enum[T](
    enum_type: type[enum.Enum],
    value: T,
    unknown_formatter: typing.Callable[[T], str] = repr,
) -> str:
    if not issubclass(enum_type, enum.Flag):
        try:
            return f"{enum_type.__name__}.{enum_type(value).name}"
        except ValueError:
            return unknown_formatter(value)

    for name, member in enum_type.__members__.items():
        if len(member) != 1 and value == member:
            return f"{enum_type.__name__}.{name}"
    members: list[str] = []
    reconstructed_value = enum_type(0)
    for member in enum_type(value):
        if member.name is None:
            continue
        members.append(f"{enum_type.__name__}.{member.name}")
        reconstructed_value |= member
    extra_value = (enum_type(value) ^ reconstructed_value).value
    if extra_value != 0:
        members.append(unknown_formatter(typing.cast(T, extra_value)))
    return " | ".join(members)


def decompile_variable(variable: mnllib.Variable) -> str:
    return f"Variables[{fhex(variable.number, 4)}]"


def repr_or_float32(value: float | object) -> str:
    if isinstance(value, float):
        return decompile_float32(value)
    else:
        return repr(value)


def fhex_or[T](
    value: T, unknown_formatter: typing.Callable[[T], str], width: int = 0
) -> str:
    if isinstance(value, int):
        return fhex(value, width=width)
    else:
        return unknown_formatter(value)


def decompile_const_or_variable[T](
    value: T | mnllib.Variable,
    const_formatter: typing.Callable[[T], str] = repr_or_float32,
) -> str:
    if isinstance(value, mnllib.Variable):
        return decompile_variable(value)
    return const_formatter(value)


def decompile_const_or_f32_or_variable[T](
    value: T | float | mnllib.Variable,
    const_formatter: typing.Callable[[T], str] = repr,
) -> str:
    if isinstance(value, float):
        return decompile_float32(value)
    else:
        return decompile_const_or_variable(
            typing.cast(T | mnllib.Variable, value),
            const_formatter=const_formatter,
        )


class DecompilerArguments(argparse.Namespace):
    scripts: list[str]
    data_dir: pathlib.Path
    scripts_dir: pathlib.Path
    force: bool
    add_offsets: bool
    stdout: bool


def create_decompiler_argument_parser(game_name: str) -> argparse.ArgumentParser:
    argp = argparse.ArgumentParser(
        description=f"Decompiler for the {game_name} scripting language to Python."
    )

    argp.add_argument(
        "scripts",
        help="the scripts to decompile. Leave blank for all.",
        nargs="*",
    )
    argp.add_argument(
        "-d",
        "--data-dir",
        help=f"""
            the directory containing the game data
            (default: '{mnllib.DEFAULT_DATA_DIR_PATH}')
        """,
        type=pathlib.Path,
        default=mnllib.DEFAULT_DATA_DIR_PATH,
    )
    argp.add_argument(
        "-s",
        "--scripts-dir",
        help=f"""
            the directory to place the decompiled scripts in
            (default: '{DEFAULT_SCRIPTS_DIR_PATH}')
        """,
        type=pathlib.Path,
        default=DEFAULT_SCRIPTS_DIR_PATH,
    )
    argp.add_argument(
        "-f",
        "--force",
        help="overwrite existing scripts",
        action="store_true",
    )
    argp.add_argument(
        "-a",
        "--add-offsets",
        help="""
            add the offset of every command and label in a comment
            at the end of the respective line
        """,
        action="store_true",
    )
    argp.add_argument(
        "-o",
        "--stdout",
        help="""
            output the decompiled scripts to STDOUT, and do not save anything.
            The script index is output first (signed 16-bit),
            followed by the length of the script (unsigned 32-bit),
            followed by the script itself.
            This repeats for every decompiled script.
        """,
        action="store_true",
    )

    return argp
