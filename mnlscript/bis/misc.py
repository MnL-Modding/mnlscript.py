import types

import mnllib
import mnllib.bis


class FEventInitModule(types.ModuleType):
    pass


class FEventScriptModule(types.ModuleType):
    script_index: int
    subroutines: list[mnllib.Subroutine]
    debug_messages: list[str]

    header: mnllib.bis.FEventScriptHeader
