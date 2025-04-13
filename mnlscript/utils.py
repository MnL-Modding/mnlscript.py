import functools
import types
import typing


def fhex(num: int, width: int = 0) -> str:
    return f"{"-" if num < 0 else ""}0x{abs(num):0{width}X}"


def fhex_byte(num: int) -> str:
    return fhex(num, 2)


def fhex_short(num: int) -> str:
    return fhex(num, 4)


def fhex_int(num: int) -> str:
    return fhex(num, 8)


def arg_isinstance_or_not_implemented[T, **P](
    index: int, allowed_types: type | types.UnionType | tuple[type, ...]
) -> typing.Callable[
    [typing.Callable[P, T]], typing.Callable[P, T | types.NotImplementedType]
]:
    def decorator(
        function: typing.Callable[P, T],
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
