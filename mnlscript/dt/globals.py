import typing

import bidict
import mnllib
import mnllib.dt
import pymsbmnl

from .sound import Sound


class Globals:
    sound_names: bidict.bidict[Sound, str] = bidict.bidict()
    fevent_manager: mnllib.dt.FEventScriptManager = typing.cast(
        mnllib.dt.FEventScriptManager, None
    )

    text_chunks: dict[str, dict[int, pymsbmnl.LMSDocument]] = {}
