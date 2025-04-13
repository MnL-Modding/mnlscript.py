import itertools
import typing

from dynamicscope import DYNAMIC_SCOPE
import mnllib.dt
import pymsbmnl

from ..utils import fhex
from .globals import Globals


DEFAULT_LANGUAGES = ["US_English", "EU_English", "JP_Japanese", "KR_Korean"]


def create_text_entry(
    text: str,
    style: int = mnllib.dt.DEFAULT_MESSAGE_STYLE,
    attributes: dict[str, typing.Any] | None = None,
) -> pymsbmnl.LMSMessage:
    message = pymsbmnl.LMSMessage(text)
    message.style = style
    message.attributes = (
        attributes
        if attributes is not None
        else mnllib.dt.DEFAULT_MESSAGE_ATTRIBUTES.copy()
    )
    return message


def emit_text_chunk(
    language: str,
    chunk: pymsbmnl.LMSDocument,
    *,
    room_id: int | None = None,
) -> pymsbmnl.LMSDocument:
    if room_id is None:
        room_id = typing.cast(int, DYNAMIC_SCOPE.script_index) // 2

    Globals.text_chunks[language][room_id] = chunk
    return chunk


@typing.overload
def emit_text_entry(
    text: str,
    /,
    style: int | None = None,
    attributes: dict[str, typing.Any] | None = None,
    *,
    room_id: int | None = None,
) -> int | None: ...
@typing.overload
def emit_text_entry(
    entry: pymsbmnl.LMSMessage | dict[str, str | pymsbmnl.LMSMessage],
    /,
    *,
    room_id: int | None = None,
) -> int | None: ...


def emit_text_entry(
    entry: str | pymsbmnl.LMSMessage | dict[str, str | pymsbmnl.LMSMessage],
    /,
    style: int | None = None,
    attributes: dict[str, typing.Any] | None = None,
    *,
    room_id: int | None = None,
) -> int | None:
    if room_id is None:
        room_id = typing.cast(int, DYNAMIC_SCOPE.script_index) // 2

    text_entry_index: int | None = None
    for language, chunks in Globals.text_chunks.items():
        chunk = chunks[room_id]

        if text_entry_index is None:
            text_entry_index = len(chunk.messages)
        elif len(chunk.messages) != text_entry_index:
            raise ValueError(
                "all languagues' text chunks must have the same length for "
                f"emit_text_entry() but chunk '{language}' of room {fhex(room_id, 4)} "
                f"has a length of {len(chunk.messages)} instead of {text_entry_index}"
            )

        if isinstance(entry, dict):
            for current_language in itertools.chain([language], DEFAULT_LANGUAGES):
                try:
                    current_language_entry = entry[current_language]
                    break
                except KeyError:
                    pass
            else:
                raise KeyError(
                    f"language '{language}' not found in the text entry, and none of "
                    f"the defaults ({DEFAULT_LANGUAGES!r}) are present either"
                )
            if isinstance(current_language_entry, pymsbmnl.LMSMessage):
                chunk.messages.append(current_language_entry)
            else:
                current_language_message = chunk.new_message()
                current_language_message.text = current_language_entry
                if style is not None:
                    current_language_message.style = style
                if attributes is not None:
                    current_language_message.attributes = attributes
        elif isinstance(entry, pymsbmnl.LMSMessage):
            chunk.messages.append(entry)
        else:
            current_language_message = chunk.new_message()
            current_language_message.text = entry
            if style is not None:
                current_language_message.style = style
            if attributes is not None:
                current_language_message.attributes = attributes

    return text_entry_index
