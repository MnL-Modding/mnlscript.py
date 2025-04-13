import collections

from ....dt.sound import Sound


class DecompilerGlobals:
    sound_names: dict[Sound, str] = {}

    next_text_entry_index: collections.defaultdict[int, int] = collections.defaultdict(
        int
    )
