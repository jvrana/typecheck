import pytest
import sys
from os.path import join, abspath, dirname


@pytest.fixture(scope="session", autouse=True)
def add_sys_path():
    sys.path.append(join(abspath(dirname(__file__))))