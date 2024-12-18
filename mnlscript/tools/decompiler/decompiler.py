import pathlib
import copy
import textwrap
import pprint
import typing

import mnllib

from ...consts import PADDING_TEXT_TABLE_ID
from ...text import LANGUAGE_IDS
from ...utils import fhex
from ..consts import FEVENT_SCRIPTS_DIR
from .command_matchers import decompile_subroutine_commands
from .globals import DecompilerGlobals
from .misc import decompile_text_entry


def decompile_subroutine(
    manager: mnllib.MnLScriptManager,
    subroutine: mnllib.Subroutine,
    chunk_triple: tuple[
        mnllib.FEventScript | None, mnllib.FEventChunk | None, mnllib.FEventChunk | None
    ],
    script_index: int,
    index: int | None,
    output: typing.TextIO,
) -> None:
    processed_subroutine = copy.deepcopy(subroutine)
    has_return = False
    if (
        len(processed_subroutine.commands) > 0
        and processed_subroutine.commands[-1].command_id == 0x0001
    ):
        has_return = True
        del processed_subroutine.commands[-1]

    decorator_args: list[str] = []
    if index is None:
        decorator_args.append("post_table=True")
    if not has_return:
        decorator_args.append("no_return=True")
    if subroutine.footer:
        decorator_args.append(f"footer={subroutine.footer!r}")
    output.write(
        textwrap.dedent(
            f"""\
            @subroutine({", ".join(decorator_args)})
            def sub_{index if index is not None else "post_table"}(sub: Subroutine):
            """
        )
    )

    if len(processed_subroutine.commands) > 0:
        decompile_subroutine_commands(
            manager, processed_subroutine, chunk_triple, script_index, output, " " * 4
        )
    else:
        output.write("    pass")


def decompile_script(
    manager: mnllib.MnLScriptManager,
    script: mnllib.FEventScript,
    chunk_triple: tuple[
        mnllib.FEventScript | None, mnllib.FEventChunk | None, mnllib.FEventChunk | None
    ],
    index: int,
    output: typing.TextIO,
) -> None:
    output.write(
        textwrap.dedent(
            f"""\
            from mnllib import *
            from mnlscript import *


            header = FEventScriptHeader(
                unk_0x00={script.header.unk_0x00!r},
                offsets_unk1={script.header.offsets_unk1!r},
                array1=[{", ".join(fhex(x, 8) for x in script.header.array1)}],
                var1={fhex(script.header.var1, 4)},
                array2=[{", ".join(fhex(x, 8) for x in script.header.array2)}],
                var2={fhex(script.header.var2, 4)},
                array3=[{", ".join(fhex(x, 4) for x in script.header.array3)}],
                section1_unk1={script.header.section1_unk1!r},
                array4=[{", ".join(
                    f"({", ".join(fhex(y, 8) for y in x)})"
                    for x in script.header.array4
                )}],
                array5=[{", ".join(fhex(x, 8) for x in script.header.array5)}],
            )


            """
        )
    )
    if script.header.post_table_subroutine != mnllib.Subroutine([]):  # TODO
        decompile_subroutine(
            manager,
            script.header.post_table_subroutine,
            chunk_triple,
            index,
            None,
            output,
        )
        output.write("\n\n\n")

    for i, subroutine in enumerate(script.subroutines):
        decompile_subroutine(manager, subroutine, chunk_triple, index, i, output)
        if i != len(script.subroutines) - 1:
            output.write("\n\n\n")

    room_id = index // 3
    if isinstance(chunk_triple[2], mnllib.LanguageTable) and script is chunk_triple[0]:
        output.write("\n")

        if DecompilerGlobals.next_text_entry_index[room_id] != 0:
            first = True
            for text_entry_index in range(
                DecompilerGlobals.next_text_entry_index[room_id],
                len(
                    typing.cast(
                        mnllib.TextTable,
                        chunk_triple[2].text_tables[next(iter(LANGUAGE_IDS.values()))],
                    ).entries
                ),
            ):
                if first:
                    output.write("\n")
                    first = False
                output.write(
                    f"\nemit_text_entry({decompile_text_entry(
                        chunk_triple[2],
                        text_entry_index,
                        implicit_text_entry_definition=True
                    )})  # {fhex(text_entry_index, 2)}"
                )

        language_table_size = len(chunk_triple[2].to_bytes(manager))
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
                i == PADDING_TEXT_TABLE_ID
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
                    % mnllib.FEVENT_LANGUAGE_TABLE_ALIGNMENT
                )
                + 1
            ):
                continue

            if isinstance(text_table, mnllib.TextTable):
                if not (
                    0x44 <= i <= 0x48
                    and DecompilerGlobals.next_text_entry_index[room_id] != 0
                ):
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
                output.write(
                    f"\n\nemit_text_table({fhex(i, 2)}, {formatted_text_table})"
                )
            elif text_table is None and i == PADDING_TEXT_TABLE_ID:
                output.write(f"\n\nemit_text_table({fhex(i, 2)}, {text_table!r})")
            else:
                continue

    output.write("\n")


def main() -> None:
    fevent_manager = mnllib.FEventScriptManager()

    FEVENT_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    (FEVENT_SCRIPTS_DIR / "__init__.py").touch()

    for room_id, chunk_triple in enumerate(fevent_manager.fevent_chunks):
        for i, chunk in enumerate(chunk_triple):
            if not isinstance(chunk, mnllib.FEventScript):
                continue
            path = pathlib.Path(
                FEVENT_SCRIPTS_DIR, f"{room_id:04x}{f"_{i}" if i != 0 else ""}.py"
            )
            # if path.exists():  # TODO
            #     continue
            with path.open("w") as file:
                decompile_script(
                    fevent_manager, chunk, chunk_triple, room_id * 3 + i, file
                )


if __name__ == "__main__":
    main()
