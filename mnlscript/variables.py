import functools
import types
import typing

import mnllib


class Operation:
    command_function: typing.Callable[
        [mnllib.Variable, mnllib.Subroutine | None], typing.Any
    ]

    def __init__(
        self,
        command_function: typing.Callable[
            [mnllib.Variable, mnllib.Subroutine | None], typing.Any
        ],
    ) -> None:
        self.command_function = command_function

    def apply(
        self, res: mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
    ) -> None:
        self.command_function(res, subroutine)


def single_command_operation[**P](
    command_function: typing.Callable[..., typing.Any], reverse: bool = False
) -> typing.Callable[
    [typing.Callable[P, Operation | types.NotImplementedType | None]],
    typing.Callable[P, Operation | types.NotImplementedType],
]:
    def decorator(
        function: typing.Callable[P, Operation | types.NotImplementedType | None],
    ) -> typing.Callable[P, Operation | types.NotImplementedType]:
        @functools.wraps(function)
        def wrapper(
            *args: P.args, **kwargs: P.kwargs
        ) -> Operation | types.NotImplementedType:
            result = function(*args, **kwargs)
            if result is not None:
                return result

            for arg in args:
                if not isinstance(arg, (int, float, mnllib.Variable)):
                    return NotImplemented

            if reverse:
                real_args: typing.Iterator[object] | tuple[object, ...] = reversed(args)
            else:
                real_args = args

            return Operation(
                lambda res, subroutine: command_function(
                    *real_args, res, subroutine=subroutine, **kwargs
                )
            )

        return wrapper

    return decorator


def in_place_single_command_operation[T, **P](
    command_function: typing.Callable[..., typing.Any],
) -> typing.Callable[
    [typing.Callable[typing.Concatenate[T, P], bool | None]],
    typing.Callable[typing.Concatenate[T, P], T | types.NotImplementedType],
]:
    def decorator(
        function: typing.Callable[typing.Concatenate[T, P], bool | None],
    ) -> typing.Callable[typing.Concatenate[T, P], T | types.NotImplementedType]:
        @functools.wraps(function)
        def wrapper(
            res: T, *args: P.args, **kwargs: P.kwargs
        ) -> T | types.NotImplementedType:
            if function(res, *args, **kwargs):
                return res

            for arg in args:
                if not isinstance(arg, (int, float, mnllib.Variable)):
                    return NotImplemented

            command_function(*args, res, **kwargs)

            return res

        return wrapper

    return decorator
