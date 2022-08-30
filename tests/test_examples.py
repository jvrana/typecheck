#  Copyright (c) 2022. Justin Vrana - All Rights Reserved
#   You may use, distribute and modify this code under the terms of the MIT license.
from typing import Dict
from typing import List
from typing import Union

import pytest

from jdv_typecheck import TypeCheckError
from jdv_typecheck import validate_args
from jdv_typecheck import validate_signature
from jdv_typecheck import validate_value


def test_validate_args():
    @validate_args
    def foo(a: Dict[int, Union[None, str]], b: Union[float, List[float]]):
        ...

    foo({}, [])
    foo({}, 1.0)
    foo({}, [2.0])
    with pytest.raises(Exception):
        foo({}, 1)
    with pytest.raises(Exception):
        foo({}, [1])
    with pytest.raises(Exception):
        foo({4: None}, [1])


class TestValidateSignature:
    def test_validate_signature_passes(self):
        def bar(a: Dict[int, Union[None, str]], b: Union[float, List[float]]):
            ...

        @validate_signature(bar)
        def foo(a: Dict[int, Union[None, str]], b: Union[float, List[float]]):
            ...

    def test_validate_signature_fails(self):
        def bar(a: Dict[int, Union[None, str]], b: Union[float, List[float]]):
            ...

        with pytest.raises(TypeCheckError):

            @validate_signature(bar)
            def foo1(a: Dict[int, Union[None, str]]):
                ...

        with pytest.raises(TypeCheckError):

            @validate_signature(bar)
            def foo2(a: Dict[int, Union[None, str]], b):
                ...
