# TODO: Fix type annotations and remove asserts once
# concatenationg keyword parameters is added.


import functools
import typing

from dynamicscope import DYNAMIC_SCOPE
import mnllib


COMMON_ARITHMETIC_COMMANDS = [
    "add",
    "subtract",
    "multiply",
    "divide",
    "modulo",
]
COMMON_ARITHMETIC_COMMANDS_2 = ["sqrt", "invsqrt", "invert", "sin", "cos", "atan"]
INTEGER_ARITHMETIC_COMMANDS = [
    "logical_shift_left",
    "logical_shift_right",
    "bitwise_and",
    "bitwise_or",
    "bitwise_xor",
]


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


def command_emitter() -> (
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


@command_emitter()
def emit_command(
    *args: typing.Any, subroutine: mnllib.Subroutine | None = None, **kwargs: typing.Any
) -> mnllib.Command:
    assert subroutine is not None

    command = mnllib.Command(*args, **kwargs)
    subroutine.commands.append(command)
    return command


@command_emitter()
def return_(*, subroutine: mnllib.Subroutine | None = None) -> mnllib.Command:
    return emit_command(0x0001, subroutine=subroutine)


@command_emitter()
def set_variable(
    value: int | mnllib.Variable,
    res: mnllib.Variable,
    *,
    subroutine: mnllib.Subroutine | None = None
) -> mnllib.Command:
    return emit_command(0x0008, [value], res, subroutine=subroutine)


def arithmetic_0_param_command(name: str, command_id: int):
    @command_emitter()
    def command(
        res: mnllib.Variable, *, subroutine: mnllib.Subroutine | None = None
    ) -> mnllib.Command:
        return emit_command(command_id, [], res, subroutine=subroutine)

    command.__name__ = name
    return command


def arithmetic_1_param_command(name: str, command_id: int):
    @command_emitter()
    def command(
        a: int | mnllib.Variable,
        res: mnllib.Variable,
        *,
        subroutine: mnllib.Subroutine | None = None
    ) -> mnllib.Command:
        return emit_command(command_id, [a], res, subroutine=subroutine)

    command.__name__ = name
    return command


def arithmetic_2_param_command(name: str, command_id: int):
    @command_emitter()
    def command(
        a: int | mnllib.Variable,
        b: int | mnllib.Variable,
        res: mnllib.Variable,
        *,
        subroutine: mnllib.Subroutine | None = None
    ) -> mnllib.Command:
        return emit_command(command_id, [a, b], res, subroutine=subroutine)

    command.__name__ = name
    return command


# This doesn't work for type checking, unfortunately.
# for i, name in enumerate(
#     itertools.chain(COMMON_ARITHMETIC_COMMANDS, INTEGER_ARITHMETIC_COMMANDS)
# ):
#     _globals[name] = arithmetic_2_param_command(name, 0x0009 + i)
#
#     assign_command_name = name + "_assign"
#     _globals[assign_command_name] = arithmetic_1_param_command(
#         assign_command_name, 0x0018 + i
#     )
add = arithmetic_2_param_command("add", 0x0009)
subtract = arithmetic_2_param_command("subtract", 0x000A)
multiply = arithmetic_2_param_command("multiply", 0x000B)
divide = arithmetic_2_param_command("divide", 0x000C)
modulo = arithmetic_2_param_command("modulo", 0x000D)
logical_shift_left = arithmetic_2_param_command("logical_shift_left", 0x000E)
logical_shift_right = arithmetic_2_param_command("logical_shift_right", 0x000F)
bitwise_and = arithmetic_2_param_command("bitwise_and", 0x0010)
bitwise_or = arithmetic_2_param_command("bitwise_or", 0x0011)
bitwise_xor = arithmetic_2_param_command("bitwise_xor", 0x0012)
add_assign = arithmetic_1_param_command("add_assign", 0x0018)
subtract_assign = arithmetic_1_param_command("subtract_assign", 0x0019)
multiply_assign = arithmetic_1_param_command("multiply_assign", 0x001A)
divide_assign = arithmetic_1_param_command("divide_assign", 0x001B)
modulo_assign = arithmetic_1_param_command("modulo_assign", 0x001C)
logical_shift_left_assign = arithmetic_1_param_command(
    "logical_shift_left_assign", 0x001D
)
logical_shift_right_assign = arithmetic_1_param_command(
    "logical_shift_right_assign", 0x001E
)
bitwise_and_assign = arithmetic_1_param_command("bitwise_and_assign", 0x001F)
bitwise_or_assign = arithmetic_1_param_command("bitwise_or_assign", 0x0020)
bitwise_xor_assign = arithmetic_1_param_command("bitwise_xor_assign", 0x0021)

negate = arithmetic_1_param_command("negate", 0x0013)
to_boolean = arithmetic_1_param_command("to_boolean", 0x0014)
bitwise_not = arithmetic_1_param_command("bitwise_not", 0x0015)
increment = arithmetic_0_param_command("increment", 0x0016)
decrement = arithmetic_0_param_command("decrement", 0x0017)

# for i, name in enumerate(COMMON_ARITHMETIC_COMMANDS_2):
#     _globals[name] = arithmetic_1_param_command(name, 0x0022 + i)
#
#     fp_command_name = "fp_" + name
#     _globals[fp_command_name] = arithmetic_1_param_command(
#         fp_command_name, 0x0032 + i
#     )
sqrt = arithmetic_1_param_command("sqrt", 0x0022)
invsqrt = arithmetic_1_param_command("invsqrt", 0x0023)
invert = arithmetic_1_param_command("invert", 0x0024)
sin = arithmetic_1_param_command("sin", 0x0025)
cos = arithmetic_1_param_command("cos", 0x0026)
atan = arithmetic_1_param_command("atan", 0x0027)
fp_sqrt = arithmetic_1_param_command("fp_sqrt", 0x0032)
fp_invsqrt = arithmetic_1_param_command("fp_invsqrt", 0x0033)
fp_invert = arithmetic_1_param_command("fp_invert", 0x0034)
fp_sin = arithmetic_1_param_command("fp_sin", 0x0035)
fp_cos = arithmetic_1_param_command("fp_cos", 0x0036)
fp_atan = arithmetic_1_param_command("fp_atan", 0x0037)

atan2 = arithmetic_2_param_command("atan2", 0x0028)
random_below = arithmetic_1_param_command("random_below", 0x0029)

fp_set_variable = arithmetic_1_param_command("fp_set_variable", 0x002A)

# for i, name in enumerate(COMMON_ARITHMETIC_COMMANDS):
#     fp_command_name = "fp_" + name
#     _globals[fp_command_name] = arithmetic_2_param_command(
#         fp_command_name, 0x002B + i
#     )
fp_add = arithmetic_2_param_command("fp_add", 0x002B)
fp_subtract = arithmetic_2_param_command("fp_subtract", 0x002C)
fp_multiply = arithmetic_2_param_command("fp_multiply", 0x002D)
fp_divide = arithmetic_2_param_command("fp_divide", 0x002E)
fp_modulo = arithmetic_2_param_command("fp_modulo", 0x002F)

fp_to_int = arithmetic_1_param_command("fp_to_int", 0x0030)
fp_trunc = arithmetic_1_param_command("fp_trunc", 0x0031)
fp_atan2 = arithmetic_2_param_command("fp_atan2", 0x0038)
