from typing import Dict
from typing import List
from typing import Union

import pytest

from typecheck import validate_args
from typecheck import validate_value


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
