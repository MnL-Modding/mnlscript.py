import typing

import mnllib.bis
import more_itertools

from ....bis.text import LANGUAGE_IDS


def decompile_text(value: bytes) -> str:
    return (
        repr(value.decode(mnllib.bis.BIS_ENCODING, errors="backslashreplace"))
        .replace("\\\\", "\\")  # TODO
        .replace("\xff", "\\xff")
    )


def decompile_text_entry(
    language_table: mnllib.bis.LanguageTable,
    text_entry_index: int,
    implicit_text_entry_definition: bool = False,
) -> str:
    def combined_entries_and_textbox_sizes(
        language_id: int,
    ) -> tuple[bytes, tuple[int, int]]:
        text_table = typing.cast(
            mnllib.bis.TextTable, language_table.text_tables[language_id]
        )
        return (
            text_table.entries[text_entry_index],
            typing.cast(list[tuple[int, int]], text_table.textbox_sizes)[
                text_entry_index
            ],
        )

    if more_itertools.all_equal(
        LANGUAGE_IDS.values(),
        key=combined_entries_and_textbox_sizes,
    ):
        text_table = typing.cast(
            mnllib.bis.TextTable,
            language_table.text_tables[next(iter(LANGUAGE_IDS.values()))],
        )
        return f"{"" if implicit_text_entry_definition else "TextEntryDefinition("}{
            decompile_text(text_table.entries[text_entry_index])
        }, {
            typing.cast(list[tuple[int, int]], text_table.textbox_sizes)[
                text_entry_index
            ]!r}{"" if implicit_text_entry_definition else ")"}"

    text_entries: list[str] = []
    for language_name, language_id in LANGUAGE_IDS.items():
        text_table = typing.cast(
            mnllib.bis.TextTable,
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
