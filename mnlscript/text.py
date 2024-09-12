import types
import typing

from dynamicscope import DYNAMIC_SCOPE

import mnllib

from .globals import Globals
from .utils import fhex


LanguageName: typing.TypeAlias = typing.Literal["en", "fr", "de", "it", "es"]
LANGUAGE_IDS: dict[LanguageName, int] = {
    "en": 0x44,
    "fr": 0x45,
    "de": 0x46,
    "it": 0x47,
    "es": 0x48,
}
DEFAULT_LANGUAGE: LanguageName = "en"


TT = typing.TypeVar("TT", bytes, None)


@typing.overload
def emit_text_table(  # pyright: ignore [reportOverlappingOverload]
    text_table_id: int, text_table: TT, *, room_id: int | None = None
) -> TT: ...


@typing.overload
def emit_text_table(  # pyright: ignore [reportOverlappingOverload]
    text_table_id: int,
    *args: typing.Any,
    room_id: int | None = None,
    **kwargs: typing.Any,
) -> mnllib.TextTable: ...


def emit_text_table(
    text_table_id: int,
    *args: typing.Any,
    room_id: int | None = None,
    **kwargs: typing.Any,
) -> mnllib.TextTable | bytes | None:
    if room_id is None:
        room_id = typing.cast(int, DYNAMIC_SCOPE.script_index) // 3

    if len(args) > 0 and isinstance(args[0], (bytes, types.NoneType)):
        text_table: mnllib.TextTable | bytes | None = args[0]
    else:
        text_table = mnllib.TextTable(*args, **kwargs)
    Globals.text_tables[room_id][text_table_id] = text_table
    return text_table


class TextEntryDefinition(typing.NamedTuple):
    text: str
    textbox_size: tuple[int, int]


@typing.overload
def emit_text_entry(
    text: str, /, textbox_size: tuple[int, int], *, room_id: int | None = None
) -> None: ...


@typing.overload
def emit_text_entry(
    entry: dict[LanguageName, TextEntryDefinition], /, *, room_id: int | None = None
) -> None: ...


def emit_text_entry(
    entry: str | dict[LanguageName, TextEntryDefinition],
    /,
    textbox_size: tuple[int, int] | None = None,
    *,
    room_id: int | None = None,
) -> None:
    if room_id is None:
        room_id = typing.cast(int, DYNAMIC_SCOPE.script_index) // 3

    if isinstance(entry, str) and textbox_size is None:
        raise TypeError("textbox_size must not be None if entry is a str")

    for language_name, language_id in LANGUAGE_IDS.items():
        if isinstance(entry, dict):
            current_language_entry = entry.get(language_name, entry[DEFAULT_LANGUAGE])
        else:
            current_language_entry = TextEntryDefinition(
                entry, typing.cast(tuple[int, int], textbox_size)
            )

        if language_id not in Globals.text_tables[room_id]:
            Globals.text_tables[room_id][language_id] = mnllib.TextTable(
                [], is_dialog=True, textbox_sizes=[]
            )  # TODO: is_dialog
        text_table = Globals.text_tables[room_id][language_id]
        if not isinstance(text_table, mnllib.TextTable):
            raise TypeError(
                f"emit_text_entry() text table for room {fhex(room_id, 4)} with "
                f"language ID {fhex(language_id, 2)} must be an mnllib.TextTable, "
                f"not '{type(text_table).__name__}'"
            )
        text_table.entries.append(
            current_language_entry.text.encode(mnllib.MNL_ENCODING)
        )
        if text_table.textbox_sizes is not None:
            text_table.textbox_sizes.append(current_language_entry.textbox_size)
