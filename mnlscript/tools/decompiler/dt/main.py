import functools
import io
import itertools
import multiprocessing
import pathlib
import struct
import sys
import textwrap
import typing
import warnings

import mnllib
import mnllib.dt
import mnllib.n3ds
import pymsbmnl
import tqdm

from ....consts import INIT_SCRIPT_FILENAME
from ....dt.sound import load_sound_names
from ....utils import fhex
from ...consts import FEVENT_SCRIPTS_DIR
from ..command_matchers import decompile_subroutine_commands
from ..misc import (
    DecompilerArguments,
    MnLScriptDecompilerWarning,
    create_decompiler_argument_parser,
)
from .command_matchers import DTScriptContext, command_matchers
from .globals import DecompilerGlobals
from .misc import CreateCallCondition, decompile_text_entry


def decompile_subroutine(
    manager: mnllib.MnLScriptManager,
    subroutine: mnllib.Subroutine,
    script: mnllib.dt.FEventScript,
    script_index: int,
    text_chunks: dict[str, pymsbmnl.LMSDocument],
    subroutine_offsets: list[tuple[int, int]],
    debug_message_offsets: list[int],
    add_offsets: bool,
    index: int | None,
    output: typing.TextIO,
) -> None:
    has_return = (
        len(subroutine.commands) > 0
        and isinstance(subroutine.commands[-1], mnllib.CodeCommand)
        and subroutine.commands[-1].command_id == 0x0001
    )

    decorator_args: list[str] = []
    if index is None:
        decorator_args.append("post_table=True")
    elif index == script.header.init_subroutine:
        decorator_args.append("init=True")
    if not has_return:
        decorator_args.append("no_return=True")
    if subroutine.footer:
        decorator_args.append(f"footer={subroutine.footer!r}")
    output.write(
        textwrap.dedent(
            f"""\
            @subroutine({", ".join(decorator_args)})
            def sub_{
                f"0x{index:x}" if index is not None else "post_table"
            }(sub: Subroutine):
            """
        )
    )

    if len(subroutine.commands) > (1 if has_return else 0):
        decompile_subroutine_commands(
            command_matchers,
            subroutine,
            DTScriptContext(
                manager,
                script_index,
                subroutine_offsets,
                debug_message_offsets,
                subroutine,
                script,
                text_chunks,
            ),
            subroutine_offsets[index + 1 if index is not None else 0][0],
            add_offsets,
            output,
            " " * 4,
        )
    else:
        output.write("    pass")


def decompile_script(
    manager: mnllib.dt.FEventScriptManager,
    script: mnllib.dt.FEventScript,
    text_chunks: dict[str, pymsbmnl.LMSDocument],
    add_offsets: bool,
    index: int,
    output: typing.TextIO,
) -> None:
    subroutine_offsets: list[tuple[int, int]] = []
    offset = len(script.header.to_bytes(manager))
    for subroutine in itertools.chain(
        [script.header.post_table_subroutine], script.subroutines
    ):
        if len(subroutine.commands) > 0 and isinstance(
            subroutine.commands[0], mnllib.ArrayCommand
        ):
            offset += (-offset) % 4
        subroutine_offset = offset
        offset += subroutine.serialized_len(manager, offset, with_footer=False)
        subroutine_offsets.append((subroutine_offset, offset))
        offset += len(subroutine.footer)

    debug_message_offsets: list[int] = []
    offset = 0
    for message in script.debug_messages:
        debug_message_offsets.append(offset)
        offset += len(message.encode(mnllib.MNL_DEBUG_MESSAGE_ENCODING)) + 1

    output.write(
        textwrap.dedent(
            f"""\
            from mnllib import *
            from mnllib.dt import *
            from mnlscript import *
            from mnlscript.dt import *


            header = FEventScriptHeader({
                    f"\n                unk_0x04={fhex(script.header.unk_0x04, 8)},"
                    if script.header.unk_0x04 != 0
                    else ""
                }{
                    f"\n                triggers=[{", ".join([
                        f"({", ".join(fhex(y, 8) for y in x)})"
                        for x in script.header.triggers
                    ])}],"
                    if index % 2 == 0 or len(script.header.triggers) > 0
                    else ""
                }
                sprite_groups=[{", ".join([fhex(x, 8) for x in script.header.sprite_groups])}],
                particle_effects=[{", ".join([fhex(x, 4) for x in script.header.particle_effects])}],
                actors=[{", ".join([
                    f"({", ".join([fhex(y, 8) for y in x])})"
                    for x in script.header.actors
                ])}],
                array4=[{", ".join([fhex(x, 8) for x in script.header.array4])}],

                index=script_index,
            )"""
        )
    )
    if script.header.post_table_subroutine != mnllib.Subroutine([]):
        output.write("\n\n\n")
        decompile_subroutine(
            manager,
            script.header.post_table_subroutine,
            script,
            index,
            text_chunks,
            subroutine_offsets,
            debug_message_offsets,
            add_offsets,
            None,
            output,
        )

    for i, subroutine in enumerate(script.subroutines):
        output.write("\n\n\n")
        decompile_subroutine(
            manager,
            subroutine,
            script,
            index,
            text_chunks,
            subroutine_offsets,
            debug_message_offsets,
            add_offsets,
            i,
            output,
        )

    room_id = index // 2
    number_of_text_entries: int | None = None
    for language, text_chunk in text_chunks.items():
        if number_of_text_entries is None:
            number_of_text_entries = len(text_chunk.messages)
        elif len(text_chunk.messages) != number_of_text_entries:
            raise ValueError(
                "all languagues' text chunks must have the same length but "
                f"chunk '{language}' of room {fhex(room_id, 4)} has a length of "
                f"{len(text_chunk.messages)} instead of {number_of_text_entries}"
            )
    remaining_text_entries = range(
        DecompilerGlobals.next_text_entry_index[room_id],
        number_of_text_entries if number_of_text_entries is not None else 0,
    )
    if len(remaining_text_entries) != 0:
        output.write("\n\n")

        for text_entry_index in remaining_text_entries:
            output.write(
                f"\nemit_text_entry({
                    decompile_text_entry(
                        text_chunks,
                        text_entry_index,
                        create_call_condition=CreateCallCondition.NEVER,
                    )
                })  # {fhex(text_entry_index, 2)}"
            )

    output.write("\n")


