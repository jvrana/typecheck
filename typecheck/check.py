from __future__ import annotations

import functools
import inspect
import sys
import typing
import warnings
from typing import Any
from typing import Callable
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union


if sys.version_info > (3.9,):
    from typing import ParamSpec, TypeAlias, Concatenate
else:
    from typing_extensions import ParamSpec, TypeAlias, Concatenate

P = ParamSpec("P")
P2 = ParamSpec("P", bound=bool)
P3 = ParamSpec("P", bound=bool)
R = TypeVar("R")
Types = Union[Type, Tuple[Type, ...]]

ExceptionType: TypeAlias = TypeVar("ExceptionType", bound=Type[Exception])
WarningType: TypeAlias = TypeVar("WarningType", bound=Type[Warning])


class TypeCheckError(Exception):
    """Type Checking Error."""


class TypeCheckWarning(Warning):
    """Type Checking Warning."""


# def get_inner_type(typ: ):


def is_builtin_type(obj: Any):
    """Return whether the provided class or type is a Python builtin type.

    :param obj: any type
    :return: True if is builtin type
    """
    if obj.__class__ is type:
        return obj.__module__ == "builtins"
    return False


def is_builtin_inst(obj: Any):
    """Return whether the provided instance is an instance of a  Python builtin
    type.

    :param obj: any instance
    :return: True only if is instance of builtin type
    """
    if obj.__class__ is type:
        return False
    return is_builtin_type(type(obj))


def is_typing_type(x: Any) -> bool:
    return x.__class__.__module__ == typing.__name__


is_generator_function = inspect.isgeneratorfunction

is_generator = inspect.isgenerator


def is_any(x: Any, types: List[Any]) -> bool:
    for t in types:
        if x is t:
            return True
    return False


def is_instance(x: Any, types: Types) -> bool:
    try:
        return isinstance(x, types)
    except TypeError:
        return False


class ValidationResult(NamedTuple):
    valid: bool
    msg: str

    def __bool__(self) -> bool:
        return self.valid

    def combine(self, other: ValidationResult) -> ValidationResult:
        valid = all([self.valid, other.valid])
        msg = "\n".join([self.msg, other.msg])
        return ValidationResult(valid, msg)


def check_handler(
    f: Callable[Concatenate[ValueChecker, P], R]
) -> Callable[Concatenate[ValueChecker, P], R]:
    @functools.wraps(f)
    def wrapped(self: ValueChecker, *args: P.args, **kwargs: P.kwargs) -> R:
        result = f(self, *args, **kwargs)
        handle_kwargs = {
            attr: kwargs.get(attr, getattr(self, attr))
            for attr in ["do_raise", "exception_type", "do_warn", "warning_type"]
        }
        return self._handle(result, **handle_kwargs)

    return wrapped


