#  Copyright (c) 2022. Justin Vrana - All Rights Reserved
#   You may use, distribute and modify this code under the terms of the MIT license.
import collections.abc
import inspect
import typing
from enum import Enum
from typing import NamedTuple
from typing import Optional

import pytest

import typecheck
from typecheck._tests import fail_type_check
from typecheck._tests import for_readable_error_on_function
from typecheck.check import is_builtin_inst
from typecheck.check import is_builtin_type
from typecheck.check import is_subclass
from typecheck.check import is_typing_type
from typecheck.check import TypeCheckError
from typecheck.check import ValidationResult
from typecheck.check import ValueChecker


class Foo:
    ...


@pytest.mark.parametrize(
    "typ", [dict, tuple, list, int, complex, float, str, bytes, bytearray]
)
def test_is_builtin_type(typ):
    assert is_builtin_type(typ)


@pytest.mark.parametrize("typ", [5, 1, "str", Foo, Foo()])
def test_is_not_builtin_type(typ):
    assert not is_builtin_type(typ)


@pytest.mark.parametrize("x", [5, (1,), 5.0, "string"])
def test_is_builtin_inst(x):
    assert is_builtin_inst(x)


@pytest.mark.parametrize("x", [Foo, Foo(), dict, tuple])
def test_is_not_builtin_inst(x):
    assert not is_builtin_inst(x)


@pytest.mark.parametrize(
    "x", [typing.Type, typing.Collection, typing.List], ids=lambda x: str(x)
)
def test_is_typing_type(x):
    assert is_typing_type(x)


@pytest.mark.parametrize("x", [5, (1,), 5.0, "string"], ids=lambda x: str(x))
def test_is_not_typing_type(x):
    assert not is_typing_type(x)


def test_is_subclass():
    class Foo(typing.List):
        ...

    class Bar(Foo):
        ...

    assert is_subclass(typing.List, typing.List)
    assert not is_subclass(5, typing.List)
    assert issubclass(Bar, Foo)
    assert is_subclass(Bar, Foo)
    assert is_subclass(Bar, typing.List)
    assert is_subclass(Foo, typing.List)
    assert not is_subclass(Foo, typing.Dict)
    assert not is_subclass(
        typing.List, typing.Sequence
    ), "List is not a direct subclass of Sequence"
    assert is_subclass(
        typing.List.__origin__, typing.Sequence
    ), "list IS a direct subclass of Sequence"


def empty_generator():
    return
    yield


def not_a_generator():
    return


def test_is_generator():
    assert inspect.isgeneratorfunction(empty_generator)
    assert not inspect.isgeneratorfunction(not_a_generator)


