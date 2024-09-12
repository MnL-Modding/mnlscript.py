import collections
import typing

import mnllib


class Globals:
    text_tables: collections.defaultdict[
        int, dict[int, mnllib.TextTable | bytes | None]
    ] = collections.defaultdict(dict)

    fevent_manager: mnllib.FEventScriptManager = typing.cast(
        mnllib.FEventScriptManager, None
    )