# TODO: add global config
class ValueChecker:
    default_exception_type: ExceptionType = TypeCheckError
    default_warning_type: WarningType = TypeCheckWarning
    default_do_raise: bool = False
    default_do_warn: bool = False

    def __init__(
        self,
        do_raise: bool = default_do_raise,
        exception_type: ExceptionType = default_exception_type,
        do_warn: bool = default_do_warn,
        warning_type: WarningType = default_warning_type,
    ):
        self.do_raise = do_raise
        self.exception_type = exception_type
        self.do_warn = do_warn
        self.warning_type = warning_type

    @staticmethod
    def _handle(
        x: ValidationResult,
        do_raise: bool = False,
        do_warn: bool = False,
        exception_type: ExceptionType = default_exception_type,
        warning_type: Optional[WarningType] = default_warning_type,
    ) -> ValidationResult:
        """Handle a validation result.

        :param x:
        :param do_raise: If True, raise
        :param exception_type:
        :return:
        """
        if exception_type:
            if not issubclass(exception_type, Exception):
                raise TypeError(
                    f"Exception type must be an Exception. Found {type(exception_type)}"
                )
        if is_instance(do_raise, bool):
            if do_raise is True and exception_type is None:
                exception_type = TypeCheckError
        if do_raise and bool(x) is False:
            raise exception_type(x.msg)
        if do_warn and bool(x) is False:
            if warning_type is None:
                w = x.msg
            else:
                w = warning_type(x.msg)
            warnings.warn(w)
        return x

    @staticmethod
    def _create_error_msg(msg: str, extra_msg: Optional[str] = None) -> str:
        if extra_msg:
            err_msg = extra_msg + " "
        else:
            err_msg = ""
        return err_msg + msg

    @check_handler
    def is_instance_of(
        self,
        obj: Any,
        typ: Types,
        *,
        extra_err_msg: Optional[str] = None,
        do_raise: bool = False,
        exception_type: ExceptionType = default_exception_type,
        do_warn: bool = False,
        warning_type: WarningType = default_warning_type,
        _force_untrue: bool = False,
    ) -> ValidationResult:
        _, _, _, _ = (
            do_raise,
            exception_type,
            do_warn,
            warning_type,
        )  # purely to ignore linting errors
        errmsg = ""
        valid = True
        if _force_untrue or not is_instance(obj, typ):
            errmsg = f"Expected {obj} to be a {typ}, but found a {type(obj)} ({obj})"
            errmsg = self._create_error_msg(errmsg, extra_err_msg)
            valid = False
        return ValidationResult(valid, errmsg)

    def __call__(
        self,
        obj: Any,
        typ: Any,
        *,
        extra_err_msg: Optional[str] = None,
        do_raise: bool = False,
        exception_type: ExceptionType = default_exception_type,
        do_warn: bool = False,
        warning_type: WarningType = default_warning_type,
    ):
        kwargs = dict(
            extra_err_msg=extra_err_msg,
            do_raise=do_raise,
            do_warn=do_warn,
            exception_type=exception_type,
            warning_type=warning_type,
        )
        if is_typing_type(typ):
            if hasattr(typ, "__origin__"):
                outer_typ = typ.__origin__
                result = self.is_instance_of(obj, outer_typ, **kwargs)
                if hasattr(typ, "__args__"):
                    if typ.__args__:
                        if outer_typ is list:
                            result = self._check_inner_list(result, obj, typ, kwargs)
                        elif outer_typ is tuple:
                            result = self._check_inner_tuple(result, obj, typ, kwargs)
                        elif outer_typ is dict:
                            result = self._check_inner_dict(result, obj, typ, kwargs)
                        elif outer_typ == typing.Union:
                            for inner_typ in typ.__args__:
                                result = self(obj, inner_typ)
                                if result.valid is True:
                                    return result
                return result
        return self.is_instance_of(obj, typ, **kwargs)

    def _check_inner_dict(self, result, obj, typ, kwargs):
        key_type, val_type = typ.__args__
        for k in obj:
            inner_result = self(k, key_type, **kwargs)
            result = result.combine(inner_result)
        for v in obj.values():
            inner_result = self(v, val_type, **kwargs)
            result = result.combine(inner_result)
        return result

    def _check_inner_tuple(self, result, obj, typ, kwargs):
        use_same_inner_type = False
        if len(typ.__args__) >= 2 and typ.__args__[1] is Ellipsis:
            inner_typ = typ.__args__[0]
            use_same_inner_type = True
        for i, inner_obj in enumerate(obj):
            try:
                if not use_same_inner_type:
                    inner_typ = typ.__args__[i]
                inner_result = self(inner_obj, inner_typ, **kwargs)
            except IndexError:
                inner_result = self.is_instance_of(
                    inner_obj, inner_typ, _force_untrue=True, **kwargs
                )
            result = result.combine(inner_result)
        return result

    def _check_inner_list(self, result, obj, typ, kwargs):
        inner_typ = typ.__args__[0]
        for inner_obj in obj:
            inner_result = self(inner_obj, inner_typ, **kwargs)
            result = result.combine(inner_result)
        return result
