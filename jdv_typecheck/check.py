#  Copyright (c) 2022. Justin Vrana - All Rights Reserved
#   You may use, distribute and modify this code under the terms of the MIT license.
from __future__ import annotations

import collections
import functools
import inspect
import sys
import textwrap
import types
import typing
import warnings
from inspect import Signature
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
SignatureLike = Union[Callable, Signature]

ExceptionType: TypeAlias = TypeVar("ExceptionType", bound=Type[Exception])
WarningType: TypeAlias = TypeVar("WarningType", bound=Type[Warning])


class TypingType(typing.Protocol):
    __args__: tuple
    __origin__: typing.Any


class TypeCheckError(Exception):
    """Type Checking Error."""


class TypeCheckWarning(Warning):
    """Type Checking Warning."""


# def get_inner_type(typ: ):
class Null:
    ...


class _Nullable:
    def __getitem__(self, item):
        return Union[Type[Null], item]


Nullable = _Nullable()


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
    """Returns True if x is an instance of the provided types.

    :param x:
    :param types:
    :return:
    """
    try:
        return isinstance(x, types)
    except TypeError:
        return False


def is_empty(x: Any):
    """Check if value is an empty type (i.e. inspect._empty).

    This is the default value for annotation of an argument with no
    annotation
    """
    return x is inspect._empty


def is_subclass(x: Type, types: Types):
    if x is types or is_empty(x):
        return True
    if not inspect.isclass(x):
        return False
    else:
        return issubclass(x, types)


def is_generator_type(x: Any):
    if is_typing_type(x):
        if hasattr(x, "__origin__"):
            return is_subclass(x.__origin__, collections.abc.Generator)


class ValidationResult(NamedTuple):
    valid: bool
    msg: str

    def __bool__(self) -> bool:
        return self.valid

    def combine(self, other: ValidationResult) -> ValidationResult:
        valid = all([self.valid, other.valid])
        if not other.valid:
            msg = "\n".join([self.msg, other.msg])
        else:
            msg = self.msg
        msg = msg.strip("\n").strip()
        return ValidationResult(valid, msg)

    def wrapped_msg(self, width=250):
        return "\n".join(textwrap.wrap(self.msg, width=width))


def check_handler(
    f: Callable[Concatenate[ValueChecker, P], R]
) -> Callable[Concatenate[ValueChecker, P], R]:
    @functools.wraps(f)
    def wrapped(self: ValueChecker, *args: P.args, **kwargs: P.kwargs) -> R:
        result = f(self, *args, **kwargs)
        handle_kwargs = {}
        for attr in ["do_raise", "exception_type", "do_warn", "warning_type"]:
            if attr not in kwargs or kwargs[attr] is Null:
                handle_kwargs[attr] = getattr(self, attr)
            else:
                handle_kwargs[attr] = kwargs[attr]
        return self._handle(result, **handle_kwargs)

    return wrapped


def get_signature(obj: SignatureLike):
    if isinstance(obj, Signature):
        signature = obj
    else:
        signature = inspect.signature(obj)
    return signature


def get_back_frame(
    frame: Optional[types.FrameType] = None, ignore_files=(__file__,)
) -> types.FrameType:
    if frame is None:
        frame = inspect.currentframe()
    while frame.f_code.co_filename in ignore_files:
        frame = frame.f_back
    return frame


