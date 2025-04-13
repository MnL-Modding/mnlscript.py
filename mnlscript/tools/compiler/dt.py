import importlib.abc
import importlib.machinery
import importlib.util
import struct
import sys
import typing
import warnings

import bidict
import mnllib.dt
import mnllib.n3ds
import pymsbmnl

from ...consts import INIT_SCRIPT_FILENAME
from ...dt.globals import Globals
from ...dt.misc import FEventInitModule, FEventScriptModule
from ...dt.sound import load_sound_names
from ...globals import CommonGlobals
from ...misc import MnLScriptWarning
from ...script import SubroutineExt, update_commands_with_offsets
from ..consts import FEVENT_SCRIPT_FILENAME_REGEX, FEVENT_SCRIPTS_DIR
from .misc import CompilerArguments, create_compiler_argument_parser


class DTCompilerArguments(CompilerArguments):
    no_text: bool


def main() -> None:
    argp = create_compiler_argument_parser("Mario & Luigi: Dream Team (Bros.)")
    argp.add_argument(
        "-t",
        "--no-text",
        help="skip loading and saving the text chunks",
        action="store_true",
    )
    args = argp.parse_args(namespace=DTCompilerArguments())

    sound_data_path = mnllib.n3ds.fs_std_romfs_path(
        mnllib.dt.SOUND_DATA_PATH, data_dir=args.data_dir
    )
    try:
        Globals.sound_names = bidict.bidict(load_sound_names(sound_data_path))
    except FileNotFoundError:
        warnings.warn(
            f"'{sound_data_path}' is missing, continuing without sound names!",
            MnLScriptWarning,
        )

    Globals.fevent_manager = mnllib.dt.FEventScriptManager(
        data_dir=args.data_dir, parse_all=False
    )
    CommonGlobals.script_manager = Globals.fevent_manager

    message_dir = mnllib.n3ds.fs_std_romfs_path(
        mnllib.dt.MESSAGE_DIR_PATH, data_dir=args.data_dir
    )
    for message_file_path in sorted(message_dir.glob("*/FMes.dat")):
        language = message_file_path.parent.name
        if len(args.scripts) > 0 and not args.no_text:
            with (
                message_file_path.open("rb") as message_file,
                message_file_path.with_suffix(".bin").open("rb") as offset_table,
            ):
                Globals.text_chunks[language] = dict(
                    enumerate(
                        mnllib.dt.read_msbt_archive(
                            message_file, offset_table, language
                        )
                    )
                )
        else:
            Globals.text_chunks[language] = {}

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
        pair_index = 1 if script_type == "enemies" else 0

        if pair_index == 0:
            for language, text_chunks in Globals.text_chunks.items():
                text_chunks[room_id] = pymsbmnl.LMSDocument(
                    lambda: mnllib.dt.DTLMSAdapter(language)
                )
        module_name = ".".join(
            path.with_suffix("").relative_to(args.scripts_dir.parent).parts
        )
        spec = typing.cast(
            importlib.machinery.ModuleSpec,
            importlib.util.spec_from_file_location(module_name, path),
        )
        module = typing.cast(FEventScriptModule, importlib.util.module_from_spec(spec))
        module.script_index = room_id * 2 + pair_index
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
        if module.header.init_subroutine is None and len(module.subroutines) <= 0:
            module.header.init_subroutine = 0
        module.header.subroutine_table = [0] * len(module.subroutines)
        update_commands_with_offsets(
            [module.header.post_table_subroutine, *module.subroutines],
            len(module.header.to_bytes(Globals.fevent_manager)),
        )
        script = mnllib.dt.FEventScript(
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
        chunk_pair = list(Globals.fevent_manager.fevent_scripts[room_id])
        chunk_pair[pair_index] = script
        Globals.fevent_manager.fevent_scripts[room_id] = typing.cast(
            mnllib.dt.FEventScriptPair, tuple(chunk_pair)
        )

    if args.stdout:
        return
    print("Saving...", file=sys.stderr)

    Globals.fevent_manager.save_all(data_dir=args.data_dir)

    if not args.no_text:
        for language, text_chunks in Globals.text_chunks.items():
            default_chunk = pymsbmnl.LMSDocument(
                lambda: mnllib.dt.DTLMSAdapter(language)
            )
            text_chunks_list = [
                text_chunks.get(i, default_chunk)
                for i in range(mnllib.dt.FMES_NUMBER_OF_CHUNKS)
            ]
            with (
                (message_dir / language / "FMes.dat").open("wb") as message_file,
                (message_dir / language / "FMes.bin").open("wb") as offset_table,
            ):
                mnllib.dt.write_msbt_archive(
                    text_chunks_list, message_file, offset_table
                )


if __name__ == "__main__":
    main()
