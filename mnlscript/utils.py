import functools
import types
import typing


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


def fhex(num: int, width: int = 0) -> str:
    return f"{"-" if num < 0 else ""}0x{abs(num):0{width}X}"


def arg_isinstance_or_not_implemented(
    index: int, allowed_types: type | types.UnionType | tuple[type, ...]
) -> typing.Callable[
    [typing.Callable[P, T]], typing.Callable[P, T | types.NotImplementedType]
]:
    def decorator(
        function: typing.Callable[P, T]
    ) -> typing.Callable[P, T | types.NotImplementedType]:
        @functools.wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | types.NotImplementedType:
            if len(args) <= index:
                return NotImplemented
            if not isinstance(args[index], allowed_types):
                return NotImplemented

            return function(*args, **kwargs)

        return wrapper

    return decorator
