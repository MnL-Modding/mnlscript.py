import enum
import typing

import mnllib.dt
import more_itertools
import pymsbmnl

from ....dt.consts import Sounds, TextboxSoundsPreset
from ....dt.misc import TextboxSounds
from ....dt.sound import Sound
from ....utils import fhex
from ..misc import (
    decompile_const_or_f32_or_variable,
    decompile_enum,
)
from .globals import DecompilerGlobals


class CreateCallCondition(enum.IntEnum):
    NEVER = 1
    WHEN_NECESSARY = 2
    ALWAYS = 3


def decompile_sound_only(value: Sound) -> str:
    try:
        return repr(DecompilerGlobals.sound_names[value])
    except KeyError:
        return f"Sound({value.bank}, {fhex(value.sound_id, 4)})"


def decompile_sound(value: Sound | int, bank_shift: int = 24) -> str:
    if isinstance(value, int):
        value = Sound(value >> bank_shift, value & ((1 << bank_shift) - 1))

    return decompile_enum(
        Sounds,
        value,
        decompile_sound_only,
    )


def decompile_textbox_sounds(
    normal: Sound | int | float | mnllib.Variable,
    fast_forwarded: Sound | int | float | mnllib.Variable,
    *,
    bank_shift: int = 16,
    force_parentheses: bool = True,
) -> str:
    if isinstance(normal, (Sound, int)) and isinstance(fast_forwarded, (Sound, int)):
        if isinstance(normal, int):
            normal = Sound(normal >> bank_shift, normal & ((1 << bank_shift) - 1))
        if isinstance(fast_forwarded, int):
            fast_forwarded = Sound(
                fast_forwarded >> bank_shift, fast_forwarded & ((1 << bank_shift) - 1)
            )

        try:
            return f"TextboxSoundsPreset.{
                typing.cast(
                    typing.Callable[[TextboxSounds], TextboxSoundsPreset],
                    TextboxSoundsPreset,
                )(TextboxSounds(normal, fast_forwarded)).name
            }"
        except ValueError:
            pass

    return f"{"(" if force_parentheses else ""}{
        decompile_const_or_f32_or_variable(
            normal,
            lambda value: decompile_sound(value, bank_shift=bank_shift),
        )
    }, {
        decompile_const_or_f32_or_variable(
            fast_forwarded,
            lambda value: decompile_sound(value, bank_shift=bank_shift),
        )
    }{")" if force_parentheses else ""}"


def decompile_text_entry_single_language(
    text_entry: pymsbmnl.LMSMessage,
    create_call_condition: CreateCallCondition = CreateCallCondition.WHEN_NECESSARY,
) -> str:
    non_default_style = text_entry.style != mnllib.dt.DEFAULT_MESSAGE_STYLE
    non_default_attributes = text_entry.attributes != typing.cast(
        dict[str, int], mnllib.dt.DEFAULT_MESSAGE_ATTRIBUTES
    )
    write_create_call = create_call_condition == CreateCallCondition.ALWAYS or (
        create_call_condition == CreateCallCondition.WHEN_NECESSARY
        and (non_default_style or non_default_attributes)
    )
    return f"{"create_text_entry(" if write_create_call else ""}{
        repr(text_entry.text)
        }{
            f", style={decompile_enum(mnllib.dt.MessageStyle, text_entry.style)}"
            if non_default_style
            else ""
        }{
            f", attributes={text_entry.attributes!r}"
            if non_default_attributes
            else ""
        }{")" if write_create_call else ""}"


def decompile_text_entry(
    text_chunks: dict[str, pymsbmnl.LMSDocument],
    text_entry_index: int,
    create_call_condition: CreateCallCondition = CreateCallCondition.WHEN_NECESSARY,
) -> str:
    if more_itertools.all_equal(
        text_chunks.values(), key=lambda chunk: chunk.messages[text_entry_index]
    ):
        text_entry = next(iter(text_chunks.values())).messages[text_entry_index]
        return decompile_text_entry_single_language(
            text_entry,
            create_call_condition=create_call_condition,
        )

    text_entries = [
        f"    {repr(language)}: {
            decompile_text_entry_single_language(
                chunk.messages[text_entry_index],
                create_call_condition=max(
                    create_call_condition, CreateCallCondition.WHEN_NECESSARY
                ),
            )
        },"
        for language, chunk in text_chunks.items()
    ]
    return f"{"{"}\n{"\n".join(text_entries)}\n{"}"}"