def reraise_outside_of_stack(exception: Exception):
    try:
        raise exception
    except Exception:
        traceback = sys.exc_info()[2]
        tb_frame = traceback.tb_frame
        back_frame = get_back_frame(tb_frame)
    back_tb = types.TracebackType(
        tb_next=None,
        tb_frame=back_frame,
        tb_lasti=back_frame.f_lasti,
        tb_lineno=back_frame.f_lineno,
    )
    raise exception.with_traceback(back_tb)


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
                reraise_outside_of_stack(
                    TypeError(
                        f"Exception type must be an Exception. Found {type(exception_type)}"
                    )
                )
        if is_instance(do_raise, bool):
            if do_raise is True and exception_type is None:
                exception_type = TypeCheckError
        if do_raise and bool(x) is False:
            reraise_outside_of_stack(exception_type(x.wrapped_msg()))
        if do_warn and bool(x) is False:
            if warning_type is None:
                w = x.wrapped_msg()
            else:
                w = warning_type(x.wrapped_msg())
            warnings.warn(w)
        return x

    @staticmethod
    def _create_error_msg(msg: str, extra_msg: Optional[str] = None) -> str:
        if extra_msg:
            err_msg = extra_msg + " "
        else:
            err_msg = ""
        return "\n".join([err_msg, msg])

    @staticmethod
    def _typ_is_callable(typ: Type):
        return typ is typing.Callable or typ is collections.Callable

    @staticmethod
    def _typ_is_typeddict(typ: Type):
        return isinstance(typ, typing._TypedDictMeta)

    @check_handler
    def is_instance_of(
        self,
        obj: Any,
        typ: Types,
        *,
        extra_err_msg: Optional[str] = None,
        do_raise: Union[Type[Null], bool] = Null,
        exception_type: Union[Type[Null], ExceptionType] = Null,
        do_warn: Union[Type[Null], bool] = Null,
        warning_type: Union[Type[Null], WarningType] = Null,
        _force_untrue: bool = False,
    ) -> ValidationResult:
        _, _, _, _ = do_raise, exception_type, do_warn, warning_type
        errmsg = ""
        valid = True
        if typ is typing.Any:
            pass  # do nothing
        elif _force_untrue or not is_instance(obj, typ):
            errmsg = f"Expected {type(obj)} '{obj}' to be a {typ}."
            errmsg = self._create_error_msg(errmsg, extra_err_msg)
            valid = False
        return ValidationResult(valid, errmsg)

    @check_handler
    def is_type_of(
        self,
        obj: Any,
        typ: Types,
        *,
        extra_err_msg: Optional[str] = None,
        do_raise: Union[Type[Null], bool] = Null,
        exception_type: Union[Type[Null], ExceptionType] = Null,
        do_warn: Union[Type[Null], bool] = Null,
        warning_type: Union[Type[Null], WarningType] = Null,
        _force_untrue: bool = False,
    ) -> ValidationResult:
        _, _, _, _ = do_raise, exception_type, do_warn, warning_type
        errmsg = ""
        valid = True
        if typ is typing.Any:
            pass  # do nothing
        elif _force_untrue or not is_subclass(obj, typ):
            errmsg = f"Expected {obj} to be a subclass of {typ}."
            errmsg = self._create_error_msg(errmsg, extra_err_msg)
            valid = False
        return ValidationResult(valid, errmsg)

    @check_handler
    def same_signature(
        self,
        obj1: SignatureLike,
        obj2: SignatureLike,
        *,
        extra_err_msg: Optional[str] = None,
        do_raise: Union[Type[Null], bool] = Null,
        exception_type: Union[Type[Null], ExceptionType] = Null,
        do_warn: Union[Type[Null], bool] = Null,
        warning_type: Union[Type[Null], WarningType] = Null,
        _force_untrue: bool = False,
    ):
        _, _, _, _ = do_raise, exception_type, do_warn, warning_type
        errmsg = f"Signature of {obj1} does not match signature of {obj2}"
        errmsg = self._create_error_msg(errmsg, extra_err_msg)
        if _force_untrue:
            return ValidationResult(False, errmsg)

        s1 = get_signature(obj1)
        s2 = get_signature(obj2)
        a = tuple(s1.parameters.values())
        b = tuple(s2.parameters.values())
        if not a == b:
            return ValidationResult(False, errmsg)
        return ValidationResult(True, "")

    @check_handler
    def check(
        self,
        obj: Any,
        typ: Any,
        *,
        arg: Optional[str] = None,
        extra_err_msg: Optional[str] = None,
        do_raise: Union[Type[Null], bool] = Null,
        exception_type: Union[Type[Null], ExceptionType] = Null,
        do_warn: Union[Type[Null], bool] = Null,
        warning_type: Union[Type[Null], WarningType] = Null,
    ):
        kwargs = dict(
            extra_err_msg=extra_err_msg,
            do_raise=do_raise,
            do_warn=do_warn,
            exception_type=exception_type,
            warning_type=warning_type,
        )
        if is_typing_type(typ):
            if typ.__class__ is TypeVar:
                return ValidationResult(True, "")
            if hasattr(typ, "__origin__"):
                outer_typ = typ.__origin__
                if hasattr(typ, "__args__"):
                    if typ.__args__:
                        if outer_typ is list:
                            result = self.is_instance_of(obj, outer_typ, **kwargs)
                            if result.valid:
                                result = self._check_inner_list(
                                    result, obj, typ, kwargs
                                )
                            return result
                        elif outer_typ is tuple:
                            result = self.is_instance_of(obj, outer_typ, **kwargs)
                            if result.valid:
                                result = self._check_inner_tuple(
                                    result, obj, typ, kwargs
                                )
                            return result
                        elif outer_typ is dict:
                            result = self.is_instance_of(obj, outer_typ, **kwargs)
                            if result.valid:
                                result = self._check_inner_dict(
                                    result, obj, typ, kwargs
                                )
                            return result
                        elif outer_typ == typing.Union:
                            for inner_typ in typ.__args__:
                                result = self(
                                    obj, inner_typ, do_raise=False, do_warn=False
                                )
                                if result.valid is True:
                                    return result
                            return ValidationResult(
                                False, f"Value {obj} did not pass {typ}"
                            )
                        elif self._typ_is_callable(outer_typ):
                            result = self.is_instance_of(obj, outer_typ, **kwargs)
                            if result.valid:
                                result = self._check_inner_callable(result, obj, typ)
                            return result
                else:
                    return self.is_instance_of(obj, outer_typ, **kwargs)
            elif self._typ_is_typeddict(typ):
                result = self.is_instance_of(obj, dict, **kwargs)
                if result.valid:
                    result = self._check_inner_typed_dict(result, obj, typ)
                return result
        if arg is not None:
            extra_msgs = [f"TypeError on argument '{arg}'."]
            if kwargs["extra_err_msg"]:
                extra_msgs.append(kwargs["extra_err_msg"])
            kwargs["extra_err_msg"] = " ".join(extra_msgs)
        return self.is_instance_of(obj, typ, **kwargs)

    @check_handler
    def __call__(
        self,
        obj: Any,
        typ: TypingType,
        *,
        arg: Optional[str] = None,
        extra_err_msg: Optional[str] = None,
        do_raise: Union[Type[Null], bool] = Null,
        exception_type: Union[Type[Null], ExceptionType] = Null,
        do_warn: Union[Type[Null], bool] = Null,
        warning_type: Union[Type[Null], WarningType] = Null,
    ):
        return self.check(
            obj=obj,
            typ=typ,
            arg=arg,
            extra_err_msg=extra_err_msg,
            do_raise=do_raise,
            exception_type=exception_type,
            do_warn=do_warn,
            warning_type=warning_type,
        )

    def _check_inner_dict(
        self, result, obj: typing.Dict, typ: TypingType, kwargs: dict
    ):
        key_type, val_type = typ.__args__
        for k in obj:
            inner_result = self(k, key_type, **kwargs)
            result = result.combine(inner_result)
        for v in obj.values():
            inner_result = self(v, val_type, **kwargs)
            result = result.combine(inner_result)
        return result

    def _check_inner_tuple(self, result, obj: Tuple, typ: TypingType, kwargs: dict):
        use_same_inner_type = False
        inner_typ = typ.__args__[0]
        if len(typ.__args__) >= 2 and typ.__args__[1] is Ellipsis:
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

    def _check_inner_list(self, result, obj: List, typ: TypingType, kwargs: dict):
        inner_typ = typ.__args__[0]
        for inner_obj in obj:
            inner_result = self(inner_obj, inner_typ, **kwargs)
            result = result.combine(inner_result)
        return result

    def _check_inner_callable(self, result, obj: Callable, typ: TypingType):
        if typ.__args__:
            arg_annots = typ.__args__[:-1]
            ret_annot = typ.__args__[-1]
            signature = inspect.signature(obj)
            signature_params = list(signature.parameters.values())
            signature_ret = signature.return_annotation
            if not len(signature_params) == len(arg_annots):
                result = result.combine(
                    ValidationResult(
                        valid=False,
                        msg=f"Expected {len(arg_annots)} arguments for "
                        f"callable ({typ}), but found {len(signature_params)}",
                    )
                )
            else:
                for param, annot in zip(signature_params, arg_annots):
                    inner_result = self.is_type_of(
                        param.annotation,
                        annot,
                        extra_err_msg=f"TypeError on arg '{param}'. ",
                    )
                    result = result.combine(inner_result)
                inner_result = self.is_type_of(
                    signature_ret,
                    ret_annot,
                    extra_err_msg="TypeError on return type. ",
                )
                result = result.combine(inner_result)

            if is_generator_type(ret_annot) and not is_generator_function(obj):
                result = result.combine(
                    ValidationResult(
                        valid=False,
                        msg=f"Function is not a generator function ({obj}).",
                    )
                )
        if not result.valid:
            outer_result = ValidationResult(
                valid=False, msg=f"'{signature}' does not match '{typ}'"
            )
            result = outer_result.combine(result)
        return result

    def _check_inner_typed_dict(self, result, obj: Callable, typ: TypingType):
        annotations = typ.__annotations__
        for k, annot in annotations.items():
            if k not in obj:
                result = result.combine(
                    ValidationResult(
                        valid=False,
                        msg=f"Key '{k}' missing on TypedDict {typ}. "
                        f"Expected keys {list(annotations.keys())}",
                    )
                )
            else:
                result = result.combine(
                    self.check(obj[k], annot, extra_err_msg=f"TypeError on key '{k}'.")
                )
        return result

    def validate_signature(self, other: SignatureLike):
        def wrapped(f: Callable) -> Callable:
            self.same_signature(f, other)
            return f

        return wrapped

    def validate_args(self, x: Union[str, Callable], *others: str) -> Callable:
        if isinstance(x, str):
            return functools.partial(self._validate_args, only=[x, *others])
        else:
            return self._validate_args(x)

    def _validate_args(self, f: Callable, only=None) -> Callable:
        signature: inspect.Signature = inspect.signature(f)
        checker = self
        frame = get_back_frame()
        frameinfo = inspect.getframeinfo(frame)

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            bound_args = signature.bind(*args, **kwargs)
            params_list = list(bound_args.signature.parameters.values())
            for p in params_list:
                if only and p.name not in only:
                    continue
                if p.annotation and not is_empty(p.annotation):
                    msg = (
                        f"Argument error for `{p}` for function `{f.__name__}` "
                        f"({frameinfo.filename}:{frameinfo.lineno})"
                    )
                    if p.name in bound_args.arguments:
                        pvalue = bound_args.arguments[p.name]
                        checker(pvalue, p.annotation, extra_err_msg=msg)
            return f(*args, **kwargs)

        return wrapped


checker = ValueChecker(do_raise=False)
check_value = checker

validator = ValueChecker(do_raise=True)
validate_value = validator
validate_args = validator.validate_args
validate_signature = validator.validate_signature