class TestValidators:
    @pytest.mark.parametrize(
        "inst,typ", [(5, int), (5.0, float), ([], list), ((1,), tuple), ("mystr", str)]
    )
    def test_validate_is_instance(self, inst, typ):
        check = ValueChecker()
        result = check.is_instance_of(inst, typ)
        assert isinstance(result, ValidationResult)
        assert result
        assert not result.msg
        assert bool(result) is True

    @pytest.mark.parametrize("inst,typ", [(5.0, int), ("sl", float), ((1,), list)])
    def test_validate_is_not_instance(self, inst, typ):
        check = ValueChecker()
        result = check.is_instance_of(inst, typ)
        assert isinstance(result, ValidationResult)
        assert not result
        assert result.msg
        assert bool(result) is False

    @pytest.mark.parametrize("inst,typ", [(5.0, int), ("sl", float), ((1,), list)])
    def test_validate_is_not_instance_do_raise(self, inst, typ):
        check = ValueChecker()
        with pytest.raises(ValueChecker.default_exception_type):
            check.is_instance_of(inst, typ, do_raise=True)

    def test_raises_custom_exception(self):
        """Test that default exception type can be overridden on
        ValueChecker.__init__"""

        class CustomException(Exception):
            ...

        check = ValueChecker(exception_type=CustomException)
        with pytest.raises(CustomException):
            check.is_instance_of(5, list, do_raise=True)

    def test_raises_custom_exception_override(self):
        """Test that exception type can be overridden on method call."""

        class CustomException(Exception):
            ...

        class CustomException2(Exception):
            ...

        check = ValueChecker(exception_type=CustomException)
        with pytest.raises(CustomException2):
            check.is_instance_of(
                5, list, do_raise=True, exception_type=CustomException2
            )

    def test_do_warn(self):
        """Test that exception type can be overridden on method call."""
        check = ValueChecker()
        with pytest.warns(ValueChecker.default_warning_type):
            check.is_instance_of(5, list, do_warn=True)

        class CustomWarning(Warning):
            ...

        class CustomWarning2(Warning):
            ...

        check = ValueChecker(warning_type=CustomWarning)
        with pytest.warns(CustomWarning):
            check.is_instance_of(5, list, do_warn=True)
        with pytest.warns(CustomWarning2):
            check.is_instance_of(5, list, do_warn=True, warning_type=CustomWarning2)

    @pytest.mark.parametrize(
        "inst,typ,valid",
        [
            ([1], typing.List, True),
            ({}, typing.Dict, True),
            ([1, 2, 3], typing.Dict, False),
            ((1,), typing.Tuple, True),
            (
                [
                    1,
                ],
                typing.Tuple,
                False,
            ),
            (empty_generator(), typing.Generator, True),
            (not_a_generator(), typing.Generator, False),
            (not_a_generator, typing.Callable, True),
            (dict, typing.Callable, True),
            (5, typing.Callable, False),
        ],
    )
    def test_check_outer_type(self, inst, typ, valid):
        check = ValueChecker()
        result = bool(check(inst, typ))
        assert result is valid

    @pytest.mark.parametrize(
        "inst,typ,valid",
        [
            ([1], typing.List, True),
            ([1], typing.List[int], True),
            (["str"], typing.List[float], False),
            (["str"], typing.List[str], True),
            (["str"], typing.Tuple[str, ...], False),
            (("str",), typing.Tuple[str, ...], True),
            (("str", "str"), typing.Tuple[str, ...], True),
            (("str", 1), typing.Tuple[str, ...], False),
            ((1,), typing.Tuple[str, ...], False),
            ({1: "str"}, typing.Dict[int, str], True),
            ({1: "str"}, typing.Dict[int, int], False),
        ],
    )
    def test_check_inner_type(self, inst, typ, valid):
        check = ValueChecker()
        result = check(inst, typ)
        print(result.msg)
        assert bool(result) is valid

    @pytest.mark.parametrize(
        "inst,typ,valid",
        [
            (1, typing.Union[int, str], True),
            ("1", typing.Union[int, str], True),
            (1.0, typing.Union[int, str], False),
            ([], typing.Union[float, typing.List[float]], True),
        ],
    )
    def test_union(self, inst, typ, valid):
        check = ValueChecker()
        result = check(inst, typ)
        print(result.msg)
        assert bool(result) is valid

    # TODO: support TypedDict

    def test_extra_msg(self):
        check = ValueChecker()
        result = check(5, float, extra_err_msg="Some extra message.")
        assert (
            result.msg
            == "Some extra message. \nExpected <class 'int'> '5' to be a <class 'float'>."
        )

    def test_arg_msg(self):
        check = ValueChecker()
        result = check(5, float, extra_err_msg="Some extra message.", arg="a")
        assert (
            result.msg == "TypeError on argument 'a'. Some extra message. \n"
            "Expected <class 'int'> '5' to be a <class 'float'>."
        )

    @pytest.mark.parametrize("value", [5, "str", {}, []])
    def test_validate_any(self, value):
        check = ValueChecker()
        result = check(value, typing.Any)
        assert bool(result)

    @pytest.mark.parametrize("value", [5, "str", {}, []])
    def test_validate_union_any(self, value):
        check = ValueChecker()

        class Foo:
            ...

        result = check(value, typing.Union[Foo, typing.Any])
        assert bool(result)

    def test_typed_dict(self):
        check = ValueChecker()

        Point2D = typing.TypedDict("Point2D", x=int, y=int, label=str)

        data = {"x": 1, "y": 2, "label": "mylabel"}
        result = check(data, Point2D)
        assert bool(result)

        data = {"x": 1, "label": "mylabel"}
        result = check(data, Point2D)
        print(result.msg)
        assert (
            result.msg
            == "Key 'y' missing on TypedDict <class 'test_typecheck.Point2D'>. "
            "Expected keys ['x', 'y', 'label']"
        )
        assert not bool(result)

        data = {"x": 1, "y": 2.0, "label": "mylabel"}
        result = check(data, Point2D)
        print(result.msg)
        assert (
            result.msg
            == "TypeError on key 'y'. \nExpected <class 'float'> '2.0' to be a <class 'int'>."
        )
        assert not bool(result)


