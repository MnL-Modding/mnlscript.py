import sys
import importlib.abc
import importlib.machinery
import importlib.util
import typing

import mnllib

from ..consts import PADDING_TEXT_TABLE_ID
from ..globals import Globals
from ..misc import FEventInitModule, FEventScriptModule
from .consts import FEVENT_SCRIPT_FILENAME_REGEX, FEVENT_SCRIPTS_DIR


def main() -> None:
    Globals.fevent_manager = mnllib.FEventScriptManager()

    init_path = FEVENT_SCRIPTS_DIR / "__init__.py"
    if init_path.is_file():
        init_module_name = ".".join(init_path.parent.parts)
        init_spec = typing.cast(
            importlib.machinery.ModuleSpec,
            importlib.util.spec_from_file_location(init_module_name, init_path),
        )
        init_module = typing.cast(
            FEventInitModule, importlib.util.module_from_spec(init_spec)
        )
        sys.modules[init_module_name] = init_module
        typing.cast(importlib.abc.Loader, init_spec.loader).exec_module(init_module)

    for path in FEVENT_SCRIPTS_DIR.iterdir():
        if not path.is_file():
            continue
        match = FEVENT_SCRIPT_FILENAME_REGEX.fullmatch(path.name)
        if match is None:
            continue
        room_id = int(match.group(1), base=16)
        triple_index = int(match.group(2) or 0)

        module_name = ".".join(path.with_suffix("").parts)
        spec = typing.cast(
            importlib.machinery.ModuleSpec,
            importlib.util.spec_from_file_location(module_name, path),
        )
        module = typing.cast(FEventScriptModule, importlib.util.module_from_spec(spec))
        module.script_index = room_id * 3 + triple_index
        module.subroutines = []
        sys.modules[module_name] = module
        typing.cast(importlib.abc.Loader, spec.loader).exec_module(module)

        print(module)
        script = mnllib.FEventScript(
            module.header, module.subroutines, module.script_index
        )
        chunk_triple = list(Globals.fevent_manager.fevent_chunks[room_id])
        chunk_triple[triple_index] = script
        if isinstance(chunk_triple[2], mnllib.LanguageTable):
            chunk_triple[2] = None
        Globals.fevent_manager.fevent_chunks[room_id] = typing.cast(
            tuple[
                mnllib.FEventScript | None,
                mnllib.FEventChunk | None,
                mnllib.FEventChunk | None,
            ],
            tuple(chunk_triple),
        )

    for room_id, language_table_dict in Globals.text_tables.items():
        language_table = Globals.fevent_manager.fevent_chunks[room_id][2]
        if language_table is None:
            language_table = mnllib.LanguageTable([], room_id)
            Globals.fevent_manager.fevent_chunks[room_id] = (
                Globals.fevent_manager.fevent_chunks[room_id][:2] + (language_table,)
            )
        elif not isinstance(language_table, mnllib.LanguageTable):
            continue

        for text_table_id, text_table in language_table_dict.items():
            language_table.text_tables.extend(
                [None] * (text_table_id - len(language_table.text_tables) + 1)
            )
            language_table.text_tables[text_table_id] = text_table

        if len(language_table.text_tables) <= PADDING_TEXT_TABLE_ID:
            language_table.text_tables.extend(
                [None] * (PADDING_TEXT_TABLE_ID - len(language_table.text_tables))
            )
            language_table.text_tables.append(b"")
            language_table_size = len(language_table.to_bytes(Globals.fevent_manager))
            language_table.text_tables[PADDING_TEXT_TABLE_ID] = b"\x00" * (
                (-(language_table_size + 1) % mnllib.FEVENT_LANGUAGE_TABLE_ALIGNMENT)
                + 1
            )

    Globals.fevent_manager.save_all()


if __name__ == "__main__":
    main()
