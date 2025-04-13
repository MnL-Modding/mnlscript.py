import argparse
import pathlib

import mnllib

from ..consts import DEFAULT_SCRIPTS_DIR_PATH


class CompilerArguments(argparse.Namespace):
    scripts: list[pathlib.Path]
    data_dir: pathlib.Path
    scripts_dir: pathlib.Path
    stdout: bool


def create_compiler_argument_parser(game_name: str) -> argparse.ArgumentParser:
    argp = argparse.ArgumentParser(
        description=f"Compiler for the {game_name} scripting language from Python."
    )

    argp.add_argument(
        "scripts",
        help="the scripts to compile. Leave blank for all.",
        type=pathlib.Path,
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
            the directory containing the scripts
            (default: '{DEFAULT_SCRIPTS_DIR_PATH}')
        """,
        type=pathlib.Path,
        default=DEFAULT_SCRIPTS_DIR_PATH,
    )
    argp.add_argument(
        "-o",
        "--stdout",
        help="""
            output the compiled chunks to STDOUT, and do not save anything.
            The chunk index is output first (signed 16-bit),
            followed by the length of the chunk (unsigned 32-bit),
            followed by the chunk itself.
            This repeats for every compiled chunk.
        """,
        action="store_true",
    )

    return argp
