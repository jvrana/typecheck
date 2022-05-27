import sys
from os.path import abspath
from os.path import dirname
from os.path import join

import pytest


@pytest.fixture(scope="session", autouse=True)
def add_sys_path():
    sys.path.append(join(abspath(dirname(__file__))))