def process_script(
    args: DecompilerArguments,
    fevent_scripts_dir: pathlib.Path,
    scripts_casefolded: list[str],
    fevent_manager: mnllib.dt.FEventScriptManager,
    text_chunks: dict[str, list[pymsbmnl.LMSDocument]],
    room_id_and_pair_index: tuple[int, int],
) -> None:
    room_id, pair_index = room_id_and_pair_index

    if fevent_manager.fevent_scripts[room_id][pair_index] is None:
        return
    script_name = f"{room_id:04x}{"_enemies" if pair_index == 1 else ""}"
    if len(args.scripts) > 0 and script_name not in scripts_casefolded:
        return
    path = fevent_scripts_dir / f"{script_name}.py"
    if not args.force and not args.stdout and path.exists():
        tqdm.tqdm.write(
            f"WARNING: '{path}' already exists, refusing to overwrite it! "
            "To overwrite existing scripts, pass `-f` / `--force`.",
            file=sys.stderr,
        )
        return

    script = typing.cast(
        mnllib.dt.FEventScript,
        fevent_manager.parsed_script(room_id, pair_index, save=False),
    )
    if pair_index == 0:
        current_text_chunks = {
            language: chunks[room_id] for language, chunks in text_chunks.items()
        }
    else:
        current_text_chunks = {}
    script_index = room_id * 2 + pair_index
    with (
        path.open("w", encoding="utf-8") if not args.stdout else io.StringIO()
    ) as output:
        decompile_script(
            fevent_manager,
            script,
            current_text_chunks,
            args.add_offsets,
            script_index,
            output,
        )
        if args.stdout:
            sys.stdout.buffer.write(struct.pack("=hI", script_index, output.tell()))
            sys.stdout.write(
                typing.cast(  # pyright: ignore[reportUnnecessaryCast]
                    io.StringIO, output
                ).getvalue()
            )


def main() -> None:
    argp = create_decompiler_argument_parser("Mario & Luigi: Dream Team (Bros.)")
    args = argp.parse_args(namespace=DecompilerArguments())

    sound_data_path = mnllib.n3ds.fs_std_romfs_path(
        mnllib.dt.SOUND_DATA_PATH, data_dir=args.data_dir
    )
    try:
        DecompilerGlobals.sound_names = load_sound_names(sound_data_path)
    except FileNotFoundError:
        warnings.warn(
            f"'{sound_data_path}' is missing, continuing without sound names!",
            MnLScriptDecompilerWarning,
        )

    fevent_manager = mnllib.dt.FEventScriptManager(
        data_dir=args.data_dir, parse_all=False
    )

    message_dir = mnllib.n3ds.fs_std_romfs_path(
        mnllib.dt.MESSAGE_DIR_PATH, data_dir=args.data_dir
    )
    text_chunks: dict[str, list[pymsbmnl.LMSDocument]] = {}
    for message_file_path in sorted(message_dir.glob("*/FMes.dat")):
        language = message_file_path.parent.name
        with (
            message_file_path.open("rb") as message_file,
            message_file_path.with_suffix(".bin").open("rb") as offset_table,
        ):
            text_chunks[language] = mnllib.dt.read_msbt_archive(
                message_file, offset_table, language
            )

    fevent_scripts_dir = args.scripts_dir / FEVENT_SCRIPTS_DIR
    fevent_scripts_dir.mkdir(parents=True, exist_ok=True)
    (args.scripts_dir / INIT_SCRIPT_FILENAME).touch()
    (fevent_scripts_dir / INIT_SCRIPT_FILENAME).touch()

    scripts_casefolded = [script_name.casefold() for script_name in args.scripts]
    with multiprocessing.Pool() as pool:
        for _ in tqdm.tqdm(
            pool.imap_unordered(
                functools.partial(
                    process_script,
                    args,
                    fevent_scripts_dir,
                    scripts_casefolded,
                    fevent_manager,
                    text_chunks,
                ),
                (
                    (room_id, pair_index)
                    for room_id in range(len(fevent_manager.fevent_scripts))
                    for pair_index in range(2)
                ),
                chunksize=100,
            ),
            total=len(fevent_manager.fevent_scripts) * 2,
        ):
            pass


if __name__ == "__main__":
    main()
