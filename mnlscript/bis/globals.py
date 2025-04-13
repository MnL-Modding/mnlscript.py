import collections
import typing

import mnllib.bis


class Globals:
    fevent_manager: mnllib.bis.FEventScriptManager = typing.cast(
        mnllib.bis.FEventScriptManager, None
    )

    text_tables: collections.defaultdict[
        int, dict[int, mnllib.bis.TextTable | bytes | None]
    ] = collections.defaultdict(dict)
