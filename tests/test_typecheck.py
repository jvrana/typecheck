import pytest
import typing
from typecheck.check import is_builtin_type, is_builtin_inst, is_typing_type, ValueChecker, ValidationResult


class Foo():
    ...


@pytest.mark.parametrize('typ', [dict, tuple, list, int, complex, float, str, bytes, bytearray])
def test_is_builtin_type(typ):
    assert is_builtin_type(typ)


@pytest.mark.parametrize('typ', [5, 1, 'str', Foo, Foo()])
def test_is_not_builtin_type(typ):
    assert not is_builtin_type(typ)


@pytest.mark.parametrize('x', [5, (1,), 5.0, 'string'])
def test_is_builtin_inst(x):
    assert is_builtin_inst(x)


@pytest.mark.parametrize('x', [Foo, Foo(), dict, tuple])
def test_is_not_builtin_inst(x):
    assert not is_builtin_inst(x)


@pytest.mark.parametrize('x', [typing.Type, typing.Collection, typing.List], ids=lambda x: str(x))
def test_is_typing_type(x):
    assert is_typing_type(x)


@pytest.mark.parametrize('x', [5, (1,), 5.0, 'string'], ids=lambda x: str(x))
def test_is_typing_type(x):
    assert not is_typing_type(x)


class TestValidators():


    @pytest.mark.parametrize('inst,typ', [
        (5, int),
        (5.0, float),
        ([], list),
        ((1,), tuple),
        ('mystr', str)
    ])
    def test_validate_is_instance(self, inst, typ):
        check = ValueChecker()
        result = check.is_instance_of(inst, typ)
        assert isinstance(result, ValidationResult)
        assert result
        assert not result.msg
        assert bool(result) is True

    @pytest.mark.parametrize('inst,typ', [
        (5.0, int),
        ('sl', float),
        ((1,), list)
    ])
    def test_validate_is_not_instance(self, inst, typ):
        check = ValueChecker()
        result = check.is_instance_of(inst, typ)
        assert isinstance(result, ValidationResult)
        assert not result
        assert result.msg
        assert bool(result) is False

    @pytest.mark.parametrize('inst,typ', [
        (5.0, int),
        ('sl', float),
        ((1,), list)
    ])
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
        """Test that exception type can be overridden on method call"""
        class CustomException(Exception):
            ...

        class CustomException2(Exception):
            ...

        check = ValueChecker(exception_type=CustomException)
        with pytest.raises(CustomException2):
            check.is_instance_of(5, list, do_raise=True, exception_type=CustomException2)
