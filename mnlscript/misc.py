import types

import mnllib


class MnLScriptWarning(UserWarning):
    pass


class FEventInitModule(types.ModuleType):
    pass


class FEventScriptModule(types.ModuleType):
    script_index: int
    subroutines: list[mnllib.Subroutine]

    header: mnllib.FEventScriptHeader
