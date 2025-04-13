import functools
import io
import itertools
import multiprocessing
import pathlib
import struct
import sys
import textwrap
import pprint
import typing

import mnllib
import mnllib.bis
import tqdm

from ....bis.text import LANGUAGE_IDS
from ....consts import INIT_SCRIPT_FILENAME
from ....utils import fhex
from ...consts import FEVENT_SCRIPTS_DIR
from ..command_matchers import decompile_subroutine_commands
from ..misc import DecompilerArguments, create_decompiler_argument_parser
from .command_matchers import BISScriptContext, command_matchers
from .globals import DecompilerGlobals
from .misc import decompile_text_entry


def decompile_subroutine(
    manager: mnllib.MnLScriptManager,
    subroutine: mnllib.Subroutine,
    chunk_triple: mnllib.bis.FEventChunkTriple,
    script_index: int,
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
    elif (
        index
        == typing.cast(
            mnllib.bis.FEventScript, chunk_triple[script_index % 3]
        ).header.init_subroutine
    ):
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
            BISScriptContext(
                manager,
                script_index,
                subroutine_offsets,
                debug_message_offsets,
                subroutine,
                chunk_triple,
            ),
            subroutine_offsets[index + 1 if index is not None else 0][0],
            add_offsets,
            output,
            " " * 4,
        )
    else:
        output.write("    pass")


