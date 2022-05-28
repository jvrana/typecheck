import inspect
import typing

import pytest

from typecheck.check import is_builtin_inst
from typecheck.check import is_builtin_type
from typecheck.check import is_typing_type
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
        ],
    )
    def test_union(self, inst, typ, valid):
        check = ValueChecker()
        result = check(inst, typ)
        print(result.msg)
        assert bool(result) is valid

    # TODO: support TypedDict


class TestTypeCheckWrapper:
    def test_type_check_simple(self):
        check = ValueChecker(do_raise=True)

        @check.typecheck
        def foo(a: int):
            ...

        foo(5)
        with pytest.raises(ValueChecker.default_exception_type):
            foo("s")

    def test_type_check_many(self):
        check = ValueChecker(do_raise=True)

        @check.typecheck
        def foo(a: int, b: str, c: dict):
            ...

        foo(5, "soething", {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, "", {})

    def test_type_check_only(self):
        check = ValueChecker(do_raise=True)

        @check.typecheck("b")
        def foo(a: int, b: str, c: dict):
            ...

        foo(5, "something", {})
        foo(5.0, "something", {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, 1, {})

    def test_type_check_only_many(self):
        check = ValueChecker(do_raise=True)

        @check.typecheck("b", "c")
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

        @check.typecheck("b")
        @check.typecheck("c")
        def foo(a: int, b: str, c: dict):
            ...

        foo(5, "something", {})
        foo(5.0, "something", {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, 1, {})
        with pytest.raises(ValueChecker.default_exception_type):
            foo(1.0, "str", 1)
