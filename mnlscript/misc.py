import types
import typing

from dynamicscope import DYNAMIC_SCOPE
import mnllib

from .commands import return_


class MnLScriptWarning(UserWarning):
    pass


class FEventInitModule(types.ModuleType):
    pass


class FEventScriptModule(types.ModuleType):
    script_index: int
    subroutines: list[mnllib.Subroutine]

    header: mnllib.FEventScriptHeader


class SubroutineCallable(typing.Protocol):
    def __call__(self, *, sub: mnllib.Subroutine) -> None: ...


def subroutine(
    *,
    post_table: bool = False,
    no_return: bool = False,
    footer: bytes = b"",
    subs: list[mnllib.Subroutine] | None = None,
    hdr: mnllib.FEventScriptHeader | None = None,
) -> typing.Callable[[SubroutineCallable], mnllib.Subroutine]:
    if subs is None:
        subs = typing.cast(list[mnllib.Subroutine], DYNAMIC_SCOPE.subroutines)
    if hdr is None:
        hdr = typing.cast(mnllib.FEventScriptHeader, DYNAMIC_SCOPE.header)

    def decorator(function: SubroutineCallable) -> mnllib.Subroutine:
        subroutine = mnllib.Subroutine([], footer)

        function(sub=subroutine)

        if not no_return:
            return_(subroutine=subroutine)

        if post_table:
            hdr.post_table_subroutine = subroutine
        else:
            subs.append(subroutine)

        return subroutine

    return decorator
