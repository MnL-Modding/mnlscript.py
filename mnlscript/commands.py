import functools
import typing

from dynamicscope import DYNAMIC_SCOPE
import mnllib
import mnllib.bis
import mnllib.dt

from .globals import CommonGlobals
from .script import CodeCommandWithOffsets, SubroutineExt
from .utils import fhex


class SubroutineCallable(typing.Protocol):
    __name__: str

    def __call__(self, *, sub: mnllib.Subroutine) -> None: ...


def subroutine(
    *,
    post_table: bool = False,
    init: bool = False,
    no_return: bool = False,
    footer: bytes = b"",
    subs: list[mnllib.Subroutine] | None = None,
    hdr: mnllib.bis.FEventScriptHeader | mnllib.dt.FEventScriptHeader | None = None,
) -> typing.Callable[[SubroutineCallable], mnllib.Subroutine]:
    rsubs = (
        subs
        if subs is not None
        else typing.cast(list[mnllib.Subroutine], DYNAMIC_SCOPE.subroutines)
    )
    rhdr = (
        hdr
        if hdr is not None
        else typing.cast(
            mnllib.bis.FEventScriptHeader | mnllib.dt.FEventScriptHeader,
            DYNAMIC_SCOPE.header,
        )
    )

    def decorator(function: SubroutineCallable) -> mnllib.Subroutine:
        subroutine = mnllib.Subroutine([], footer)
        subroutine_ext = typing.cast(SubroutineExt, subroutine)
        subroutine_ext.name = function.__name__

        function(sub=subroutine)

        if not no_return:
            return_(subroutine=subroutine)

        if post_table:
            if init:
                raise ValueError(
                    "the post-table subroutine can't be the init subroutine"
                )
            rhdr.post_table_subroutine = subroutine
        else:
            rsubs.append(subroutine)

        if init:
            if rhdr.init_subroutine is not None:
                raise ValueError(
                    f"the init suboutine is already set to {fhex(rhdr.init_subroutine)}"
                )
            rhdr.init_subroutine = len(rsubs) - 1

        return subroutine

    return decorator


def command_emitter[T, **P]() -> (
    typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]
):
    def decorator(function: typing.Callable[P, T]) -> typing.Callable[P, T]:
        @functools.wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if kwargs.get("subroutine") is None:
                kwargs["subroutine"] = typing.cast(mnllib.Subroutine, DYNAMIC_SCOPE.sub)
            return function(*args, **kwargs)

        return wrapper

    return decorator


def arithmetic_0_param_command(name: str, command_id: int):
    @command_emitter()
    def command(
        res: mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
    ) -> mnllib.CodeCommand:
        return emit_command(command_id, [], res, subroutine=subroutine)

    command.__name__ = name
    return command


def arithmetic_1_param_command(name: str, command_id: int):
    @command_emitter()
    def command(
        a: int | float | mnllib.Variable,
        res: mnllib.Variable,
        *,
        subroutine: mnllib.Subroutine | None = None,
    ) -> mnllib.CodeCommand:
        return emit_command(command_id, [a], res, subroutine=subroutine)

    command.__name__ = name
    return command


def arithmetic_2_param_command(name: str, command_id: int):
    @command_emitter()
    def command(
        a: int | float | mnllib.Variable,
        b: int | float | mnllib.Variable,
        res: mnllib.Variable,
        *,
        subroutine: mnllib.Subroutine | None = None,
    ) -> mnllib.CodeCommand:
        return emit_command(command_id, [a, b], res, subroutine=subroutine)

    command.__name__ = name
    return command


@command_emitter()
def emit_command(
    *args: typing.Any, subroutine: mnllib.Subroutine | None = None, **kwargs: typing.Any
) -> mnllib.CodeCommand:
    assert subroutine is not None

    command = mnllib.CodeCommand(*args, **kwargs)
    subroutine.commands.append(command)
    return command


@command_emitter()
def emit_command_with_offsets(
    *args: typing.Any, subroutine: mnllib.Subroutine | None = None, **kwargs: typing.Any
) -> CodeCommandWithOffsets:
    assert subroutine is not None

    command = CodeCommandWithOffsets(*args, **kwargs)
    subroutine.commands.append(command)
    return command


@command_emitter()
def data(
    *args: typing.Any, subroutine: mnllib.Subroutine | None = None, **kwargs: typing.Any
) -> mnllib.RawDataCommand:
    assert subroutine is not None

    command = mnllib.RawDataCommand(*args, **kwargs)
    subroutine.commands.append(command)
    return command


@command_emitter()
def array(
    *args: typing.Any, subroutine: mnllib.Subroutine | None = None, **kwargs: typing.Any
) -> mnllib.ArrayCommand:
    assert subroutine is not None

    command = mnllib.ArrayCommand(*args, **kwargs)
    subroutine.commands.append(command)
    return command


@command_emitter()
def label(name: str, *, subroutine: mnllib.Subroutine | None = None) -> str:
    assert subroutine is not None

    subroutine_ext = typing.cast(SubroutineExt, subroutine)
    if not hasattr(subroutine_ext, "labels"):
        subroutine_ext.labels = {}
    subroutine_ext.labels[name] = subroutine.serialized_len(
        CommonGlobals.script_manager, 0, with_footer=False
    )
    return name


@command_emitter()
def terminate_script(
    *, subroutine: mnllib.Subroutine | None = None
) -> mnllib.CodeCommand:
    return emit_command(0x0000, subroutine=subroutine)


@command_emitter()
def return_(*, subroutine: mnllib.Subroutine | None = None) -> mnllib.CodeCommand:
    return emit_command(0x0001, subroutine=subroutine)
