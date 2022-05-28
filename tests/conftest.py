#  Copyright (c) 2022. Justin Vrana - All Rights Reserved
#   You may use, distribute and modify this code under the terms of the MIT license.
import sys
from os.path import abspath
from os.path import dirname
from os.path import join

import pytest


@pytest.fixture(scope="session", autouse=True)
def add_sys_path():
    sys.path.append(join(abspath(dirname(__file__))))
