import collections


class DecompilerGlobals:
    next_text_entry_index: collections.defaultdict[int, int] = collections.defaultdict(
        int
    )
