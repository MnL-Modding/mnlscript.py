import functools
import types
import typing

import mnllib

from .commands import (
    add,
    add_in_place,
    bitwise_and,
    bitwise_and_in_place,
    bitwise_not,
    bitwise_or,
    bitwise_or_in_place,
    bitwise_xor,
    bitwise_xor_in_place,
    decrement,
    divide,
    divide_in_place,
    increment,
    logical_shift_left,
    logical_shift_left_in_place,
    logical_shift_right,
    logical_shift_right_in_place,
    modulo,
    modulo_in_place,
    multiply,
    multiply_in_place,
    negate,
    set_variable,
    subtract,
    subtract_in_place,
)


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


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


def single_command_operation(
    command_function: typing.Callable[..., typing.Any], reverse: bool = False
) -> typing.Callable[
    [typing.Callable[P, Operation | types.NotImplementedType | None]],
    typing.Callable[P, Operation | types.NotImplementedType],
]:
    def decorator(
        function: typing.Callable[P, Operation | types.NotImplementedType | None]
    ) -> typing.Callable[P, Operation | types.NotImplementedType]:
        @functools.wraps(function)
        def wrapper(
            *args: P.args, **kwargs: P.kwargs
        ) -> Operation | types.NotImplementedType:
            result = function(*args, **kwargs)
            if result is not None:
                return result

            for arg in args:
                if not isinstance(arg, (int, mnllib.Variable)):
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


def in_place_single_command_operation(
    command_function: typing.Callable[..., typing.Any]
) -> typing.Callable[
    [typing.Callable[typing.Concatenate[T, P], bool | None]],
    typing.Callable[typing.Concatenate[T, P], T | types.NotImplementedType],
]:
    def decorator(
        function: typing.Callable[typing.Concatenate[T, P], bool | None]
    ) -> typing.Callable[typing.Concatenate[T, P], T | types.NotImplementedType]:
        @functools.wraps(function)
        def wrapper(
            res: T, *args: P.args, **kwargs: P.kwargs
        ) -> T | types.NotImplementedType:
            if function(res, *args, **kwargs):
                return res

            for arg in args:
                if not isinstance(arg, (int, mnllib.Variable)):
                    return NotImplemented

            command_function(*args, res, **kwargs)

            return res

        return wrapper

    return decorator


class Variable(mnllib.Variable):
    @typing.overload
    def __init__(self, number: int, /) -> None: ...
    @typing.overload
    def __init__(self, variable: mnllib.Variable, /) -> None: ...

    def __init__(self, arg: int | mnllib.Variable, /) -> None:
        if isinstance(arg, mnllib.Variable):
            super().__init__(arg.number)
        else:
            super().__init__(arg)

    @single_command_operation(add)
    def __add__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(add, reverse=True)
    def __radd__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(add_in_place)
    def __iadd__(self, other: int | mnllib.Variable) -> bool:
        if other == 1:
            increment(self)
            return True
        if other == -1:
            decrement(self)
            return True
        return False

    @single_command_operation(subtract)
    def __sub__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(subtract, reverse=True)
    def __rsub__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(subtract_in_place)
    def __isub__(self, other: int | mnllib.Variable) -> bool:
        if other == 1:
            decrement(self)
            return True
        if other == -1:
            increment(self)
            return True
        return False

    @single_command_operation(multiply)
    def __mul__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(multiply, reverse=True)
    def __rmul__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(multiply_in_place)
    def __imul__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(divide)
    def __floordiv__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(divide, reverse=True)
    def __rfloordiv__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(divide_in_place)
    def __ifloordiv__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(modulo)
    def __mod__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(modulo, reverse=True)
    def __rmod__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(modulo_in_place)
    def __imod__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(logical_shift_left)
    def __lshift__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(logical_shift_left, reverse=True)
    def __rlshift__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(logical_shift_left_in_place)
    def __ilshift__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(logical_shift_right)
    def __rshift__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(logical_shift_right, reverse=True)
    def __rrshift__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(logical_shift_right_in_place)
    def __irshift__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(bitwise_and)
    def __and__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(bitwise_and, reverse=True)
    def __rand__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(bitwise_and_in_place)
    def __iand__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(bitwise_xor)
    def __xor__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(bitwise_xor, reverse=True)
    def __rxor__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(bitwise_xor_in_place)
    def __ixor__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(bitwise_or)
    def __or__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(bitwise_or, reverse=True)
    def __ror__(self, other: int | mnllib.Variable) -> None:
        pass

    @in_place_single_command_operation(bitwise_or_in_place)
    def __ior__(self, other: int | mnllib.Variable) -> None:
        pass

    @single_command_operation(negate)
    def __neg__(self) -> None:
        pass

    @single_command_operation(bitwise_not)
    def __invert__(self) -> None:
        pass


class VariablesMeta(type):
    @functools.lru_cache
    def __getitem__(self, number: int) -> Variable:
        return Variable(number)

    def __setitem__(
        self, number: int, value: int | mnllib.Variable | Operation
    ) -> None:
        res = self[number]

        if isinstance(value, Operation):
            value.apply(res)
        elif not isinstance(value, mnllib.Variable) or value.number != number:
            set_variable(value, res)


class Variables(metaclass=VariablesMeta):
    pass
