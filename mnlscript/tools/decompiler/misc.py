import enum
import typing

import more_itertools
import mnllib

from ...text import LANGUAGE_IDS
from ...utils import fhex


T = typing.TypeVar("T")


def decompile_enum(
    enum_type: type[enum.Enum],
    value: T,
    unknown_formatter: typing.Callable[[T], str] = repr,
) -> str:
    try:
        return f"{enum_type.__name__}.{enum_type(value).name}"
    except ValueError:
        return unknown_formatter(value)


def decompile_variable(variable: mnllib.Variable) -> str:
    return f"Variables[{fhex(variable.number, 4)}]"


def decompile_const_or_variable(
    value: int | mnllib.Variable,
    const_formatter: typing.Callable[[int], str] = repr,
) -> str:
    if isinstance(value, mnllib.Variable):
        return decompile_variable(value)
    return const_formatter(value)


def decompile_bool_int_or_variable(
    value: int | mnllib.Variable, int_formatter: typing.Callable[[int], str] = repr
) -> str:
    if value in [0, 1]:
        return repr(bool(value))
    return decompile_const_or_variable(value, const_formatter=int_formatter)


def decompile_text(value: bytes) -> str:
    return (
        repr(value.decode(mnllib.MNL_ENCODING, errors="backslashreplace"))
        .replace("\\\\", "\\")
        .replace("\xff", "\\xff")
    )


def decompile_text_entry(
    language_table: mnllib.LanguageTable,
    text_entry_index: int,
    implicit_text_entry_definition: bool = False,
) -> str:
    def combined_entries_and_textbox_sizes(
        language_id: int,
    ) -> tuple[bytes, tuple[int, int]]:
        text_table = typing.cast(
            mnllib.TextTable, language_table.text_tables[language_id]
        )
        return (
            text_table.entries[text_entry_index],
            typing.cast(list[tuple[int, int]], text_table.textbox_sizes)[
                text_entry_index
            ],
        )

    if more_itertools.all_equal(
        map(combined_entries_and_textbox_sizes, LANGUAGE_IDS.values())
    ):
        text_table = typing.cast(
            mnllib.TextTable,
            language_table.text_tables[next(iter(LANGUAGE_IDS.values()))],
        )
        return f"{"" if implicit_text_entry_definition else "TextEntryDefinition("}{
            decompile_text(text_table.entries[text_entry_index])
        }, {
            typing.cast(list[tuple[int, int]], text_table.textbox_sizes)[
                text_entry_index
            ]!r}{"" if implicit_text_entry_definition else ")"}"
    else:
        text_entries: list[str] = []
        for language_name, language_id in LANGUAGE_IDS.items():
            text_table = typing.cast(
                mnllib.TextTable,
                language_table.text_tables[language_id],
            )
            text_entries.append(
                f"    {repr(language_name)}: TextEntryDefinition({
                    decompile_text(text_table.entries[text_entry_index])
                }, {
                    typing.cast(list[tuple[int, int]], text_table.textbox_sizes)[
                        text_entry_index
                    ]!r}),"
            )
        return f"{"{"}\n{"\n".join(text_entries)}\n{"}"}"
