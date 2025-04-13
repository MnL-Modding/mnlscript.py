import struct
import sys
import importlib.abc
import importlib.machinery
import importlib.util
import typing

import mnllib.bis

from ...bis.globals import Globals
from ...bis.misc import FEventInitModule, FEventScriptModule
from ...consts import INIT_SCRIPT_FILENAME
from ...globals import CommonGlobals
from ...script import SubroutineExt, update_commands_with_offsets
from ..consts import FEVENT_SCRIPT_FILENAME_REGEX, FEVENT_SCRIPTS_DIR
from .misc import CompilerArguments, create_compiler_argument_parser


def main() -> None:
    argp = create_compiler_argument_parser("Mario & Luigi: Bowser's Inside Story")
    args = argp.parse_args(namespace=CompilerArguments())

    Globals.fevent_manager = mnllib.bis.FEventScriptManager(data_dir=args.data_dir)
    CommonGlobals.script_manager = Globals.fevent_manager

    fevent_scripts_dir = args.scripts_dir / FEVENT_SCRIPTS_DIR

    for module_dir in [args.scripts_dir, fevent_scripts_dir]:
        init_path = module_dir / INIT_SCRIPT_FILENAME
        if init_path.is_file():
            init_module_name = ".".join(
                init_path.relative_to(args.scripts_dir.parent).parent.parts
            )
            init_spec = typing.cast(
                importlib.machinery.ModuleSpec,
                importlib.util.spec_from_file_location(init_module_name, init_path),
            )
            init_module = typing.cast(
                FEventInitModule, importlib.util.module_from_spec(init_spec)
            )
            sys.modules[init_module_name] = init_module
            typing.cast(importlib.abc.Loader, init_spec.loader).exec_module(init_module)

    for path in sorted(fevent_scripts_dir.iterdir()):
        if not path.is_file():
            continue
        if len(args.scripts) > 0 and not any(path.samefile(x) for x in args.scripts):
            continue
        match = FEVENT_SCRIPT_FILENAME_REGEX.fullmatch(path.name)
        if match is None:
            continue
        room_id = int(match.group(1), base=16)
        script_type = match.group(2)
        triple_index = 1 if script_type == "enemies" else 0

        module_name = ".".join(
            path.with_suffix("").relative_to(args.scripts_dir.parent).parts
        )
        spec = typing.cast(
            importlib.machinery.ModuleSpec,
            importlib.util.spec_from_file_location(module_name, path),
        )
        module = typing.cast(FEventScriptModule, importlib.util.module_from_spec(spec))
        module.script_index = room_id * 3 + triple_index
        module.subroutines = []
        module.debug_messages = []
        sys.modules[module_name] = module
        print(module, file=sys.stderr)
        typing.cast(importlib.abc.Loader, spec.loader).exec_module(module)

        post_table_subroutine_ext = typing.cast(
            SubroutineExt, module.header.post_table_subroutine
        )
        if not hasattr(post_table_subroutine_ext, "name"):
            post_table_subroutine_ext.name = "sub_post_table"
        module.header.subroutine_table = [0] * len(module.subroutines)
        update_commands_with_offsets(
            [module.header.post_table_subroutine, *module.subroutines],
            len(module.header.to_bytes(Globals.fevent_manager)),
        )
        script = mnllib.bis.FEventScript(
            module.header,
            module.subroutines,
            module.debug_messages,
            module.script_index,
        )
        if args.stdout:
            script_bytes = script.to_bytes(Globals.fevent_manager)
            sys.stdout.buffer.write(
                struct.pack("=hI", module.script_index, len(script_bytes))
            )
            sys.stdout.buffer.write(script_bytes)
        chunk_triple = list(Globals.fevent_manager.fevent_chunks[room_id])
        chunk_triple[triple_index] = script
        chunk_triple[2] = None
        Globals.fevent_manager.fevent_chunks[room_id] = typing.cast(
            mnllib.bis.FEventChunkTriple, tuple(chunk_triple)
        )

    for room_id, language_table_dict in Globals.text_tables.items():
        language_table = Globals.fevent_manager.fevent_chunks[room_id][2]
        if language_table is None:
            language_table = mnllib.bis.LanguageTable([], room_id)
            Globals.fevent_manager.fevent_chunks[room_id] = (
                Globals.fevent_manager.fevent_chunks[room_id][:2] + (language_table,)
            )

        for text_table_id, text_table in language_table_dict.items():
            language_table.text_tables.extend(
                [None] * (text_table_id - len(language_table.text_tables) + 1)
            )
            language_table.text_tables[text_table_id] = text_table

        if len(language_table.text_tables) <= mnllib.bis.FEVENT_PADDING_TEXT_TABLE_ID:
            language_table.text_tables.extend(
                [None]
                * (
                    mnllib.bis.FEVENT_PADDING_TEXT_TABLE_ID
                    - len(language_table.text_tables)
                )
            )
            language_table.text_tables.append(b"")
            language_table_size = len(language_table.to_bytes())
            language_table.text_tables[mnllib.bis.FEVENT_PADDING_TEXT_TABLE_ID] = (
                b"\x00"
                * (
                    (-(language_table_size + 1) % mnllib.bis.LANGUAGE_TABLE_ALIGNMENT)
                    + 1
                )
            )

        if args.stdout:
            language_table_bytes = language_table.to_bytes()
            sys.stdout.buffer.write(
                struct.pack("=hI", room_id * 3 + 2, len(language_table_bytes))
            )
            sys.stdout.buffer.write(language_table_bytes)

    if args.stdout:
        return
    print("Saving...", file=sys.stderr)
    Globals.fevent_manager.save_all(data_dir=args.data_dir)


if __name__ == "__main__":
    main()