def decompile_script(
    manager: mnllib.bis.FEventScriptManager,
    script: mnllib.bis.FEventScript,
    chunk_triple: mnllib.bis.FEventChunkTriple,
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
            from mnllib.bis import *
            from mnlscript import *
            from mnlscript.bis import *


            header = FEventScriptHeader({
                    f"\n                unk_0x04={fhex(script.header.unk_0x04, 8)},"
                    if script.header.unk_0x04 != 0
                    else ""
                }{
                    f"\n                triggers=[{", ".join([
                        f"({", ".join(fhex(y, 8) for y in x)})"
                        for x in script.header.triggers
                    ])}],"
                    if index % 3 == 0 or len(script.header.triggers) > 0
                    else ""
                }
                sprite_groups=[{", ".join([fhex(x, 8) for x in script.header.sprite_groups])}],
                sprite_groups_unk1={fhex(script.header.sprite_groups_unk1, 4)},
                palettes=[{", ".join([fhex(x, 8) for x in script.header.palettes])}],
                palettes_unk1={fhex(script.header.palettes_unk1, 4)},
                particle_effects=[{", ".join([fhex(x, 4) for x in script.header.particle_effects])}],
                visual_effects=[{", ".join([fhex(x, 4) for x in script.header.visual_effects])}],
                actors=[{", ".join([
                    f"({", ".join([fhex(y, 8) for y in x])})"
                    for x in script.header.actors
                ])}],
                array5=[{", ".join([fhex(x, 8) for x in script.header.array5])}],

                index=script_index,
            )"""
        )
    )
    if script.header.post_table_subroutine != mnllib.Subroutine([]):
        output.write("\n\n\n")
        decompile_subroutine(
            manager,
            script.header.post_table_subroutine,
            chunk_triple,
            index,
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
            chunk_triple,
            index,
            subroutine_offsets,
            debug_message_offsets,
            add_offsets,
            i,
            output,
        )

    room_id = index // 3
    if chunk_triple[2] is not None and index % 3 == 0:
        outputted_separator = False

        if DecompilerGlobals.next_text_entry_index[room_id] != 0:
            for text_entry_index in range(
                DecompilerGlobals.next_text_entry_index[room_id],
                len(
                    typing.cast(
                        mnllib.bis.TextTable,
                        chunk_triple[2].text_tables[next(iter(LANGUAGE_IDS.values()))],
                    ).entries
                ),
            ):
                if not outputted_separator:
                    output.write("\n\n")
                    outputted_separator = True
                output.write(
                    f"\nemit_text_entry({decompile_text_entry(
                        chunk_triple[2],
                        text_entry_index,
                        implicit_text_entry_definition=True
                    )})  # {fhex(text_entry_index, 2)}"
                )

        language_table_size = len(chunk_triple[2].to_bytes())
        for i, text_table in enumerate(chunk_triple[2].text_tables):
            # if i == PADDING_TEXT_TABLE_ID:
            #     if not isinstance(text_table, bytes) or not (
            #         len(text_table) <= 1
            #         or (len(set(text_table)) == 1 and text_table[0] == 0x00)
            #     ):
            #         warnings.warn(
            #             f"Text table {fhex(i, 2)} {
            #                 f"for room {fhex(index // 3, 4)} "
            #                 if index is not None
            #                 else ""
            #             }does not consist solely of null bytes, but is rather: {
            #                 repr(text_table)
            #             }",
            #             MnLScriptWarning,
            #         )
            #     continue
            if (
                i == mnllib.bis.FEVENT_PADDING_TEXT_TABLE_ID
                and (
                    text_table is None
                    or (
                        isinstance(text_table, bytes)
                        and (
                            len(text_table) <= 1
                            or (len(set(text_table)) == 1 and text_table[0] == 0x00)
                        )
                    )
                )
                and (len(text_table) if text_table is not None else 0)
                == (
                    -(
                        language_table_size
                        - (len(text_table) if text_table is not None else 0)
                        + 1
                    )
                    % mnllib.bis.LANGUAGE_TABLE_ALIGNMENT
                )
                + 1
            ):
                continue

            if isinstance(text_table, mnllib.bis.TextTable):
                if not (
                    0x44 <= i <= 0x48
                    and DecompilerGlobals.next_text_entry_index[room_id] != 0
                ):
                    if not outputted_separator:
                        output.write("\n")
                        outputted_separator = True
                    output.write(
                        f"\n\nemit_text_table({fhex(i, 2)}, [\n{
                            "\n".join([f"    {x!r}," for x in text_table.entries])
                        }\n], is_dialog=True, textbox_sizes={pprint.pformat(
                            text_table.textbox_sizes, indent=4, compact=True
                        )})"
                    )
            elif isinstance(text_table, bytes):
                if len(set(text_table)) == 1 and len(text_table) > 1:
                    formatted_text_table = f"{text_table[0:1]!r} * {len(text_table)}"
                else:
                    formatted_text_table = repr(text_table)
                if not outputted_separator:
                    output.write("\n")
                    outputted_separator = True
                output.write(
                    f"\n\nemit_text_table({fhex(i, 2)}, {formatted_text_table})"
                )
            elif text_table is None and i == mnllib.bis.FEVENT_PADDING_TEXT_TABLE_ID:
                if not outputted_separator:
                    output.write("\n")
                    outputted_separator = True
                output.write(f"\n\nemit_text_table({fhex(i, 2)}, {text_table!r})")
            else:
                continue

    output.write("\n")


def process_script(
    args: DecompilerArguments,
    fevent_scripts_dir: pathlib.Path,
    scripts_casefolded: list[str],
    fevent_manager: mnllib.bis.FEventScriptManager,
    index_and_chunk_triple: tuple[int, mnllib.bis.FEventChunkTriple, int],
) -> None:
    room_id, chunk_triple, triple_index = index_and_chunk_triple
    chunk = chunk_triple[triple_index]
    if not isinstance(chunk, mnllib.bis.FEventScript):
        return

    script_name = f"{room_id:04x}{"_enemies" if triple_index == 1 else ""}"
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

    script_index = room_id * 3 + triple_index
    with (
        path.open("w", encoding="utf-8") if not args.stdout else io.StringIO()
    ) as output:
        decompile_script(
            fevent_manager,
            chunk,
            chunk_triple,
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
    argp = create_decompiler_argument_parser("Mario & Luigi: Bowser's Inside Story")
    args = argp.parse_args(namespace=DecompilerArguments())

    fevent_manager = mnllib.bis.FEventScriptManager(data_dir=args.data_dir)

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
                ),
                (
                    (room_id, chunk_triple, triple_index)
                    for room_id, chunk_triple in enumerate(fevent_manager.fevent_chunks)
                    for triple_index in range(2)
                ),
                chunksize=1000,
            ),
            total=len(fevent_manager.fevent_chunks) * 2,
        ):
            pass


if __name__ == "__main__":
    main()