class TestCallableChecks:
    @pytest.mark.parametrize(
        "typ", [typing.Callable[[int, float], typing.Any], typing.Callable]
    )
    def test_callable_passes(self, typ):
        check = ValueChecker()

        def foo(a: int, b: float) -> typing.Any:
            ...

        assert bool(check(foo, typ))

    def test_any_annotation(self):
        check = ValueChecker()

        def foo(a: int, b: float) -> typing.Any:
            ...

        def bar(a: str, b: list) -> dict:
            ...

        assert check(foo, typing.Callable[[typing.Any, typing.Any], typing.Any])
        assert check(bar, typing.Callable[[typing.Any, typing.Any], typing.Any])

    def test_any_annotation2(self):
        check = ValueChecker()

        def foo(a: typing.Any, b: float) -> dict:
            ...

        assert not check(foo, typing.Callable[[int, float], dict])

    def test_wrong_return_type(self):
        check = ValueChecker()

        def foo(a: int, b: float) -> float:
            ...

        assert bool(check(foo, typing.Callable))
        result = check(foo, typing.Callable[[int, float], typing.Any])
        print(result.msg)
        assert bool(result)
        assert bool(check(foo, typing.Callable[[int, float], float]))
        assert not bool(check(foo, typing.Callable[[int, float], int]))

    @pytest.mark.parametrize(
        "typ", [typing.Callable[[int, float], typing.Any], typing.Callable]
    )
    def test_not_a_callable(self, typ):
        check = ValueChecker()
        result = check(5, typ)
        assert bool(result) is False

    def test_callable_wrong_num_args(self):
        check = ValueChecker()
        Fn = typing.Callable[[int, float], typing.Any]

        def foo(a: int, b: float, c: float) -> typing.Any:
            ...

        result = check(foo, Fn)
        assert not bool(result)

    def test_wrong_type(self):
        check = ValueChecker()
        Fn = typing.Callable[[int, float], typing.Any]

        def foo(a: float, b: float) -> typing.Any:
            ...

        result = check(foo, Fn)
        print(result.msg)
        assert not bool(result)

    def test_callable_class(self):
        check = ValueChecker()

        class Foo(typing.Callable[[int, float], str]):
            def __call__(self, a: int, b: float) -> str:
                ...

        result = check(Foo(), typing.Callable[[int, float], str])
        print(result.msg)
        assert bool(result)

    def test_generator_function(self):
        check = ValueChecker()

        T = typing.Callable[[int], typing.Generator[int, None, None]]

        def foo(a: int) -> typing.Generator[int, None, None]:
            yield 5

        assert bool(check(foo, T))

    def test_wrapper_with_generator_function(self):
        check = ValueChecker(do_raise=True)

        class Foo:
            ...

        T = typing.Callable[[int], typing.Generator[Foo, None, None]]

        @check.validate_args
        def wrapper(fn: T):
            ...

        def foo(a: int) -> typing.Generator[Foo, None, None]:
            yield 5

        wrapper(foo)

    def test_is_generator_type(self):
        T = typing.Generator[int, None, None]
        assert is_subclass(T.__origin__, collections.abc.Generator)

    def test_not_a_generator_function(self):
        check = ValueChecker()

        T = typing.Callable[[int], typing.Generator[int, None, None]]

        def foo(a: int) -> typing.Generator[int, None, None]:
            return 5

        assert not bool(check(foo, T))

    def test_generator_function_no_return_type(self):
        check = ValueChecker()

        T = typing.Callable[[int], typing.Generator[int, None, None]]

        def foo(a: int):
            yield 5

        assert bool(check(foo, T))

    def test_generator2(self):
        check = ValueChecker()
        assert check.is_type_of(
            typing.Generator[int, None, None], typing.Generator[int, None, None]
        )


def test_stack_trace():
    with pytest.raises(TypeCheckError) as e:
        fail_type_check()
    expected_error = str(e.traceback[1])
    assert "validate_value(5.0, int)" in expected_error


class TestTypeCheckWrapper:
    def test_type_check_simple(self):
        check = ValueChecker(do_raise=True)

        @check.validate_args
        def foo(a: int):
            ...

        foo(5)
        with pytest.raises(ValueChecker.default_exception_type):
            foo("s")

    def test_type_check_many(self):
        check = ValueChecker(do_raise=True)

        @check.validate_args
        def foo(a: int, b: str, c: dict):
            ...

        foo(5, "soething", {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, "", {})

    def test_type_check_function(self):
        check = ValueChecker(do_raise=True)

        class Foo:
            @check.validate_args
            def foo(self, a: int, b: str, c: dict):
                ...

        Foo().foo(5, "str", {})
        with pytest.raises(TypeCheckError):
            Foo().foo(5, 5.0, {})

    def test_type_check_only(self):
        check = ValueChecker(do_raise=True)

        @check.validate_args("b")
        def foo(a: int, b: str, c: dict):
            ...

        foo(5, "something", {})
        foo(5.0, "something", {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, 1, {})

    def test_type_check_only_many(self):
        check = ValueChecker(do_raise=True)

        @check.validate_args("b", "c")
        def foo(a: int, b: str, c: dict):
            ...

        foo(5, "something", {})
        foo(5.0, "something", {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, 1, {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, "str", 1)

    def test_type_check_only_many_wrappers(self):
        check = ValueChecker(do_raise=True)

        @check.validate_args("b")
        @check.validate_args("c")
        def foo(a: int, b: str, c: dict):
            ...

        foo(5, "something", {})
        foo(5.0, "something", {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, 1, {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, "str", 1)

    def test_nested(self):
        check = ValueChecker()
        result = check(
            [([1.0], "str")], typing.List[typing.Tuple[typing.List[float], str]]
        )
        assert bool(result)

        result = check([([1.0], 1)], typing.List[typing.Tuple[typing.List[float], str]])
        assert not bool(result)

        result = check(
            [([1], "str")], typing.List[typing.Tuple[typing.List[float], str]]
        )
        assert not bool(result)


class TestExamples:
    def test_with_named_tuple(self):
        class EventType(Enum):
            Type1 = "Type1"

        class Event(
            NamedTuple(
                "Event",
                [
                    ("event_type", EventType),
                    ("step_key", Optional[str]),
                    ("metadata", Optional[dict]),
                ],
            )
        ):
            ...

            @typecheck.validate_args
            def __new__(
                cls,
                event_type: EventType,
                step_key: Optional[str] = None,
                metadata: typing.Optional[dict] = None,
            ):
                super().__new__(cls, event_type, step_key, metadata)

        Event(EventType.Type1)
        Event(EventType.Type1, "step_key")
        Event(EventType.Type1, "step_key", {})
        with pytest.raises(TypeCheckError):
            Event(EventType.Type1, {})
        with pytest.raises(TypeCheckError):
            Event(EventType.Type1, 1)
        with pytest.raises(TypeCheckError):
            Event(EventType.Type1, "step_key", 1)

    def test_for_readable_error_on_function(self):
        with pytest.raises(Exception) as e:
            for_readable_error_on_function("str")
        for tb in e.traceback:
            print(tb)
